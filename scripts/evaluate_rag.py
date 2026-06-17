import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag.rag_service import RagSummarizeService


def load_cases(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("评测集必须是 JSON 数组。")
    return data


def score_case(answer: str, case: dict) -> dict:
    expected_keywords = case.get("expected_keywords") or []
    expected_sources = case.get("expected_sources") or []

    def keyword_group_hit(keyword_or_group):
        if isinstance(keyword_or_group, list):
            return any(str(keyword).lower() in answer.lower() for keyword in keyword_or_group)
        return str(keyword_or_group).lower() in answer.lower()

    keyword_hits = [keyword for keyword in expected_keywords if keyword_group_hit(keyword)]
    source_hits = [source for source in expected_sources if source.lower() in answer.lower()]

    return {
        "id": case.get("id"),
        "question": case.get("question"),
        "keyword_hits": len(keyword_hits),
        "keyword_total": len(expected_keywords),
        "source_hits": len(source_hits),
        "source_total": len(expected_sources),
        "passed": len(keyword_hits) == len(expected_keywords) and len(source_hits) == len(expected_sources),
        "missing_keywords": [keyword for keyword in expected_keywords if keyword not in keyword_hits],
        "missing_sources": [source for source in expected_sources if source not in source_hits],
        "answer_preview": answer[:320],
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate RAG answers against a small regression set.")
    parser.add_argument("--cases", default="evals/cyberpunk_eval_set.json", help="Path to eval cases JSON.")
    parser.add_argument("--output", default="", help="Optional JSON output path.")
    args = parser.parse_args()

    cases_path = Path(args.cases)
    if not cases_path.is_absolute():
        cases_path = PROJECT_ROOT / cases_path

    service = RagSummarizeService()
    results = []
    for case in load_cases(cases_path):
        answer = service.rag_summarize(case["question"])
        result = score_case(answer, case)
        results.append(result)
        status = "PASS" if result["passed"] else "FAIL"
        print(f"[{status}] {result['id']} keyword={result['keyword_hits']}/{result['keyword_total']} source={result['source_hits']}/{result['source_total']}")
        if not result["passed"]:
            print(f"  missing_keywords={result['missing_keywords']}")
            print(f"  missing_sources={result['missing_sources']}")
            print(f"  answer={result['answer_preview']}")

    passed = sum(1 for result in results if result["passed"])
    summary = {
        "passed": passed,
        "total": len(results),
        "pass_rate": round(passed / max(len(results), 1), 4),
        "results": results,
    }
    print(f"SUMMARY passed={summary['passed']}/{summary['total']} pass_rate={summary['pass_rate']}")

    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = PROJECT_ROOT / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

    raise SystemExit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
