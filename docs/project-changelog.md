# Project Changelog

这个文档记录项目每次新增的重要能力。以后有新模块、新工具、新评测、新部署方式，都追加到这里，方便写简历和复盘。

## 2026-06-18

### Parent-Child 后 Ragas 全量评测

- 开启 Cross-Encoder Rerank 后重新跑完 35 条 Golden Test Set。
- 当前策略为 Parent-Child Retrieval + Dense Embedding + bm25s + jieba + RRF + Cross-Encoder Rerank。
- 最新全量结果：
  - Faithfulness: `0.9556`
  - Answer Relevancy: `0.6562`
  - Context Recall: `0.9143`
  - Context Precision: `0.7704`
  - Average: `0.8241`
- 相比最初 Dense baseline：
  - Context Recall: `0.3095 -> 0.9143`
  - Average: `0.5995 -> 0.8241`
- 评测历史已保留在 `docs/ragas-evaluation.md`，包含 Baseline、BM25 + RRF、Cross-Encoder、Parent-Child + Cross-Encoder 四轮结果。

## 2026-06-17

### Parent-Child Retrieval 接入

- 新增轻量版 Parent-Child Retrieval。
- 入库时将原始文档先切成较大的 parent chunk，再将 parent 切成较小 child chunk。
- Chroma 中仍写入 child chunk，用于 Dense / BM25 / RRF / Cross-Encoder 检索。
- child metadata 保存 `parent_id`，最终回答前根据 `parent_id` 回填 parent chunk。
- parent 文本保存到 `storage/parent_docs.json`，该文件属于本地运行产物，不提交 Git。
- 目标是保持 child 检索精度，同时让模型拿到更完整上下文，改善分集摘要、角色解析和设定解释类问题。
- 同步移除旧 MySQL 依赖 `pymysql`；当前项目不再使用 MySQL。

### Filesystem MCP 接入

- 在 `config/agent.yaml` 中接入 `@modelcontextprotocol/server-filesystem`。
- 当前限制访问范围为：
  - `data/`
  - `docs/`
- MCP 工具通过 `load_mcp_tools()` 自动加载，并与本地 Cyberpunk 工具合并进 Agent 工具列表。
- 已验证可加载 14 个 filesystem MCP 工具，包括读文件、列目录、搜索文件、查看文件信息和编辑文件等。
- Windows 环境下使用 `cmd /c npx.cmd` 启动，避免 PowerShell 执行策略拦截 `npx.ps1`。

### 项目主题清理

- 将 README、端到端说明和学习计划统一改为 Cyberpunk RAG Agent 主题。
- 清理前端中的旧业务文案、快捷问题和示例输入。
- 移除旧报告链路：`report_prompt`、外部记录 CSV、MySQL 导入脚本和 report data store。
- 将启动自检从旧外部数据依赖中解耦，只检查当前项目真正需要的提示词和知识库目录。
- 清空旧会话历史，避免前端继续展示历史主题对话。

### Cross-Encoder Rerank 接入

- 在 Dense Embedding + BM25 + RRF 之后新增可选 Cross-Encoder 精排。
- 默认配置：
  - `cross_encoder_rerank_enabled: false`
  - `cross_encoder_model_name: BAAI/bge-reranker-base`
  - `cross_encoder_top_n: 20`
- 运行逻辑：
  - 先通过 Dense 和 BM25 粗召回。
  - 再用 RRF 融合候选排名。
  - 对前 20 个候选执行 Cross-Encoder 精排。
  - 最后执行多样性去重并返回 top-k。
- 如果 `sentence-transformers` 未安装、模型下载失败或推理失败，会自动回退到 RRF 结果。
- 为避免首次下载模型阻塞日常启动，默认关闭；需要测试时设置 `ENABLE_CROSS_ENCODER_RERANK=1`。
- Cross-Encoder Rerank 不需要接 LLM，它使用专门的 reranker 模型对 `query + chunk` 打相关性分。

### BM25 中文召回升级

- 将手写 BM25 替换为 `bm25s`。
- 使用 `jieba` 做中文分词，并保留英文词、中文连续词块和 2/3/4 字 n-gram。
- BM25 索引使用进程内缓存，不依赖 Redis。

### Ragas 全量评测

- Cross-Encoder Rerank 开启后的 35 条 Golden Test Set 全量结果：
  - Faithfulness: `0.9607`
  - Answer Relevancy: `0.6419`
  - Context Recall: `0.7286`
  - Context Precision: `0.6996`
  - Average: `0.7577`
- RRF-only 版本的 35 条 Golden Test Set 全量结果：
  - Faithfulness: `0.8948`
  - Answer Relevancy: `0.6830`
  - Context Recall: `0.6143`
  - Context Precision: `0.6165`
  - Average: `0.7022`

## 2026-06-16

### Ragas 评测体系

- 新增 35 条 Cyberpunk 领域 Golden Test Set。
- 接入 Ragas 指标：
  - Faithfulness
  - Answer Relevancy
  - Context Recall
  - Context Precision
- 评测结果写入 `evals/ragas_latest_result.json` 和 `evals/history/`。

### Dense + BM25 + RRF 检索

- 增加 Dense Embedding 与 BM25 双路召回。
- 使用 RRF 融合两路召回排名。
- 增加来源过滤和多样性去重，避免旧知识库或重复 chunk 污染上下文。
