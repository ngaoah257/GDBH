from __future__ import annotations

import json
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "shared" / "types"))
sys.path.insert(0, str(ROOT / "shared"))
sys.path.insert(0, str(ROOT / "modules" / "evidence-service" / "src"))

from evidence_service import EvidenceRetrievalService


def resolve_path_from_env(env_name: str, fallback_candidates: list[Path]) -> Path | None:
    raw_value = os.getenv(env_name, "").strip()
    if raw_value:
        return Path(raw_value)
    for candidate in fallback_candidates:
        if candidate.exists():
            return candidate
    return None


def expected_chunk_id_for_query(payload: dict) -> str:
    claim_id = str(payload.get("claim_id", "")).strip()
    note_id = str(payload.get("note_id", "")).strip()
    return f"xml5:{claim_id}:{note_id}:chunk:0"


def build_benchmark_summary(query_rows: list[dict], results: list[object]) -> dict[str, object]:
    summary_rows: list[dict[str, object]] = []
    hit_at_1 = 0
    hit_at_3 = 0
    hit_at_5 = 0
    reciprocal_rank_sum = 0.0

    query_by_id = {
        str(row.get("query_id", "")).strip(): row
        for row in query_rows
    }
    for result in results:
        query_row = query_by_id.get(result.query_id, {})
        expected_chunk_id = expected_chunk_id_for_query(query_row)
        ranks = {
            item.chunk_id: item.rank
            for item in result.results
        }
        matched_rank = ranks.get(expected_chunk_id)
        hit_at_1 += 1 if matched_rank == 1 else 0
        hit_at_3 += 1 if matched_rank is not None and matched_rank <= 3 else 0
        hit_at_5 += 1 if matched_rank is not None and matched_rank <= 5 else 0
        reciprocal_rank_sum += 0.0 if matched_rank is None else 1.0 / matched_rank
        summary_rows.append(
            {
                "query_id": result.query_id,
                "claim_id": query_row.get("claim_id"),
                "note_id": query_row.get("note_id"),
                "expected_chunk_id": expected_chunk_id,
                "matched_rank": matched_rank,
                "top_results": [item.chunk_id for item in result.results[:5]],
            }
        )

    query_count = len(results)
    return {
        "retriever_version": EvidenceRetrievalService.RETRIEVER_VERSION,
        "embedding_model": EvidenceRetrievalService.EMBEDDING_MODEL,
        "query_count": query_count,
        "hit_at_1": hit_at_1,
        "hit_at_3": hit_at_3,
        "hit_at_5": hit_at_5,
        "hit_at_1_rate": round(hit_at_1 / query_count, 4) if query_count else 0.0,
        "hit_at_3_rate": round(hit_at_3 / query_count, 4) if query_count else 0.0,
        "hit_at_5_rate": round(hit_at_5 / query_count, 4) if query_count else 0.0,
        "mrr": round(reciprocal_rank_sum / query_count, 4) if query_count else 0.0,
        "rows": summary_rows,
    }


def main() -> int:
    default_query_file = resolve_path_from_env(
        "TOOLGDBH_QUERY_JSONL",
        [ROOT / "runtime" / "knowledge-base" / "queries" / "xml5_note_records.queries.jsonl"],
    )
    default_chunks_file = resolve_path_from_env(
        "TOOLGDBH_CHUNKS_JSONL",
        [ROOT / "runtime" / "knowledge-base" / "chunks" / "xml5_note_records.chunks.jsonl"],
    )
    default_output_file = ROOT / "runtime" / "knowledge-base" / "retrieval" / "xml5_note_records.retrieval.jsonl"
    default_summary_file = ROOT / "runtime" / "knowledge-base" / "retrieval" / "xml5_note_records.benchmark.json"

    query_file = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default_query_file
    chunks_file = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else default_chunks_file
    output_file = Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else default_output_file.resolve()
    summary_file = Path(sys.argv[4]).resolve() if len(sys.argv) > 4 else default_summary_file.resolve()

    if query_file is None or not query_file.exists():
        print("Query jsonl not found.")
        return 1
    if chunks_file is None or not chunks_file.exists():
        print("Chunks jsonl not found.")
        return 1

    service = EvidenceRetrievalService()
    results = service.export_results(query_file, chunks_file, output_file, top_k=5)
    query_rows = service.load_jsonl(query_file)
    summary = build_benchmark_summary(query_rows, results)
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "query_file": str(query_file),
                "chunks_file": str(chunks_file),
                "output_file": str(output_file),
                "query_count": len(results),
                "summary_file": str(summary_file),
                "hit_at_1_rate": summary["hit_at_1_rate"],
                "mrr": summary["mrr"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
