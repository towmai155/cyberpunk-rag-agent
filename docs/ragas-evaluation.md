# Ragas Evaluation

本项目已接入 Ragas 评测闭环，用于验证 Cyberpunk RAG Agent 的检索与回答质量。

## 覆盖内容

- Golden Test Set：`evals/cyberpunk_golden_30.json`
- 当前样本数：35 条
- 评测脚本：`scripts/evaluate_ragas.py`
- 最新结果：`evals/ragas_latest_result.json`
- 历史结果：`evals/history/ragas_*.json`

## 指标

- `faithfulness`：答案是否被检索上下文支持。
- `answer_relevancy`：答案是否直接回应用户问题。
- `context_recall`：检索上下文是否覆盖参考答案所需信息。
- `llm_context_precision_with_reference`：检索上下文中有多少内容对参考答案有用。

## 运行方式

```bash
python scripts/evaluate_ragas.py --batch-size 4
```

快速冒烟测试：

```bash
python scripts/evaluate_ragas.py --limit 2 --batch-size 1
```

## 当前真实结果

运行时间：2026-06-17 02:57:59

检索策略：Dense Embedding + bm25s + jieba + RRF + Cross-Encoder Rerank

说明：该结果为接入 Parent-Child Retrieval 前的最新全量评测结果。Parent-Child Retrieval 已接入，后续需要重新跑一轮全量 Ragas 来确认真实分数变化。

| Metric | Score |
| --- | ---: |
| Faithfulness | 0.9607 |
| Answer Relevancy | 0.6419 |
| Context Recall | 0.7286 |
| Context Precision | 0.6996 |
| Average | 0.7577 |

## 优化对比

| Metric | Baseline | BM25 + RRF | Cross-Encoder | Total Change |
| --- | ---: | ---: | ---: | ---: |
| Faithfulness | 0.7868 | 0.8948 | 0.9607 | +0.1739 |
| Answer Relevancy | 0.5470 | 0.6830 | 0.6419 | +0.0949 |
| Context Recall | 0.3095 | 0.6143 | 0.7286 | +0.4191 |
| Context Precision | 0.7548 | 0.6165 | 0.6996 | -0.0552 |
| Average | 0.5995 | 0.7022 | 0.7577 | +0.1582 |

## 当前暴露的问题

- Cross-Encoder 后 `context_recall` 从 0.6143 提升到 0.7286，说明精排进一步改善了上下文覆盖。
- Cross-Encoder 后 `context_precision` 从 0.6165 回升到 0.6996，说明冗余上下文有所减少。
- `answer_relevancy` 从 RRF-only 的 0.6830 降到 0.6419，可能与生成答案偏短、Ragas judge 波动或精排后上下文表达方式变化有关。
- 当前低分项仍集中在分集摘要类问题，例如第 1、4、5、10 集。
- 下一步如果继续优化，更应该做通用的 section-aware chunking 或 parent-child retrieval，而不是继续堆单点规则。

## 简历表述建议

目前可以真实写：

> 基于 Ragas 建立 RAG 质量评测体系，覆盖 Faithfulness、Answer Relevancy、Context Recall、Context Precision 四类指标，构建 35 条 Cyberpunk 领域 Golden Test Set，并将每轮评测结果写入历史记录用于回归对比。

也可以写：

> 引入 Dense Embedding + BM25 混合召回与 RRF 排序融合后，35 条 Golden Test Set 上 Context Recall 从 0.3095 提升至 0.6143，Faithfulness 从 0.7868 提升至 0.8948。

也可以写：

> 在 RRF 后接入可选 Cross-Encoder Rerank，35 条 Golden Test Set 上 Faithfulness 提升至 0.9607，Context Recall 提升至 0.7286，平均分从 0.5995 提升至 0.7577。

暂时不要写：

> Faithfulness 从 0.62 提升到 0.81。

原因：当前项目已经有真实 Ragas 基线，但还没有完成一轮从 0.62 到 0.81 的真实优化闭环。后续如果优化检索或提示词后分数确实提升，再写具体提升数字。
