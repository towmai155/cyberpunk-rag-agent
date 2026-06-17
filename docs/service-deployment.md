# 服务化部署说明

本项目保留 Streamlit 作为演示前端，同时新增 FastAPI 服务入口，方便作为实习项目展示“前后端分离 / API 化”的能力。

## 启动 Streamlit 演示前端

```powershell
cd D:\langchain-agent-master\langchain-agent-master
python -m streamlit run app.py
```

## 启动 FastAPI 服务

```powershell
cd D:\langchain-agent-master\langchain-agent-master
python -m uvicorn api:app --host 0.0.0.0 --port 8000
```

接口文档：

```text
http://localhost:8000/docs
```

## 常用接口

- `GET /health`：运行时配置检查。
- `POST /chat`：完整 Agent 对话。
- `POST /rag/query`：直接调用 RAG 总结。
- `POST /tools/search`：按剧透等级结构化检索。
- `POST /tools/episode`：查询分集摘要。
- `POST /tools/character`：查询角色资料。
- `POST /tools/viewer-profile`：生成观影偏好画像。

## Ragas 评测

```powershell
python scripts\evaluate_ragas.py --batch-size 4
```

开启 Cross-Encoder 精排后评测：

```powershell
$env:ENABLE_CROSS_ENCODER_RERANK="1"
python scripts\evaluate_ragas.py --batch-size 4
```

输出会写入 `evals/ragas_latest_result.json` 和 `evals/history/`。
