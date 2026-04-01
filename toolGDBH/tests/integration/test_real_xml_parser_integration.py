from __future__ import annotations

import os
from pathlib import Path

import pytest

from deterministic_rule_engine import DeterministicRuleEngine
from parser_normalizer import ParserNormalizerService
from rule_registry import RuleRegistry


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REAL_XML_FIXTURE = Path(
    os.getenv(
        "TOOLGDBH_DEFAULT_XML_FILE",
        PROJECT_ROOT / "xulyXML" / "XML" / "data_112645_HT3382796012783_25029071_3176.xml",
    )
)
RULE_FILE = PROJECT_ROOT / "modules" / "rule-registry" / "config" / "rules.mwp.json"


def _require_real_fixture() -> Path:
    if not REAL_XML_FIXTURE.exists():
        pytest.skip(f"Khong tim thay real XML fixture: {REAL_XML_FIXTURE}")
    return REAL_XML_FIXTURE


def test_parser_should_extract_xml2_xml3_xml4_xml5_from_real_fixture() -> None:
    service = ParserNormalizerService()

    result = service.parse_file(_require_real_fixture())

    assert result.header.claim_id == "112645"
    assert any(line.source_xml == "XML2" and line.item_code == "40.1021" for line in result.lines)
    assert any(line.source_xml == "XML3" and line.item_code == "12.33" for line in result.lines)
    assert any(
        line.source_xml == "XML3"
        and line.item_code == "23.0058.1487"
        and line.equipment_ref == "SH.1.19C112;31E411"
        for line in result.lines
    )
    assert any(
        item.source_xml == "XML4"
        and item.service_code == "23.0166.1494"
        and item.indicator_name == "Urê"
        for item in result.clinical_results
    )
    assert any(
        note.source_xml == "XML5"
        and note.practitioner_id == "004334/TH-CCHN"
        and "Nhập viện điều trị" in note.note_text
        for note in result.clinical_notes
    )
    assert {doc.document_type for doc in result.documents} >= {
        "XML1",
        "XML2",
        "XML3",
        "XML4",
        "XML5",
        "XML7",
        "XML8",
        "XML14",
    }


def test_real_fixture_should_not_trigger_clinical_context_rule() -> None:
    claim = ParserNormalizerService().parse_file(_require_real_fixture())
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)

    result = engine.evaluate(claim, "2026-03-30")

    assert all(hit.rule_id != "LOGIC.CLINICAL_CONTEXT.001" for hit in result.hits)


def test_parser_should_build_xml5_note_records_from_real_xml_directory() -> None:
    xml_dir = REAL_XML_FIXTURE.parent
    if not xml_dir.exists():
        pytest.skip(f"Khong tim thay thu muc XML: {xml_dir}")

    records = ParserNormalizerService().build_xml5_note_records_from_directory(xml_dir)

    assert records
    assert any(record.source_file_type == "XML5" for record in records)
    assert any(record.recorded_at for record in records)
    assert any(record.clinical_text for record in records)
