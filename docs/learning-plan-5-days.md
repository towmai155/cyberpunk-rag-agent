# 5 天学习计划

这份计划用于快速吃透当前 Cyberpunk RAG Agent 项目，方便面试前复盘。

## Day 1：跑通项目

目标：知道项目怎么启动、怎么对话、怎么重建知识库。

重点文件：

- `app.py`
- `api.py`
- `config/rag.yaml`
- `config/chroma.yaml`
- `config/prompt.yaml`
- `config/agent.yaml`

要能讲清楚：

- Streamlit 前端和 FastAPI 服务分别怎么启动。
- `DASHSCOPE_API_KEY` 为什么是必需的。
- `data/` 目录和 `storage/chroma_db/` 分别是什么。
- `/health` 检查了哪些运行条件。

## Day 2：理解 Agent 和工具

目标：知道用户问题如何被 Agent 路由到工具。

重点文件：

- `agent/react_agent.py`
- `agent/tools/agent_tools.py`
- `agent/tools/middleware.py`
- `agent/tools/mcp_tools.py`
- `prompts/main_prompt.txt`

要能讲清楚：

- 当前有哪些本地工具。
- `rag_summarize` 和结构化工具有什么区别。
- 剧透等级如何影响结构化检索。
- MCP 工具如何通过 `config/agent.yaml` 注入。

## Day 3：理解知识库入库

目标：知道文档如何变成 Chroma 里的 chunk。

重点文件：

- `rag/vector_store.py`
- `utils/file_handler.py`
- `storage/knowledge_manifest.json`
- `data/cyberpunk_edgerunners_rag_kb_pack(1)/txt/`

要能讲清楚：

- 支持哪些文件类型。
- FAQ 文档和普通文本如何切块。
- manifest 如何支持增量更新。
- 文件删除后如何清理旧向量。
- Chroma 索引异常时如何自动重建。

## Day 4：理解检索优化

目标：能讲清楚为什么项目不是普通 Chroma Demo。

重点文件：

- `rag/rag_service.py`
- `docs/retrieval-design.md`
- `config/chroma.yaml`

要能讲清楚：

- Dense Embedding 适合什么问题。
- BM25s + jieba 解决什么问题。
- RRF 为什么能融合两路排序。
- Cross-Encoder Rerank 为什么不需要 LLM。
- 为什么 Cross-Encoder 默认关闭。
- top-k、candidate-k、cross_encoder_top_n 分别控制什么。

## Day 5：理解评测与展示

目标：能用真实数据说明优化有效。

重点文件：

- `scripts/evaluate_ragas.py`
- `evals/cyberpunk_golden_30.json`
- `evals/ragas_latest_result.json`
- `docs/ragas-evaluation.md`
- `docs/project-changelog.md`

要能讲清楚：

- Ragas 四个指标分别代表什么。
- Golden Test Set 为什么重要。
- 最新分数是多少。
- Dense-only、BM25+RRF、Cross-Encoder 三个阶段的变化。
- 为什么 Ragas 分数适合做回归对比，而不是绝对真理。

## 面试前自测问题

- 这个项目和普通 RAG Demo 的区别是什么？
- 为什么要同时用 Dense 和 BM25？
- RRF 相比直接加权分数有什么好处？
- Cross-Encoder Rerank 的代价是什么？
- 如果换一个知识库，哪些能力仍然通用？
- 当前项目离真正生产级还差什么？
