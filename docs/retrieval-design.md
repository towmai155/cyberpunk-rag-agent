# Retrieval Design

当前 RAG 检索采用 `Dense Embedding + bm25s + jieba + RRF + Cross-Encoder Rerank` 的混合召回与多阶段排序。

## 流程

```text
用户问题
 -> query 规范化与同义词扩展
 -> Dense Embedding 向量召回
 -> BM25 关键词召回
 -> RRF 排名融合
 -> Cross-Encoder 可选精排
 -> Parent-Child 上下文回填
 -> 按问题类型做轻量 source boost
 -> 多样性去重
 -> 返回 top-k chunk 给总结模型
```

## Dense Embedding

Dense 通道使用 Chroma 相似度检索，适合处理语义相近但字面不完全一致的问题。

示例：

- “没玩过游戏能看吗”
- “露西为什么执着月球”
- “边缘行者和 2077 的关系”

## BM25

BM25 通道使用 `bm25s` 实现，并用 `jieba` 做中文分词。它按标准 BM25 公式计算：

- `k1 = 1.5`
- `b = 0.75`

中文文本使用混合 tokenizer：

- `jieba` 负责中文自然分词。
- 英文和数字按词切分。
- 中文额外保留连续词块。
- 中文额外生成 2/3/4 字 n-gram，避免领域专有词未进词典时召回不稳。

这样可以稳定召回：

- “第6集”
- “赛博精神病”
- “亚当重锤”
- “I Really Want to Stay at Your House”
- “98.7 Body Heat Radio”

BM25 索引使用进程内缓存：

- 第一次检索时从 Chroma 读取 chunk 并构建 bm25s index。
- 后续检索复用内存中的 BM25 index。
- 检测到 Chroma 文档数量变化时自动重建缓存。
- 不依赖 Redis。

## RRF

RRF 是 Reciprocal Rank Fusion，用于融合 Dense 和 BM25 的排序结果。

公式：

```text
score(doc) = sum(weight / (rrf_k + rank))
```

当前配置：

- `rrf_k = 60`
- Dense 权重：`1.0`
- BM25 权重：`1.0`

RRF 的好处是不用强行归一化向量分数和 BM25 分数，只依赖排名位置，稳定性更好。

## Cross-Encoder Rerank

Cross-Encoder Rerank 是可选精排阶段，不需要接 LLM。

它使用专门的 reranker 模型，把用户问题和候选 chunk 拼成一对输入：

```text
query + chunk -> Cross-Encoder -> relevance score
```

当前配置：

- `cross_encoder_rerank_enabled = false`
- `cross_encoder_model_name = BAAI/bge-reranker-base`
- `cross_encoder_top_n = 20`

运行方式：

- RRF 先生成候选池。
- Cross-Encoder 只重排前 20 个候选，避免对所有 chunk 做昂贵推理。
- 如果 `sentence-transformers` 未安装、模型下载失败或推理失败，系统会自动回退到 RRF 结果。
- 为避免首次下载模型阻塞日常启动，默认关闭；需要测试时设置环境变量：

```bash
ENABLE_CROSS_ENCODER_RERANK=1
```

它的目标是提高最终上下文精确率和答案相关性。

## Parent-Child Retrieval

当前项目接入轻量版 Parent-Child Retrieval，不替换原有 Dense + BM25 + RRF + Cross-Encoder 链路。

设计目标：

- child chunk 用于检索，保持命中精度。
- parent chunk 用于最终回答，提供更完整上下文。

入库流程：

```text
原始文档
 -> parent splitter 生成较大 parent chunk
 -> child splitter 将每个 parent 再切成较小 child chunk
 -> child chunk 写入 Chroma
 -> child metadata 保存 parent_id
 -> parent 文本保存到 storage/parent_docs.json
```

检索流程：

```text
Dense / BM25 / RRF / Cross-Encoder 命中 child chunk
 -> 根据 parent_id 找回 parent chunk
 -> 去重 parent
 -> 将 parent chunk 作为最终上下文交给模型
```

当前配置：

```yaml
use_parent_context: true
parent_chunk_size: 720
parent_chunk_overlap: 120
txt_chunk_size: 220
txt_chunk_overlap: 40
```

这样做的好处是：检索仍然用较短 child 保持精准，生成回答时使用较长 parent 避免上下文过碎，尤其适合分集摘要、角色弧光和设定解释类问题。

## Source Boost

RRF 后会根据问题类型做轻量来源加权：

- 分集问题优先 `01_作品基础`、`03_赛博朋克边缘行者100问`、`cyberpunk_edgerunners_full_kb`
- 角色问题优先 `05_人物关系`
- 设定问题优先 `04_夜之城`、`06_设定术语`
- 音乐电台问题优先 `08_游戏本体联动与音乐电台`
- 鸣潮联动问题优先 `09_鸣潮联动与边缘幻梦剧情`

这一步只是小幅 tie-break，不替代 BM25/RRF 主排序。

## 多样性去重

最终返回前会做两类去重：

- 内容指纹去重，减少 txt/pdf 或合集重复片段。
- 单一来源最多保留 2 个 chunk，避免 top-k 被同一个文件占满。

## 当前配置

配置位于 `config/chroma.yaml`：

```yaml
k: 8
candidate_k: 32
rrf_k: 60
bm25_k1: 1.5
bm25_b: 0.75
use_parent_context: true
parent_chunk_size: 720
parent_chunk_overlap: 120
cross_encoder_rerank_enabled: false
cross_encoder_model_name: BAAI/bge-reranker-base
cross_encoder_top_n: 20
```
