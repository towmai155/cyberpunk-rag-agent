# 端到端项目说明

本文用于从面试讲解角度说明当前《赛博朋克：边缘行者》RAG Agent 的完整链路。

## 项目定位

这是一个中文作品知识库问答 Agent，面向《赛博朋克：边缘行者》《Cyberpunk 2077》及相关音乐、电台、世界观、角色、剧情和联动内容。

项目目标不是只做一个能聊天的 Demo，而是展示一个 RAG Agent 从知识入库、混合检索、工具调用、前端交互、API 服务到质量评测的完整闭环。

## 用户问题如何流转

```text
用户输入
 -> Streamlit 前端 / FastAPI 接口
 -> ReactAgent
 -> 主提示词判断问题类型与剧透边界
 -> 调用本地 Cyberpunk 工具或 MCP 工具
 -> RAG 检索 child chunk
 -> Parent-Child 回填 parent chunk
 -> 模型基于上下文生成回答
 -> 返回正文和参考来源
```

如果用户问的是分集、角色或观影画像，Agent 可以调用结构化工具；如果问题需要更完整资料，会调用 `rag_summarize` 进行检索总结。

## 知识库入库流程

```text
data 文档
 -> 文件读取
 -> 文本清洗
 -> FAQ / 100问类文档优先拆成问答文档
 -> parent splitter 生成较大 parent chunk
 -> child splitter 将 parent 切成较小 child chunk
 -> child chunk 生成稳定 chunk id
 -> child embedding
 -> child chunk 写入 Chroma
 -> parent 文本写入 storage/parent_docs.json
 -> 更新 knowledge_manifest
```

当前支持配置层面的 `txt`、`pdf`、`md`、`markdown`。实际 loader 目前主要实现了 `txt/pdf`，Markdown loader 是后续可以补齐的点。

文件更新后会自动清理旧 child 切片与 parent 文本，并写入新版本；文件删除后会清理 Chroma 中残留的旧切片和 `parent_docs.json` 中的旧 parent 文本。

当前入库后的本地状态：

- Chroma 中保存 child chunk，用于检索。
- `storage/parent_docs.json` 保存 parent chunk，用于回答。
- `storage/knowledge_manifest.json` 保存每个文件的 md5、child 数和 parent 数。

## 检索流程

当前检索不是单一路径，而是多阶段：

```text
query 规范化
 -> 同义词和分集标题扩展
 -> Dense Embedding 召回
 -> BM25s + jieba 召回
 -> RRF 融合排序
 -> Cross-Encoder 可选精排
 -> Parent-Child 上下文回填
 -> source boost
 -> 多样性去重
 -> parent 上下文交给模型
```

Dense 负责语义召回，BM25 负责关键词和专有名词召回，RRF 负责融合两路排序，Cross-Encoder 负责对候选 child chunk 做更细的相关性判断。

Parent-Child Retrieval 的作用是：检索时用较短 child 保持命中精度，生成回答时回填较长 parent，避免上下文太碎。这对分集摘要、角色弧光和设定解释类问题更友好。

当前关键配置：

```yaml
k: 8
candidate_k: 32
use_parent_context: true
parent_chunk_size: 720
parent_chunk_overlap: 120
txt_chunk_size: 220
txt_chunk_overlap: 40
cross_encoder_rerank_enabled: false
```

## Agent 工具

当前本地工具包括：

- `rag_summarize(query)`：检索并总结本地知识库。
- `search_cyberpunk_kb(query, spoiler_level, max_results)`：按剧透等级检索结构化知识。
- `get_episode_summary(episode, spoiler_level)`：查询指定集数摘要。
- `get_character_profile(name, spoiler_level)`：查询角色资料。
- `get_user_profile(viewer_profile)`：根据用户偏好生成观影画像和避雷建议。

项目还支持 MCP 工具注入，可以在 `config/agent.yaml` 中配置外部 MCP server。

当前已经接入 Filesystem MCP，访问范围限制为：

```text
data/
docs/
```

它用于查看知识库文件和项目文档，不开放整个磁盘。

## 前端能力

Streamlit 前端负责：

- 多轮对话展示。
- 会话创建、切换、删除。
- 快捷问题。
- 知识库重建。
- 参考来源展示。
- 本地片段预览。

前端不是企业后台，但足够支撑项目演示和面试讲解。

## 服务化能力

FastAPI 提供 API 化入口：

- `/health`
- `/chat`
- `/rag/query`
- `/tools/search`
- `/tools/episode`
- `/tools/character`
- `/tools/viewer-profile`

这说明项目可以脱离 Streamlit 作为后端服务被其他前端或系统调用。

## 评测闭环

项目使用 Ragas 建立评测体系，评测集位于 `evals/cyberpunk_golden_30.json`。

覆盖指标：

- Faithfulness
- Answer Relevancy
- Context Recall
- Context Precision

最新结果会写入 `evals/ragas_latest_result.json`，历史结果写入 `evals/history/`，便于对比每次检索策略调整是否真的有效。

目前文档中的全量 Ragas 分数是 Parent-Child Retrieval 接入前的最新全量结果。Parent-Child 已通过 1 条样本的冒烟评测，后续需要重新跑全量 Ragas 来确认真实变化。

## 当前亮点

- 有真实知识库，不是硬编码回答。
- 有混合检索和 RRF，不只是 Chroma similarity search。
- 有可选 Cross-Encoder 精排。
- 有轻量版 Parent-Child Retrieval，child 检索、parent 生成。
- 有 Ragas 评测数据，能展示优化前后变化。
- 有 Streamlit 前端和 FastAPI 服务入口。
- 有 Filesystem MCP 接入，能展示外部工具扩展能力。
- 有知识库增量同步和异常修复。

## 当前不足

- 还没有知识库管理后台。
- 还没有 Docker 化部署。
- 还没有完整监控面板。
- Cross-Encoder 首次加载慢，默认关闭。
- Markdown loader 还没有真正实现。
- Parent-Child 接入后还需要重新跑全量 Ragas，确认真实分数变化。
- 分集摘要类问题后续仍可继续用 section-aware chunking 优化。

## 后续扩展

- 可接入 Fetch MCP，用于读取用户提供的官方链接，例如 Cyberpunk 官网公告、CDPR patch notes 或联动活动页面。
- Fetch MCP 暂不默认启用，避免项目从“本地可信 RAG”变成泛联网搜索助手。
- 推荐策略是：用户提供 URL 时读取并总结；用户未提供 URL 时，明确说明当前未接入自动搜索最新外部资料。
- 如果后续需要自动搜索最新消息，再考虑 Firecrawl、Brave Search、Exa 等搜索型 MCP，但这会引入 API Key、成本和来源可信度管理问题。

## 面试讲法

可以这样概括：

> 我做的是一个中文 Cyberpunk 领域 RAG Agent。基础链路是本地知识库入库后将 child chunk 写入 Chroma，并把 parent chunk 存到本地 parent store。检索侧使用 Dense Embedding 和 BM25s/jieba 双路召回，用 RRF 做融合排序，再接可选 Cross-Encoder 精排，最终根据 parent_id 回填更完整的 parent 上下文。质量侧用 Ragas 做了 35 条 Golden Test Set 的回归评测，指标包括 Faithfulness、Answer Relevancy、Context Recall 和 Context Precision。
