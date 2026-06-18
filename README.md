# Cyberpunk Edgerunners RAG Agent

这是一个面向中文用户的《赛博朋克：边缘行者》知识库问答 Agent。项目基于 Streamlit、FastAPI、LangChain、Chroma、DashScope、BM25s、jieba、Cross-Encoder 和 Ragas，支持作品内容问答、剧情解析、角色资料、世界观设定、音乐电台、游戏关联、联动内容和观影推荐。

项目当前定位是“可展示的小型企业级 RAG Agent 原型”：不仅能跑通问答，还包含混合检索、可选精排、知识库增量同步、服务化 API、前端演示和 Ragas 质量评测闭环。

## 主要能力

- 支持多轮对话，历史消息会一起传入 Agent。
- 基于本地知识库进行 RAG 检索与总结。
- 支持《赛博朋克：边缘行者》《Cyberpunk 2077》及相关音乐、电台、联动资料问答。
- 支持剧透等级控制，区分 `S0`、`S1`、`S2`、`S3`、`Full`。
- 支持结构化工具：知识库检索、分集摘要、角色资料、观影画像。
- 支持 Dense Embedding + BM25s/jieba 混合召回。
- 支持 RRF 融合排序。
- 支持可选 Cross-Encoder Rerank。
- 支持轻量版 Parent-Child Retrieval，使用 child chunk 检索、parent chunk 生成回答。
- 支持 Ragas 全量评测，记录 Faithfulness、Answer Relevancy、Context Recall、Context Precision。
- 支持 Streamlit 前端和 FastAPI 服务入口。
- 支持知识库增量同步、陈旧切片清理和 Chroma 索引异常自动修复。

## 项目结构

- `app.py`
  Streamlit 前端入口，负责聊天界面、会话管理、引用来源展示和知识库重建。

- `api.py`
  FastAPI 服务入口，提供健康检查、Agent 对话、RAG 查询和结构化工具接口。

- `agent/react_agent.py`
  Agent 构建入口，封装模型、提示词、中间件和工具注册。

- `agent/tools/agent_tools.py`
  Cyberpunk 主题工具定义，包括：
  - `rag_summarize`
  - `search_cyberpunk_kb`
  - `get_episode_summary`
  - `get_character_profile`
  - `get_user_profile`

- `agent/tools/mcp_tools.py`
  MCP 工具加载逻辑，可按需从 `config/agent.yaml` 注入外部 MCP server。

- `rag/vector_store.py`
  知识库入库和向量库管理，负责文档加载、清洗、切块、向量化、manifest 增量同步和重建。

- `rag/rag_service.py`
  RAG 检索和总结服务，负责查询扩展、Dense/BM25 混合召回、RRF、可选 Cross-Encoder 精排、多样性去重和来源整理。

- `scripts/evaluate_ragas.py`
  Ragas 全量评测脚本。

- `config/`
  项目配置目录：
  - `rag.yaml`：模型配置。
  - `chroma.yaml`：向量库、切块、检索和 rerank 配置。
  - `prompt.yaml`：提示词路径配置。
  - `agent.yaml`：MCP server 配置。

- `prompts/`
  提示词目录：
  - `main_prompt.txt`
  - `rag_summarize.txt`

- `data/`
  本地知识库目录，支持递归扫描 `txt`、`pdf`、`md`、`markdown` 文件。

- `evals/`
  Golden Test Set、最新评测结果和历史评测记录。

- `docs/`
  项目说明、检索设计、Ragas 评测报告和服务化部署文档。

## 知识库机制

当前知识库不是简单文本堆叠，而是有一套可维护的入库流程：

1. 递归扫描 `data/` 目录下的可用文件。
2. 根据文件类型读取内容。
3. 对文本做清洗，统一换行和空白。
4. 对 FAQ / `100问` 类文档优先按问答结构切分。
5. 按不同文件类型使用不同切块参数。
6. 为每个 chunk 生成稳定 ID。
7. 写入 Chroma 向量库。
8. 同步更新 `storage/knowledge_manifest.json`。

增量同步逻辑：

- 文件未变化：跳过入库。
- 文件已更新：删除旧切片，重新切块并写入。
- 文件已删除：清理向量库中残留的旧切片。
- 首次运行或 manifest 缺失：按当前文件状态重建同步信息。

## 检索链路

当前检索策略：

```text
用户问题
 -> query 规范化与同义词扩展
 -> Dense Embedding 向量召回
 -> BM25s + jieba 关键词召回
 -> RRF 融合排序
 -> Cross-Encoder 可选精排
 -> source boost
 -> 多样性去重
 -> 返回 top-k chunk 给总结模型
```

Cross-Encoder 默认关闭，避免日常启动时加载大模型。需要开启时设置：

```powershell
$env:ENABLE_CROSS_ENCODER_RERANK="1"
```

## Ragas 评测

最新全量评测结果见 [docs/ragas-evaluation.md](docs/ragas-evaluation.md)。

当前真实结果：

| Metric | Score |
| --- | ---: |
| Faithfulness | 0.9607 |
| Answer Relevancy | 0.6419 |
| Context Recall | 0.7286 |
| Context Precision | 0.6996 |
| Average | 0.7577 |

运行全量评测：

```powershell
python scripts\evaluate_ragas.py --batch-size 4
```

开启 Cross-Encoder 后评测：

```powershell
$env:ENABLE_CROSS_ENCODER_RERANK="1"
python scripts\evaluate_ragas.py --batch-size 4
```

快速冒烟测试：

```powershell
python scripts\evaluate_ragas.py --limit 2 --batch-size 1
```

## 安装方式

### 1. 创建环境

```powershell
conda create -n agent310 python=3.10 -y
conda activate agent310
```

### 2. 安装依赖

```powershell
pip install -r requirements.txt
```

### 3. 配置环境变量

```powershell
$env:DASHSCOPE_API_KEY="your_api_key_here"
```

如果使用 DeepSeek 聊天模型：

```powershell
$env:DEEPSEEK_API_KEY="your_api_key_here"
```

## 启动方式

### Streamlit 前端

```powershell
python -m streamlit run app.py
```

### FastAPI 服务

```powershell
python -m uvicorn api:app --host 0.0.0.0 --port 8000
```

接口文档：

```text
http://localhost:8000/docs
```

### 预构建或重建知识库

```powershell
python -m rag.vector_store
```

## 常用接口

- `GET /health`：运行时配置检查。
- `POST /chat`：完整 Agent 对话。
- `POST /rag/query`：直接调用 RAG 总结。
- `POST /tools/search`：按剧透等级结构化检索。
- `POST /tools/episode`：查询分集摘要。
- `POST /tools/character`：查询角色资料。
- `POST /tools/viewer-profile`：生成观影偏好画像。

## 当前限制

- 知识库仍以本地静态文件为主，还没有在线管理后台。
- Cross-Encoder 首次加载较慢，因此默认关闭。
- 分集摘要类问题仍有优化空间，后续更适合做 section-aware chunking 或 parent-child retrieval。
- Ragas 分数依赖评测集和 LLM judge，适合做回归对比，不应当当作绝对质量分数。

## 简历表述

可以真实写：

> 构建中文《赛博朋克：边缘行者》RAG Agent，支持 Streamlit 前端、FastAPI 服务、Chroma 向量库、BM25s/jieba 混合召回、RRF 融合排序、Cross-Encoder 精排和 Ragas 质量评测闭环。

也可以写：

> 基于 35 条 Golden Test Set 接入 Ragas 评测体系，覆盖 Faithfulness、Answer Relevancy、Context Recall、Context Precision；引入 Dense + BM25 + RRF + Cross-Encoder 后，Average 从 0.5995 提升至 0.7577。
