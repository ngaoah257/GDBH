from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "modules" / "guideline-rule-builder" / "src"))

from guideline_rule_builder import GuidelineRuleBuilderService


def _write_minimal_docx(path: Path, paragraphs: list[str]) -> None:
    body = "".join(
        f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"
        for text in paragraphs
    )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", document_xml)


def test_service_should_build_candidates_from_docx(tmp_path: Path) -> None:
    docx_path = tmp_path / "guideline.docx"
    _write_minimal_docx(
        docx_path,
        [
            "Hướng dẫn điều trị ung thư vú",
            "Chỉ định: Dùng thuốc TH001 cho bệnh nhân C50.",
            "Chống chỉ định: Không dùng khi men gan tăng cao.",
        ],
    )

    raw_document, candidates = GuidelineRuleBuilderService().build_candidates_from_docx(docx_path)

    assert raw_document.doc_id == "guideline"
    assert candidates
    assert candidates[0].statement_type_hint in {"indication", "unknown", "regimen"}
    assert any(candidate.statement_type_hint == "contraindication" for candidate in candidates)


def test_service_should_convert_doc_input_before_parsing(tmp_path: Path, monkeypatch) -> None:
    legacy_doc_path = tmp_path / "legacy.doc"
    converted_docx_path = tmp_path / ".converted-docx" / "legacy.docx"
    legacy_doc_path.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
    converted_docx_path.parent.mkdir(parents=True, exist_ok=True)
    _write_minimal_docx(
        converted_docx_path,
        [
            "Huong dan dieu tri ung thu vu",
            "Chi dinh: Dung thuoc TH001 cho benh nhan C50.",
        ],
    )

    service = GuidelineRuleBuilderService()

    def _fake_convert(path: Path) -> Path:
        assert path == legacy_doc_path
        return converted_docx_path

    monkeypatch.setattr(service, "_convert_doc_to_docx", _fake_convert)

    raw_document, candidates = service.build_candidates_from_word(legacy_doc_path)

    assert raw_document.source_path == str(legacy_doc_path)
    assert candidates
    assert all(candidate.source_path == str(legacy_doc_path) for candidate in candidates)


def test_service_should_filter_administrative_candidates_and_keep_medical_ones(tmp_path: Path) -> None:
    service = GuidelineRuleBuilderService()
    rows = [
        {
            "candidate_id": "1",
            "doc_id": "DOC",
            "source_path": "x.doc",
            "title": "QUYET DINH",
            "section_path": ["BO TRUONG BO Y TE"],
            "paragraph_index": 1,
            "statement_type_hint": "unknown",
            "source_text": "Can cu Luat Kham benh, chua benh nam 2009.",
            "source_section": "BO TRUONG BO Y TE",
        },
        {
            "candidate_id": "2",
            "doc_id": "DOC",
            "source_path": "x.doc",
            "title": "QUYET DINH",
            "section_path": ["Phan 2"],
            "paragraph_index": 2,
            "statement_type_hint": "unknown",
            "source_text": "Bai 33. Ung thu phoi te bao nho",
            "source_section": "Phan 2",
        },
        {
            "candidate_id": "3",
            "doc_id": "DOC",
            "source_path": "x.doc",
            "title": "QUYET DINH",
            "section_path": ["Dieu tri"],
            "paragraph_index": 3,
            "statement_type_hint": "requirement",
            "source_text": "Can theo doi xet nghiem chuc nang gan truoc dieu tri.",
            "source_section": "Dieu tri",
        },
        {
            "candidate_id": "4",
            "doc_id": "DOC",
            "source_path": "x.doc",
            "title": "QUYET DINH",
            "section_path": ["Phan 2"],
            "paragraph_index": 4,
            "statement_type_hint": "unknown",
            "source_text": "Bai 34. Ung thu vu",
            "source_section": "Phan 2",
        },
    ]
    tmp_input = tmp_path / "candidates.jsonl"
    tmp_input.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    filtered = service.filter_business_candidates(service.load_candidates(tmp_input))

    assert [candidate.candidate_id for candidate in filtered] == ["3"]


def test_service_should_build_rule_drafts_from_normalized_statements(tmp_path: Path) -> None:
    statements_path = tmp_path / "normalized.jsonl"
    statements_path.write_text(
        json.dumps(
            {
                "statement_id": "GS001",
                "doc_id": "DOC001",
                "statement_type": "requirement",
                "condition": {
                    "diagnosis_codes": ["C50"],
                    "clinical_context_tags": ["hoa chat"],
                    "demographics": [],
                    "timing_constraints": [],
                    "lab_constraints": [],
                    "procedure_constraints": [],
                },
                "recommended_action": {
                    "action_type": "require",
                    "target_codes": ["TH001"],
                    "target_groups": ["drug"],
                    "text": "Can co XML5 note hoa chat va ma TH001.",
                },
                "contraindication": {
                    "diagnosis_codes": [],
                    "clinical_context_tags": [],
                    "lab_constraints": [],
                    "text": None,
                },
                "required_evidence": [
                    {
                        "evidence_type": "xml5_note",
                        "codes": ["TH001"],
                        "keywords": ["hoa chat"],
                        "min_count": 1,
                        "time_window": "same_episode",
                    }
                ],
                "applies_to_codes": ["TH001"],
                "priority": 70,
                "source_quote": "Can co XML5 note hoa chat va ma TH001.",
                "source_section": "Muc 1",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    drafts_output, manifest_output = GuidelineRuleBuilderService().export_rule_drafts(
        statements_path,
        tmp_path,
    )

    draft_row = json.loads(drafts_output.read_text(encoding="utf-8").splitlines()[0])
    manifest_row = json.loads(manifest_output.read_text(encoding="utf-8"))

    assert draft_row["statement_id"] == "GS001"
    assert draft_row["rule_family"] == "GUIDELINE"
    assert draft_row["severity"] == "pending"
    assert draft_row["suggested_action"] == "request_more"
    assert draft_row["trigger"]["applies_to_codes"] == ["TH001"]
    assert manifest_row["record_count"] == 1


def test_service_should_apply_internal_code_mapping(tmp_path: Path) -> None:
    statements_path = tmp_path / "normalized.jsonl"
    statements_path.write_text(
        json.dumps(
            {
                "statement_id": "GS001",
                "doc_id": "DOC001",
                "statement_type": "requirement",
                "condition": {
                    "diagnosis_codes": [],
                    "clinical_context_tags": [],
                    "demographics": [],
                    "timing_constraints": [],
                    "lab_constraints": [],
                    "procedure_constraints": [],
                },
                "recommended_action": {
                    "action_type": "require",
                    "target_codes": ["CHEMO-INFUSION"],
                    "target_groups": ["service"],
                    "text": "Need infusion evidence.",
                },
                "contraindication": {
                    "diagnosis_codes": [],
                    "clinical_context_tags": [],
                    "lab_constraints": [],
                    "text": None,
                },
                "required_evidence": [
                    {
                        "evidence_type": "order",
                        "codes": ["CHEMO-INFUSION"],
                        "keywords": ["hoa chat"],
                        "min_count": 1,
                        "time_window": "same_day",
                    }
                ],
                "applies_to_codes": ["CHEMO-INFUSION"],
                "priority": 70,
                "source_quote": "Need infusion evidence.",
                "source_section": "Muc 1",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    mapping_path = tmp_path / "mapping.json"
    mapping_path.write_text(
        json.dumps(
            {
                "mappings": [
                    {
                        "placeholder_code": "CHEMO-INFUSION",
                        "mapped_code": "INT.SVC.CHEMO_INFUSION",
                        "item_type": "service",
                        "label": "Truyen hoa chat",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "normalized.mapped.jsonl"

    mapped_output, manifest_output = GuidelineRuleBuilderService().export_mapped_statements(
        statements_path,
        mapping_path,
        output_path,
    )

    mapped_row = json.loads(mapped_output.read_text(encoding="utf-8").splitlines()[0])
    manifest_row = json.loads(manifest_output.read_text(encoding="utf-8"))

    assert mapped_row["applies_to_codes"] == ["INT.SVC.CHEMO_INFUSION"]
    assert mapped_row["recommended_action"]["target_codes"] == ["INT.SVC.CHEMO_INFUSION"]
    assert mapped_row["required_evidence"][0]["codes"] == ["INT.SVC.CHEMO_INFUSION"]
    assert manifest_row["record_count"] == 1
