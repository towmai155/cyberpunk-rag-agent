import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from statistics import mean

from ragas.dataset_schema import EvaluationDataset, SingleTurnSample
from ragas.evaluation import evaluate, LangchainEmbeddingsWrapper, LangchainLLMWrapper
from ragas.metrics._answer_relevance import ResponseRelevancy
from ragas.metrics._context_precision import LLMContextPrecisionWithReference
from ragas.metrics._context_recall import LLMContextRecall
from ragas.metrics._faithfulness import Faithfulness

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model.factory import get_chat_model, get_embedding_model
from rag.rag_service import RagSummarizeService


DEFAULT_SET = ROOT / "evals" / "cyberpunk_golden_30.json"
LATEST_RESULT = ROOT / "evals" / "ragas_latest_result.json"
HISTORY_DIR = ROOT / "evals" / "history"


METRIC_COLUMNS = [
    "faithfulness",
    "answer_relevancy",
    "context_recall",
    "llm_context_precision_with_reference",
]


def load_cases(path: Path, limit: int | None = None) -> list[dict]:
    cases = json.loads(path.read_text(encoding="utf-8"))
    if limit:
        return cases[:limit]
    return cases


def build_dataset(cases: list[dict], max_context_chars: int) -> tuple[EvaluationDataset, list[dict]]:
    rag = RagSummarizeService()
    samples = []
    traces = []
    for case in cases:
        question = case["question"]
        docs = rag.retriever_docs(question)
        contexts = [doc.page_content[:max_context_chars] for doc in docs]
        answer = rag.rag_summarize(question)
        samples.append(
            SingleTurnSample(
                user_input=question,
                retrieved_contexts=contexts,
                response=answer,
                reference=case["reference"],
            )
        )
        traces.append(
            {
                "id": case["id"],
                "question": question,
                "reference": case["reference"],
                "answer": answer,
                "contexts": contexts,
                "sources": [doc.metadata for doc in docs],
            }
        )
    return EvaluationDataset(samples=samples), traces


def safe_float(value):
    try:
        if value != value:
            return None
        return float(value)
    except Exception:
        return None


def summarize(rows: list[dict]) -> dict:
    summary = {}
    for metric in METRIC_COLUMNS:
        values = [safe_float(row.get(metric)) for row in rows]
        values = [value for value in values if value is not None]
        summary[metric] = round(mean(values), 4) if values else None
    valid = [value for value in summary.values() if value is not None]
    summary["average"] = round(mean(valid), 4) if valid else None
    return summary


def load_previous() -> dict | None:
    if not LATEST_RESULT.exists():
        return None
    try:
        return json.loads(LATEST_RESULT.read_text(encoding="utf-8"))
    except Exception:
        return None


def deltas(current: dict, previous: dict | None, current_case_count: int, current_golden_set: str) -> dict:
    if not previous:
        return {}
    previous_run = previous.get("run", {})
    if previous_run.get("case_count") != current_case_count:
        return {}
    if previous_run.get("golden_set") != current_golden_set:
        return {}
    previous_summary = previous.get("summary", {})
    result = {}
    for metric, value in current.items():
        old_value = previous_summary.get(metric)
        if isinstance(value, (int, float)) and isinstance(old_value, (int, float)):
            result[metric] = round(value - old_value, 4)
    return result


def write_results(payload: dict) -> Path:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = payload["run"]["timestamp"].replace(":", "").replace("-", "").replace("T", "_")
    history_path = HISTORY_DIR / f"ragas_{timestamp}.json"
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    history_path.write_text(text, encoding="utf-8")
    LATEST_RESULT.write_text(text, encoding="utf-8")
    return history_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Ragas evaluation for the Cyberpunk RAG agent.")
    parser.add_argument("--set", default=str(DEFAULT_SET), help="Golden test set JSON path.")
    parser.add_argument("--limit", type=int, default=None, help="Only evaluate the first N cases.")
    parser.add_argument("--max-context-chars", type=int, default=1800, help="Max characters per retrieved context.")
    parser.add_argument("--batch-size", type=int, default=4, help="Ragas batch size.")
    args = parser.parse_args()

    cases = load_cases(Path(args.set), args.limit)
    previous = load_previous()
    dataset, traces = build_dataset(cases, args.max_context_chars)

    metrics = [
        Faithfulness(),
        ResponseRelevancy(),
        LLMContextRecall(),
        LLMContextPrecisionWithReference(),
    ]
    result = evaluate(
        dataset,
        metrics=metrics,
        llm=LangchainLLMWrapper(get_chat_model(), bypass_n=True),
        embeddings=LangchainEmbeddingsWrapper(get_embedding_model()),
        raise_exceptions=False,
        show_progress=True,
        batch_size=args.batch_size,
    )
    rows = result.to_pandas().to_dict(orient="records")
    for row, trace in zip(rows, traces):
        row["id"] = trace["id"]
        row["sources"] = trace["sources"]

    summary = summarize(rows)
    payload = {
        "run": {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "golden_set": str(Path(args.set)),
            "case_count": len(cases),
            "metrics": METRIC_COLUMNS,
            "tool": "ragas==0.4.3",
        },
        "summary": summary,
        "delta_from_previous": deltas(summary, previous, len(cases), str(Path(args.set))),
        "rows": rows,
        "traces": traces,
    }
    history_path = write_results(payload)

    print(json.dumps({"summary": summary, "history": str(history_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
