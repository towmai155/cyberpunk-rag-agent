import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag.rag_service import RagSummarizeService


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").lower())


def terms(text: str) -> set[str]:
    normalized = (text or "").lower()
    base_terms = set(re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9]+", normalized))
    compact = normalize_text(text)
    if re.search(r"[\u4e00-\u9fff]", compact):
        for size in (2, 3, 4):
            base_terms.update(compact[index:index + size] for index in range(0, max(len(compact) - size + 1, 0)))
    return {term for term in base_terms if term not in {"参考来源", "知识库", "资料", "回答"}}


def keyword_group_hit(text: str, keyword_or_group) -> bool:
    normalized = normalize_text(text)
    if isinstance(keyword_or_group, list):
        return any(normalize_text(str(keyword)) in normalized for keyword in keyword_or_group)
    return normalize_text(str(keyword_or_group)) in normalized


def keyword_recall(text: str, keyword_groups: list) -> tuple[int, int, list]:
    hits = [group for group in keyword_groups if keyword_group_hit(text, group)]
    missing = [group for group in keyword_groups if group not in hits]
    return len(hits), len(keyword_groups), missing


def is_relevant_context(doc_text: str, keyword_groups: list) -> bool:
    return any(keyword_group_hit(doc_text, group) for group in keyword_groups)


def average_precision(relevance_flags: list[bool]) -> float:
    relevant_seen = 0
    precision_sum = 0.0
    for index, relevant in enumerate(relevance_flags, start=1):
        if not relevant:
            continue
        relevant_seen += 1
        precision_sum += relevant_seen / index
    if relevant_seen == 0:
        return 0.0
    return precision_sum / relevant_seen


def split_answer_sentences(answer: str) -> list[str]:
    body = answer.split("\n参考来源：", 1)[0]
    raw_sentences = re.split(r"(?<=[。！？!?])\s*|\n+", body)
    return [sentence.strip() for sentence in raw_sentences if len(sentence.strip()) >= 6]


def sentence_supported(sentence: str, context_text: str) -> bool:
    sentence_terms = terms(sentence)
    if not sentence_terms:
        return True
    context_terms = terms(context_text)
    overlap = len(sentence_terms & context_terms)
    coverage = overlap / max(len(sentence_terms), 1)
    return coverage >= 0.35 or overlap >= 3


def faithfulness(answer: str, context_text: str) -> tuple[float, int, int, list[str]]:
    sentences = split_answer_sentences(answer)
    if not sentences:
        return 0.0, 0, 0, []
    unsupported = [sentence for sentence in sentences if not sentence_supported(sentence, context_text)]
    supported_count = len(sentences) - len(unsupported)
    return supported_count / len(sentences), supported_count, len(sentences), unsupported


def source_hit(answer: str, expected_sources: list[str]) -> tuple[int, int, list[str]]:
    hits = [source for source in expected_sources if normalize_text(source) in normalize_text(answer)]
    missing = [source for source in expected_sources if source not in hits]
    return len(hits), len(expected_sources), missing


def evaluate_case(service: RagSummarizeService, case: dict) -> dict:
    question = case["question"]
    expected_keywords = case.get("expected_keywords") or []
    expected_sources = case.get("expected_sources") or []

    docs = service.retriever_docs(question)
    context_texts = [doc.page_content for doc in docs]
    context_text = "\n\n".join(context_texts)
    answer = service.rag_summarize(question)

    relevance_flags = [is_relevant_context(text, expected_keywords) for text in context_texts]
    context_precision = average_precision(relevance_flags)
    raw_context_precision = sum(relevance_flags) / max(len(relevance_flags), 1)

    context_hits, context_total, missing_context_keywords = keyword_recall(context_text, expected_keywords)
    answer_hits, answer_total, missing_answer_keywords = keyword_recall(answer, expected_keywords)
    source_hits, source_total, missing_sources = source_hit(answer, expected_sources)
    faithful_score, supported_sentences, total_sentences, unsupported_sentences = faithfulness(answer, context_text)

    return {
        "id": case.get("id"),
        "question": question,
        "retrieved_contexts": len(docs),
        "relevant_context_flags": relevance_flags,
        "context_precision_ap": round(context_precision, 4),
        "context_precision_raw": round(raw_context_precision, 4),
        "context_recall": round(context_hits / max(context_total, 1), 4),
        "context_keyword_hits": context_hits,
        "context_keyword_total": context_total,
        "answer_relevancy": round(answer_hits / max(answer_total, 1), 4),
        "answer_keyword_hits": answer_hits,
        "answer_keyword_total": answer_total,
        "faithfulness": round(faithful_score, 4),
        "supported_sentences": supported_sentences,
        "total_sentences": total_sentences,
        "source_recall": round(source_hits / max(source_total, 1), 4),
        "source_hits": source_hits,
        "source_total": source_total,
        "missing_context_keywords": missing_context_keywords,
        "missing_answer_keywords": missing_answer_keywords,
        "missing_sources": missing_sources,
        "unsupported_sentences": unsupported_sentences[:5],
        "sources": [
            {
                "source": doc.metadata.get("source"),
                "page": doc.metadata.get("page"),
                "chunk_index": doc.metadata.get("chunk_index"),
                "relevance_score": doc.metadata.get("relevance_score"),
                "keyword_score": doc.metadata.get("keyword_score"),
                "rerank_score": doc.metadata.get("rerank_score"),
            }
            for doc in docs
        ],
        "answer_preview": answer[:500],
    }


def mean(values: list[float]) -> float:
    return round(sum(values) / max(len(values), 1), 4)


def main():
    parser = argparse.ArgumentParser(description="Evaluate RAG quality metrics with deterministic heuristics.")
    parser.add_argument("--cases", default="evals/cyberpunk_eval_set.json")
    parser.add_argument("--output", default="evals/latest_quality_result.json")
    args = parser.parse_args()

    cases_path = Path(args.cases)
    if not cases_path.is_absolute():
        cases_path = PROJECT_ROOT / cases_path
    with open(cases_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    service = RagSummarizeService()
    results = [evaluate_case(service, case) for case in cases]
    summary = {
        "total": len(results),
        "context_precision_ap": mean([item["context_precision_ap"] for item in results]),
        "context_precision_raw": mean([item["context_precision_raw"] for item in results]),
        "context_recall": mean([item["context_recall"] for item in results]),
        "faithfulness": mean([item["faithfulness"] for item in results]),
        "answer_relevancy": mean([item["answer_relevancy"] for item in results]),
        "source_recall": mean([item["source_recall"] for item in results]),
    }

    print("SUMMARY")
    for key, value in summary.items():
        print(f"{key}: {value}")
    print("\nDETAILS")
    for item in results:
        print(
            f"{item['id']}: "
            f"context_precision_ap={item['context_precision_ap']} "
            f"context_recall={item['context_recall']} "
            f"faithfulness={item['faithfulness']} "
            f"answer_relevancy={item['answer_relevancy']} "
            f"source_recall={item['source_recall']}"
        )
        if item["missing_answer_keywords"] or item["unsupported_sentences"]:
            print(f"  missing_answer_keywords={item['missing_answer_keywords']}")
            print(f"  unsupported_sentences={item['unsupported_sentences']}")

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": results}, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
