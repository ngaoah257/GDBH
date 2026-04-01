from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "shared" / "types"))
sys.path.insert(0, str(PROJECT_ROOT / "shared"))
sys.path.insert(0, str(PROJECT_ROOT / "modules" / "evidence-service" / "src"))

from evidence_service import EvidenceRetrievalService


def test_retrieval_service_should_rank_matching_chunk_first(tmp_path: Path) -> None:
    query_path = tmp_path / "queries.jsonl"
    chunks_path = tmp_path / "chunks.jsonl"

    query_path.write_text(
        json.dumps(
            {
                "query_id": "query:HS001:XML5-1",
                "claim_id": "HS001",
                "line_id": None,
                "note_id": "XML5-1",
                "query_type": "clinical_context_lookup",
                "effective_date": "2026-03-28",
                "specialties": ["ung_buou_vu"],
                "item_types": ["drug", "note"],
                "codes": ["TH001", "C50"],
                "instruction_text": "Tim boi canh lien quan.",
                "query_text": "chan doan: C50 | note_type: progress_note | context: hoa chat, met moi | codes: TH001 | Hoa chat Navelbin gay met moi.",
                "filters": {
                    "source_types": ["xml5_note"],
                    "facility_scope": ["79001"],
                    "effective_only": True,
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    chunks_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "chunk_id": "chunk-good",
                        "metadata": {
                            "source_type": "xml5_note",
                            "effective_from": "2026-03-28",
                            "effective_to": "2026-03-28",
                            "specialties": ["ung_buou_vu"],
                            "facility_scope": ["79001"],
                            "item_types": ["drug", "note"],
                            "codes": ["TH001", "C50"],
                            "keywords": ["hoa chat", "met moi", "progress_note"],
                            "priority": 70,
                        },
                        "text_chunk": "Hoa chat Navelbin gay met moi cho benh nhan C50.",
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "chunk_id": "chunk-weak",
                        "metadata": {
                            "source_type": "xml5_note",
                            "effective_from": "2026-03-28",
                            "effective_to": "2026-03-28",
                            "specialties": ["ung_buou_ho_hap"],
                            "facility_scope": ["79001"],
                            "item_types": ["note"],
                            "codes": ["C34"],
                            "keywords": ["dau nguc"],
                            "priority": 50,
                        },
                        "text_chunk": "Dau nguc o benh nhan C34.",
                    },
                    ensure_ascii=False,
                ),
            ]
        ),
        encoding="utf-8",
    )

    results = EvidenceRetrievalService().retrieve_from_files(query_path, chunks_path, top_k=3)

    assert len(results) == 1
    assert results[0].results
    assert results[0].results[0].chunk_id == "chunk-good"
    assert results[0].results[0].matched_codes == ["TH001", "C50"]
    assert "hoa chat" in results[0].results[0].matched_keywords
