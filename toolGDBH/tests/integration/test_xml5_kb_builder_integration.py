from __future__ import annotations

import json
from pathlib import Path

from parser_normalizer import XML5KnowledgeBaseBuilder


def test_builder_should_export_parsed_chunks_and_manifest(tmp_path: Path) -> None:
    input_file = tmp_path / "xml5_note_records.jsonl"
    output_root = tmp_path / "knowledge-base"
    input_file.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "claim_id": "HS001",
                        "note_id": "XML5-1",
                        "source_file_type": "XML5",
                        "source_file_name": "fixture.xml",
                        "facility_id": "79001",
                        "patient_id": "BN001",
                        "encounter_id": "HS001",
                        "department_code": "K01",
                        "department_name": None,
                        "practitioner_id": "BS001",
                        "practitioner_name": None,
                        "recorded_at": "2026-03-28T08:30:00",
                        "recorded_date": "2026-03-28",
                        "admission_time": "2026-03-28T08:00:00",
                        "discharge_time": "2026-03-29T10:00:00",
                        "primary_diagnosis_code": "C50",
                        "primary_diagnosis_text": None,
                        "secondary_diagnosis_codes": [],
                        "secondary_diagnosis_texts": [],
                        "clinical_text": "Bệnh nhân mệt, ăn kém, hóa chất Navelbin ngày 2.",
                        "clinical_text_normalized": "Bệnh nhân mệt, ăn kém, hóa chất Navelbin ngày 2.",
                        "note_type": "progress_note",
                        "context_tags": ["met moi", "an kem", "hoa chat"],
                        "linked_line_ids": ["XML2-1"],
                        "linked_item_codes": ["TH001"],
                        "linked_result_ids": [],
                        "evidence_flags": {
                            "has_diagnosis_context": True,
                            "has_treatment_context": True,
                            "has_procedure_context": False,
                            "has_lab_context": False,
                            "has_imaging_context": False,
                        },
                        "parser_version": "parser-xml5-0.1.0",
                        "raw_ref": {
                            "file_hoso_id": "XML5",
                            "xml_node_path": "DSACH_CHI_TIET_DIEN_BIEN_BENH/CHI_TIET_DIEN_BIEN_BENH",
                        },
                    },
                    ensure_ascii=False,
                )
            ]
        ),
        encoding="utf-8",
    )

    manifest = XML5KnowledgeBaseBuilder().export(input_file, output_root)

    parsed_path = output_root / "parsed" / "xml5_note_records.parsed.jsonl"
    chunks_path = output_root / "chunks" / "xml5_note_records.chunks.jsonl"
    queries_path = output_root / "queries" / "xml5_note_records.queries.jsonl"
    manifest_path = output_root / "manifests" / "xml5_note_records.manifest.json"

    assert manifest.input_record_count == 1
    assert parsed_path.exists()
    assert chunks_path.exists()
    assert queries_path.exists()
    assert manifest_path.exists()

    parsed_row = json.loads(parsed_path.read_text(encoding="utf-8").splitlines()[0])
    chunk_row = json.loads(chunks_path.read_text(encoding="utf-8").splitlines()[0])
    query_row = json.loads(queries_path.read_text(encoding="utf-8").splitlines()[0])
    manifest_row = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert parsed_row["parsed_document_id"] == "xml5:HS001:XML5-1"
    assert parsed_row["source_type"] == "xml5_note"
    assert parsed_row["structured_fields"]["keywords"] == ["met moi", "an kem", "hoa chat", "progress_note"]
    assert chunk_row["chunk_type"] == "clinical_note_pattern"
    assert chunk_row["metadata"]["codes"] == ["TH001", "C50"]
    assert chunk_row["metadata"]["evidence_required"] == ["xml5_note", "claim_line"]
    assert query_row["query_type"] == "clinical_context_lookup"
    assert query_row["note_id"] == "XML5-1"
    assert query_row["codes"] == ["TH001", "C50"]
    assert query_row["filters"]["source_types"] == ["xml5_note", "legal", "guideline", "catalog", "historical_decision"]
    assert manifest_row["chunk_count"] == 1
    assert manifest_row["query_count"] == 1
    assert manifest_row["notes_without_tags"] == 0
