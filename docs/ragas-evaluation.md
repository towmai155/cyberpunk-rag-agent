# Ragas Evaluation

本项目已接入 Ragas 评测闭环，用于验证 Cyberpunk RAG Agent 的检索与回答质量。评测结果会写入 `evals/ragas_latest_result.json`，历史结果保存在 `evals/history/ragas_*.json`。

## 覆盖内容

- Golden Test Set：`evals/cyberpunk_golden_30.json`
- 当前样本数：35 条
- 评测脚本：`scripts/evaluate_ragas.py`
- 评测工具：`ragas==0.4.3`
- 当前最新历史文件：`evals/history/ragas_20260618_202707.json`

## 指标

- `faithfulness`：答案是否被检索上下文支持，主要看有没有幻觉。
- `answer_relevancy`：答案是否直接回应用户问题。
- `context_recall`：检索上下文是否覆盖参考答案所需信息。
- `llm_context_precision_with_reference`：检索上下文中有多少内容对参考答案有用。

## 运行方式

全量评测：

```bash
$env:ENABLE_CROSS_ENCODER_RERANK="1"
python scripts/evaluate_ragas.py --batch-size 4
```

快速冒烟测试：

```bash
python scripts/evaluate_ragas.py --limit 2 --batch-size 1
```

## 当前真实结果

运行时间：2026-06-18 20:27:07

检索策略：Parent-Child Retrieval + Dense Embedding + bm25s + jieba + RRF + Cross-Encoder Rerank

样本数：35 条

| Metric | Score |
| --- | ---: |
| Faithfulness | 0.9556 |
| Answer Relevancy | 0.6562 |
| Context Recall | 0.9143 |
| Context Precision | 0.7704 |
| Average | 0.8241 |

## 历史全量对比

| Metric | Baseline | BM25 + RRF | Cross-Encoder | Parent-Child + Cross-Encoder | Total Change |
| --- | ---: | ---: | ---: | ---: | ---: |
| Faithfulness | 0.7868 | 0.8948 | 0.9607 | 0.9556 | +0.1688 |
| Answer Relevancy | 0.5470 | 0.6830 | 0.6419 | 0.6562 | +0.1092 |
| Context Recall | 0.3095 | 0.6143 | 0.7286 | 0.9143 | +0.6048 |
| Context Precision | 0.7548 | 0.6165 | 0.6996 | 0.7704 | +0.0156 |
| Average | 0.5995 | 0.7022 | 0.7577 | 0.8241 | +0.2246 |

## 历史记录

| Run Time | Strategy | Case Count | Faithfulness | Answer Relevancy | Context Recall | Context Precision | Average |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-06-16 04:37:37 | Dense baseline | 35 | 0.7868 | 0.5470 | 0.3095 | 0.7548 | 0.5995 |
| 2026-06-16 06:43:18 | Dense + BM25 + RRF | 35 | 0.8948 | 0.6830 | 0.6143 | 0.6165 | 0.7022 |
| 2026-06-17 02:57:59 | Dense + BM25 + RRF + Cross-Encoder | 35 | 0.9607 | 0.6419 | 0.7286 | 0.6996 | 0.7577 |
| 2026-06-18 19:30:41 | Parent-Child + Cross-Encoder smoke test | 1 | 1.0000 | 0.7178 | 1.0000 | 1.0000 | 0.9294 |
| 2026-06-18 20:27:07 | Parent-Child + Dense + BM25 + RRF + Cross-Encoder | 35 | 0.9556 | 0.6562 | 0.9143 | 0.7704 | 0.8241 |

## 结果解读

- Parent-Child Retrieval 后，`context_recall` 从 0.7286 提升到 0.9143，是本轮最明显的收益，说明检索命中 child chunk 后回填 parent chunk 能补足更多上下文。
- `context_precision` 从 0.6996 提升到 0.7704，说明回填 parent 并没有明显引入噪声，反而让上下文更完整、更可判断。
- `faithfulness` 从 0.9607 小幅回落到 0.9556，仍然处在高位，可以接受。
- `answer_relevancy` 从 0.6419 回升到 0.6562，但仍是四个指标里相对弱的一项，后续更适合从回答模板、答案长度和问题意图识别继续优化。

## 简历表述建议

目前可以真实写：

> 基于 Ragas 建立 RAG 质量评测体系，覆盖 Faithfulness、Answer Relevancy、Context Recall、Context Precision 四类指标，构建 35 条 Cyberpunk 领域 Golden Test Set，并将每轮评测结果写入历史记录用于回归对比。

也可以写：

> 引入 Dense Embedding + BM25 混合召回与 RRF 排序融合后，35 条 Golden Test Set 上 Context Recall 从 0.3095 提升至 0.6143，Faithfulness 从 0.7868 提升至 0.8948。

当前最新版本可以写：

> 在 BM25/RRF 混合检索基础上接入 Cross-Encoder Rerank 与 Parent-Child Retrieval，35 条 Golden Test Set 上 Context Recall 从 0.3095 提升至 0.9143，平均分从 0.5995 提升至 0.8241。

暂时不要写：

> Faithfulness 从 0.62 提升到 0.81。

原因：当前项目已有真实 Ragas 基线和多轮全量评测，简历里应优先写本项目真实跑出来的数字。
