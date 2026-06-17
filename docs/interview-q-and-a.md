# 项目面试问答

这份文档用于准备 Cyberpunk RAG Agent 项目的面试讲解。每个问题都配了可直接回答的版本。

## 1. 这个项目是做什么的？

答：

这是一个中文《赛博朋克：边缘行者》RAG Agent 项目，主要回答动画、Cyberpunk 2077、夜之城世界观、角色、剧情、音乐电台和联动内容相关问题。

它不是单纯聊天 Demo，而是包含本地知识库入库、Chroma 向量检索、Dense + BM25 混合召回、RRF 融合排序、Cross-Encoder 精排、Agent 工具调用、Streamlit 前端、FastAPI 服务和 Ragas 评测闭环的小型 RAG Agent 原型。

## 2. 用户提问后，完整链路是什么？

答：

完整链路是：

```text
用户输入
 -> Streamlit / FastAPI
 -> ReactAgent
 -> 根据 prompt 判断是否需要工具
 -> 调用 RAG 或结构化工具
 -> 检索本地知识库
 -> 拼接上下文
 -> 调用 LLM 总结回答
 -> 返回答案和参考来源
```

如果是普通作品问题，会优先走 `rag_summarize`。如果是分集、角色、剧透等级明确的问题，也可以走结构化工具，比如 `get_episode_summary` 或 `get_character_profile`。

## 3. RAG 在这个项目里解决什么问题？

答：

RAG 主要解决模型不知道本地知识、容易凭记忆胡说的问题。

项目把 Cyberpunk 相关资料放在 `data/`，切块后写入 Chroma。用户提问时，系统先从知识库检索相关 chunk，再把这些 chunk 作为上下文交给模型生成答案。

这样回答可以基于本地资料，而不是完全依赖模型参数记忆。

## 4. 知识库是怎么入库的？

答：

入库流程在 `rag/vector_store.py`：

```text
扫描 data/
 -> 读取 txt/pdf
 -> clean_text 清洗文本
 -> FAQ / 100问类文档优先按问答结构切分
 -> RecursiveCharacterTextSplitter 切 chunk
 -> 生成稳定 chunk id
 -> embedding
 -> 写入 Chroma
 -> 更新 knowledge_manifest
```

当前配置里允许 `txt`、`pdf`、`md`、`markdown`，但实际 loader 主要实现了 `txt/pdf`，Markdown loader 是后续可以补的点。

## 5. 当前 chunk 是怎么切的？

答：

当前主要用 `RecursiveCharacterTextSplitter`。

配置在 `config/chroma.yaml`：

```yaml
txt_chunk_size: 220
txt_chunk_overlap: 40
pdf_chunk_size: 420
pdf_chunk_overlap: 60
chunk_size: 240
chunk_overlap: 40
separators: ["\n\n","。",".","?","？","!"," ",""]
```

也就是说，txt 更小，pdf 稍大。切分优先按段落、句号、问号等自然边界切，最后才按字符硬切。

另外，`100问.txt` 或包含“常见问题”的文档会先用 `split_qa_documents()` 拆成独立问答，再进入普通切块流程。

## 6. 为什么要做 FAQ 特殊切分？

答：

FAQ 文档通常天然是“问题-答案”结构。如果直接按长度切，可能把问题和答案切开，导致检索时只召回问题或只召回答案。

特殊切分后，每个问答会变成：

```text
问题：xxx？
答案：xxx
```

这样更容易命中用户的相似问题，也能让模型拿到完整上下文。

## 7. 什么是 Dense Embedding 检索？

答：

Dense Embedding 检索是把问题和文档 chunk 都转成向量，然后通过语义相似度找相关内容。

它适合处理表达不完全一样但语义接近的问题。

比如：

```text
没玩过游戏能看吗？
```

可以召回：

```text
动画主线独立，不需要先玩 Cyberpunk 2077。
```

## 8. 为什么还要加 BM25？

答：

Dense 检索擅长语义，但对专有名词、集数、歌曲名、英文名有时不稳定。

BM25 是关键词检索，适合召回：

- `第6集`
- `亚当重锤`
- `I Really Want to Stay at Your House`
- `98.7 Body Heat Radio`
- `Sandevistan`

所以项目用 Dense 负责语义召回，BM25 负责关键词召回，两者互补。

## 9. jieba 在 BM25 里有什么用？

答：

BM25 需要先把文本切成 token。英文可以按空格切，但中文没有天然空格，所以要分词。

`jieba` 是中文分词工具，用来把中文句子切成词。

项目里不仅用 jieba，还额外保留了英文词、数字、中文连续词块和 2/3/4 字 n-gram，避免专有名词没进词典时召回不稳。

## 10. RRF 是什么？为什么要用？

答：

RRF 是 Reciprocal Rank Fusion，中文可以理解为“倒数排名融合”。

它不直接比较 Dense 分数和 BM25 分数，因为这两种分数尺度不同，不能简单相加。

RRF 只看排名位置：

```text
score = sum(weight / (rrf_k + rank))
```

如果一个 chunk 在 Dense 和 BM25 里都排得靠前，它的融合分就高。

这样能稳定融合两路召回。

## 11. Cross-Encoder Rerank 是什么？

答：

Cross-Encoder 是精排模型，不是 LLM。

它会把：

```text
query + chunk
```

作为一对输入，直接判断这段 chunk 和问题的相关性。

项目中流程是：

```text
Dense + BM25 先召回候选
 -> RRF 粗排
 -> Cross-Encoder 只重排前 20 个候选
 -> 返回 top-k
```

这样可以提高最终上下文质量。

## 12. 为什么 Cross-Encoder 默认关闭？

答：

因为 Cross-Encoder 首次加载模型比较慢，推理也比普通向量检索更耗时。

日常启动前端时不一定需要它，所以默认关闭。

需要评测或展示时可以用环境变量开启：

```powershell
$env:ENABLE_CROSS_ENCODER_RERANK="1"
```

## 13. 当前 RAG 检索链路是什么？

答：

当前检索链路是：

```text
query 规范化
 -> 同义词和分集标题扩展
 -> Dense Embedding 召回
 -> BM25s + jieba 召回
 -> RRF 融合排序
 -> Cross-Encoder 可选精排
 -> source boost
 -> 多样性去重
 -> top-k chunk
```

这个链路比单纯 Chroma similarity search 更完整。

## 14. 什么是 source boost？

答：

source boost 是轻量来源加权。

比如用户问音乐电台问题，系统会轻微提升 `08_游戏本体联动与音乐电台.txt` 的权重。用户问角色问题，会提升 `05_人物关系与角色解析.txt` 的权重。

它不是硬编码答案，只是 tie-break，避免通用合集抢占 top-k。

## 15. 什么是多样性去重？

答：

多样性去重是在最终返回 top-k 前，避免 top-k 全部来自同一个文件或重复内容。

项目里会控制：

- 重复内容不重复返回。
- 单个来源最多保留一定数量 chunk。

这样模型拿到的上下文更互补，不会全是同一段资料的变体。

## 16. Ragas 是怎么评测的？

答：

Ragas 会用评测集中的：

```text
question
reference
retrieved_contexts
answer
```

计算四个指标：

- Faithfulness：答案是否被上下文支持。
- Answer Relevancy：答案是否正面回答问题。
- Context Recall：检索上下文是否覆盖参考答案需要的信息。
- Context Precision：检索上下文是否有用、少噪音。

脚本是 `scripts/evaluate_ragas.py`。

## 17. 当前 Ragas 分数是多少？

答：

Cross-Encoder 开启后的最新全量结果是：

```text
Faithfulness: 0.9607
Answer Relevancy: 0.6419
Context Recall: 0.7286
Context Precision: 0.6996
Average: 0.7577
```

可以说明项目优化后，忠实度和上下文召回有明显提升。

## 18. 为什么 Answer Relevancy 相对低？

答：

Answer Relevancy 主要看回答是否直接回应用户问题。

它相对低，可能有几个原因：

- 回答有时补充背景太多，直接性不够。
- 检索上下文比较丰富，模型会扩展解释。
- Ragas judge 对中文长回答的相关性判断有波动。

后续可以通过 prompt 约束“先直接回答，再补充背景”来优化。

## 19. `scripts` 目录是干什么的？

答：

`scripts` 是评测脚本区，不是项目运行入口。

主要有三个脚本：

- `evaluate_rag.py`：最简单的关键词和来源回归测试。
- `evaluate_rag_quality.py`：自定义规则质量评测。
- `evaluate_ragas.py`：正式 Ragas 评测脚本。

其中最重要的是 `evaluate_ragas.py`，因为它输出真实 Ragas 指标和历史评测记录。

## 20. Agent tools 模块是干什么的？

答：

`agent/tools` 是 Agent 的工具层。

它分三部分：

- `agent_tools.py`：本地 Cyberpunk 工具。
- `mcp_tools.py`：加载外部 MCP 工具。
- `middleware.py`：监控工具调用、记录模型调用、动态拼接 prompt。

Agent 通过这些工具获得检索、结构化查询和外部能力。

## 21. 当前有哪些本地工具？

答：

当前本地工具有：

- `rag_summarize`：检索并总结知识库。
- `search_cyberpunk_kb`：按剧透等级检索结构化知识。
- `get_episode_summary`：查询指定集数摘要。
- `get_character_profile`：查询角色资料。
- `get_user_profile`：根据用户偏好生成观影画像和避雷建议。

这些工具都用 `@tool` 注册给 LangChain Agent。

## 22. `rag_summarize` 和结构化工具有什么区别？

答：

`rag_summarize` 走完整 RAG 检索链路，适合开放式问题。

结构化工具读取 `cyberpunk_edgerunners_rag_chunks.jsonl`，更确定、更快，适合分集、角色、剧透等级明确的问题。

简单说：

```text
复杂问题 -> rag_summarize
确定性查询 -> 结构化工具
```

## 23. middleware 有什么用？

答：

`middleware.py` 主要做三件事：

1. `monitor_tool`：记录工具调用参数和结果，失败时返回 ToolMessage，避免 Agent 崩溃。
2. `log_before_model`：每次模型调用前记录消息数量和最后一条消息。
3. `session_prompt`：把会话事实拼进系统提示词，让多轮对话更稳定。

它相当于 Agent 执行过程的监控和增强层。

## 24. MCP 在项目里有什么用？

答：

MCP 是 Model Context Protocol，用于把外部工具以标准协议接入 Agent。

项目里已经实现了 MCP 加载逻辑：

```text
config/agent.yaml
 -> load_mcp_tools()
 -> MultiServerMCPClient
 -> MCP tools
 -> Agent tools
```

这样后续不用改 Agent 主体，就可以接入外部工具。

## 25. 当前接了什么 MCP？

答：

当前接入了 Filesystem MCP。

配置在 `config/agent.yaml`，限制访问范围为：

```text
data/
docs/
```

它可以让 Agent 通过 MCP 查看知识库文件和项目文档，例如列目录、读文件、搜索文件、查看文件信息。

## 26. 为什么不开放整个磁盘给 Filesystem MCP？

答：

出于安全和边界控制。

Agent 只需要访问知识库和项目文档，所以只开放：

```text
data/
docs/
```

这样既能展示 MCP 能力，也能避免误读或误改无关文件。

## 27. 为什么暂时不接 Fetch MCP？

答：

Fetch MCP 适合读取用户提供的 URL，比如官方公告或 patch notes。

但当前项目核心是本地可信 RAG，不是泛联网搜索助手。暂时不接 Fetch，可以保持系统边界清晰。

后续策略是：

```text
用户提供 URL -> Fetch MCP 读取并总结
用户没提供 URL -> 说明当前未接入自动搜索最新资料
```

## 28. Streamlit 和 FastAPI 分别负责什么？

答：

Streamlit 是演示前端，负责聊天界面、会话管理、快捷问题、参考来源展示和知识库重建按钮。

FastAPI 是服务化入口，提供：

- `/health`
- `/chat`
- `/rag/query`
- `/tools/search`
- `/tools/episode`
- `/tools/character`
- `/tools/viewer-profile`

这说明项目既能演示，也能作为后端服务被其他系统调用。

## 29. `/chat` 和 `/rag/query` 有什么区别？

答：

`/chat` 走完整 Agent，会让模型决定是否调用工具，适合多轮对话。

`/rag/query` 直接调用 RAG 服务，不经过 Agent 决策，适合测试检索总结能力。

简单说：

```text
/chat -> Agent 对话
/rag/query -> 直接 RAG
```

## 30. 会话是怎么保存的？

答：

会话保存逻辑在 `utils/chat_session_store.py`。

它用本地 JSON 文件：

```text
storage/chat_sessions.json
```

保存会话 id、标题、创建时间、更新时间和 messages。

前端刷新后可以恢复历史会话。

## 31. `bootstrap.py` 是干什么的？

答：

`bootstrap.py` 做启动前自检。

它检查：

- 模型 API Key 是否存在。
- prompt 文件是否存在。
- 知识库目录是否存在。
- 模型配置是否完整。
- 向量库配置是否完整。
- prompt 文件是否是 UTF-8。

如果有问题，前端会直接显示错误并停止启动。

## 32. 项目当前最强的亮点是什么？

答：

最强亮点是它不是普通 RAG Demo，而是做了完整检索优化和评测闭环。

可以概括为：

```text
Dense Embedding + BM25s/jieba + RRF + Cross-Encoder Rerank + Ragas Evaluation
```

并且有真实评测数据和前后优化对比。

## 33. 项目当前最大短板是什么？

答：

当前最大短板是工程化后台和知识库治理还不完整。

比如：

- 没有知识库管理后台。
- 没有 Docker 化部署。
- 没有完整监控面板。
- Markdown loader 还没真正实现。
- 分集摘要类问题适合继续做 section-aware chunking。

## 34. 如果继续优化，你会做什么？

答：

我会优先做三件事：

1. 补 Markdown loader，让配置和实际能力一致。
2. 做 section-aware chunking，让标题、分集、角色段落保持完整。
3. 加 Ragas 阈值回归，比如 Average 低于某个值就提示失败。

如果再往工程化走，会加 Dockerfile、知识库状态面板和评测结果展示页。

## 35. 这个项目算企业级吗？

答：

它更准确的定位是“小型企业级 RAG Agent 原型”，不是完整生产级系统。

它已经具备：

- 本地知识库。
- 增量同步。
- 混合检索。
- 精排。
- Agent 工具。
- MCP 扩展。
- 服务化 API。
- Ragas 评测。

但真正生产级还需要：

- 用户权限。
- 监控告警。
- 知识库管理后台。
- 灰度发布。
- 数据权限隔离。
- 更完整的自动化测试和部署。

## 36. 简历上怎么写比较真实？

答：

可以写：

> 构建中文《赛博朋克：边缘行者》RAG Agent，支持 Streamlit 前端、FastAPI 服务、Chroma 向量库、BM25s/jieba 混合召回、RRF 融合排序、Cross-Encoder 精排和 Ragas 质量评测闭环。

也可以写：

> 基于 35 条 Golden Test Set 接入 Ragas 评测体系，覆盖 Faithfulness、Answer Relevancy、Context Recall、Context Precision；引入 Dense + BM25 + RRF + Cross-Encoder 后，Average 从 0.5995 提升至 0.7577。

不要写没有真实做过的生产级能力，比如完整权限系统、线上监控平台或自动知识库治理后台。
