from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "shared" / "types"))
sys.path.insert(0, str(PROJECT_ROOT / "shared"))
sys.path.insert(0, str(PROJECT_ROOT / "modules" / "parser-normalizer" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "modules" / "eligibility-service" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "modules" / "master-data-service" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "modules" / "deterministic-rule-engine" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "modules" / "diagnosis-validator" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "modules" / "evidence-service" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "modules" / "reviewer-workspace" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "modules" / "rule-registry" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "modules" / "case-triage" / "src"))

from reviewer_workspace import (
    ClinicalPolicyRecord,
    DiseaseLineDraftRecord,
    DiseaseProfileDraftRecord,
    DiseaseResultDraftRecord,
    PaymentPolicyRecord,
    ReviewerWorkspaceService,
    RuleEditorRecord,
)


def test_reviewer_workspace_service_should_load_and_update_rules(tmp_path: Path) -> None:
    rule_file = tmp_path / "rules.json"
    rule_file.write_text(
        json.dumps(
            [
                {
                    "rule_id": "RULE.001",
                    "rule_name": "Rule cu",
                    "rule_group": "master-data",
                    "severity": "warning",
                    "legal_basis": "Noi bo",
                    "effective_from": "2025-01-01",
                    "effective_to": None,
                    "input_scope": "line",
                    "decision_logic": "Logic cu",
                    "suggested_action": "warn",
                    "owner": "owner-a",
                    "enabled": True,
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    service = ReviewerWorkspaceService(rule_file)
    rules = service.list_rules()

    assert len(rules) == 1
    assert rules[0].rule_id == "RULE.001"

    service.update_rule(
        RuleEditorRecord(
            rule_id="RULE.001",
            rule_name="Rule moi",
            rule_group="clinical",
            severity="reject",
            legal_basis="Noi bo moi",
            effective_from="2025-02-01",
            effective_to=None,
            input_scope="claim",
            decision_logic="Logic moi",
            suggested_action="reject",
            owner="owner-b",
            enabled=False,
        )
    )

    updated_payload = json.loads(rule_file.read_text(encoding="utf-8"))
    assert updated_payload[0]["rule_name"] == "Rule moi"
    assert updated_payload[0]["enabled"] is False


def test_reviewer_workspace_service_should_load_and_save_payment_policy(tmp_path: Path) -> None:
    rule_file = tmp_path / "rules.json"
    rule_file.write_text("[]", encoding="utf-8")
    payment_policy_file = tmp_path / "payment_policy.json"
    payment_policy_file.write_text(
        json.dumps(
            {
                "source_ref": "payment-policy@test",
                "included_in_price_codes": {"service": [], "drug": [], "supply": ["VT001"]},
                "included_in_price_keywords": {"service": [], "drug": [], "supply": ["kim tiem"]},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    service = ReviewerWorkspaceService(rule_file, payment_policy_file=payment_policy_file)
    policy = service.get_payment_policy()

    assert policy.included_in_price_codes["supply"] == ["VT001"]

    service.save_payment_policy(
        PaymentPolicyRecord(
            source_ref="payment-policy@test2",
            included_in_price_codes={"service": ["DV001"], "drug": [], "supply": ["VT002"]},
            included_in_price_keywords={"service": ["kham"], "drug": [], "supply": []},
        )
    )

    updated_payload = json.loads(payment_policy_file.read_text(encoding="utf-8"))
    assert updated_payload["source_ref"] == "payment-policy@test2"
    assert updated_payload["included_in_price_codes"]["service"] == ["DV001"]


def test_reviewer_workspace_service_should_load_and_save_clinical_policy(tmp_path: Path) -> None:
    rule_file = tmp_path / "rules.json"
    rule_file.write_text("[]", encoding="utf-8")
    clinical_policy_file = tmp_path / "clinical_policy.json"
    clinical_policy_file.write_text(
        json.dumps(
            {
                "source_ref": "clinical-policy@test",
                "service_duplicate_thresholds": [{"group": "kham", "match_prefixes": ["12."], "max_per_day": 1}],
                "cls_duplicate_thresholds": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = ReviewerWorkspaceService(rule_file, clinical_policy_file=clinical_policy_file)
    policy = service.get_clinical_policy()

    assert policy.source_ref == "clinical-policy@test"
    assert policy.payload["service_duplicate_thresholds"]

    service.save_clinical_policy(
        ClinicalPolicyRecord(
            source_ref="clinical-policy@test2",
            payload={
                "source_ref": "clinical-policy@test2",
                "service_duplicate_thresholds": [{"group": "cls", "match_prefixes": ["22."], "max_per_day": 2}],
                "cls_duplicate_thresholds": [],
            },
        )
    )
    updated_payload = json.loads(clinical_policy_file.read_text(encoding="utf-8"))
    assert updated_payload["source_ref"] == "clinical-policy@test2"


def test_reviewer_workspace_service_should_append_disease_profile_to_clinical_policy(tmp_path: Path) -> None:
    rule_file = tmp_path / "rules.json"
    rule_file.write_text("[]", encoding="utf-8")
    clinical_policy_file = tmp_path / "clinical_policy.json"
    clinical_policy_file.write_text(
        json.dumps(
            {
                "source_ref": "clinical-policy@test",
                "drug_context_heuristics": [],
                "service_context_heuristics": [],
                "cls_context_heuristics": [],
                "department_context_heuristics": {},
                "diagnosis_context_aliases": {},
                "disease_profiles": [],
                "equipment_required_service_heuristics": [],
                "service_duplicate_thresholds": [],
                "cls_duplicate_thresholds": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = ReviewerWorkspaceService(rule_file, clinical_policy_file=clinical_policy_file)

    updated_policy = service.append_disease_profile(
        DiseaseProfileDraftRecord(
            profile_id="DX.C61.001",
            diagnosis_code_prefixes=["C61"],
            diagnosis_aliases=["ung thu tuyen tien liet", "psa"],
            department_codes=["K33"],
            department_context_keywords=["ung thu", "psa", "tuyen tien liet"],
            line_rules=[
                DiseaseLineDraftRecord(
                    line_rule_id="prostate_mri",
                    line_types=["service"],
                    line_item_codes=[],
                    line_item_code_prefixes=[],
                    line_item_name_keywords=["mri tuyen tien liet"],
                    line_department_codes=["K33"],
                    line_required_note_keywords=["psa", "xam lan"],
                    line_required_note_match="any",
                    line_context_label="mri danh gia ung thu tuyen tien liet",
                ),
                DiseaseLineDraftRecord(
                    line_rule_id="prostate_pain_support",
                    line_types=["drug"],
                    line_item_codes=[],
                    line_item_code_prefixes=[],
                    line_item_name_keywords=["giam dau"],
                    line_department_codes=["K33"],
                    line_required_note_keywords=["dau", "xuong"],
                    line_required_note_match="any",
                    line_context_label="ho tro giam dau",
                ),
            ],
            result_rules=[
                DiseaseResultDraftRecord(
                    result_rule_id="psa_followup",
                    result_service_codes=["23.PSA.0001"],
                    result_indicator_keywords=["psa"],
                    result_required_note_keywords=["psa", "theo doi"],
                    result_required_note_match="all",
                    result_context_label="theo doi chi so psa",
                )
            ],
        )
    )

    payload = updated_policy.to_dict()
    assert payload["disease_profiles"]
    assert payload["disease_profiles"][0]["profile_id"] == "DX.C61.001"
    assert payload["disease_profiles"][0]["department_context_keywords"]["K33"] == [
        "ung thu",
        "psa",
        "tuyen tien liet",
    ]
    assert len(payload["disease_profiles"][0]["line_rules"]) == 2
    assert payload["disease_profiles"][0]["line_rules"][0]["item_name_keywords"] == ["mri tuyen tien liet"]
    assert payload["disease_profiles"][0]["line_rules"][1]["line_types"] == ["drug"]
    assert payload["disease_profiles"][0]["result_rules"][0]["required_note_match"] == "all"


def test_reviewer_workspace_service_should_run_preview_on_real_xml() -> None:
    root = Path(__file__).resolve().parents[3]
    project_root = root
    xml_file = Path(
        os.getenv(
            "TOOLGDBH_DEFAULT_XML_FILE",
            root.parent / "xulyXML" / "XML" / "data_112645_HT3382796012783_25029071_3176.xml",
        )
    )
    rule_file = project_root / "modules" / "rule-registry" / "config" / "rules.mwp.json"
    catalog_dir = Path(os.getenv("TOOLGDBH_CATALOG_DIR", root.parent / "Danhmuc"))
    policy_file = project_root / "modules" / "eligibility-service" / "config" / "policy.mwp.json"
    payment_policy_file = (
        project_root / "modules" / "deterministic-rule-engine" / "config" / "payment_policy.mwp.json"
    )

    if not xml_file.exists() or not catalog_dir.exists():
        pytest.skip("Khong tim thay du lieu real XML hoac Danhmuc de test preview.")

    service = ReviewerWorkspaceService(
        rule_file,
        catalog_dir,
        policy_file,
        payment_policy_file,
    )
    preview = service.run_preview(xml_file, "2026-03-30")

    assert preview.claim.header.claim_id
    assert preview.xml_file == xml_file.resolve()
    assert preview.effective_rule_count > 0
    assert preview.triage_result.claim_id == preview.claim.header.claim_id


def test_reviewer_workspace_service_should_run_xml5_retrieval_preview() -> None:
    root = Path(__file__).resolve().parents[3]
    project_root = root
    xml_file = Path(
        os.getenv(
            "TOOLGDBH_DEFAULT_XML_FILE",
            root.parent / "xulyXML" / "XML" / "data_112645_HT3382796012783_25029071_3176.xml",
        )
    )
    kb_chunks_file = (
        project_root / "runtime" / "knowledge-base" / "chunks" / "xml5_note_records.chunks.jsonl"
    )
    rule_file = project_root / "modules" / "rule-registry" / "config" / "rules.mwp.json"

    if not xml_file.exists() or not kb_chunks_file.exists():
        pytest.skip("Khong tim thay du lieu XML hoac knowledge-base chunks de test retrieval preview.")

    service = ReviewerWorkspaceService(
        rule_file,
        kb_chunks_file=kb_chunks_file,
    )
    result = service.run_xml5_retrieval_preview(xml_file, "2026-03-30")

    assert result.xml_file == xml_file.resolve()
    assert result.note_records
    assert len(result.note_records) == len(result.retrieval_results)
    assert any(item.results for item in result.retrieval_results)


def test_reviewer_workspace_service_should_count_guideline_drafts(tmp_path: Path) -> None:
    rule_file = tmp_path / "rules.json"
    rule_file.write_text("[]", encoding="utf-8")
    drafts_file = tmp_path / "guideline_rule_drafts.jsonl"
    drafts_file.write_text('{"draft_rule_id":"GL.001"}\n{"draft_rule_id":"GL.002"}\n', encoding="utf-8")

    service = ReviewerWorkspaceService(
        rule_file,
        guideline_rule_drafts_file=drafts_file,
    )

    assert service.guideline_draft_count() == 2


def test_reviewer_workspace_service_should_include_diagnosis_validation_in_preview(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    project_root = root
    xml_file = Path(
        os.getenv(
            "TOOLGDBH_DEFAULT_XML_FILE",
            root.parent / "xulyXML" / "XML" / "data_112645_HT3382796012783_25029071_3176.xml",
        )
    )
    catalog_dir = Path(os.getenv("TOOLGDBH_CATALOG_DIR", root.parent / "Danhmuc"))
    if not xml_file.exists() or not catalog_dir.exists():
        pytest.skip("Khong tim thay du lieu real XML hoac Danhmuc de test diagnosis validation preview.")

    rule_file = project_root / "modules" / "rule-registry" / "config" / "rules.mwp.json"
    policy_file = project_root / "modules" / "eligibility-service" / "config" / "policy.mwp.json"
    payment_policy_file = (
        project_root / "modules" / "deterministic-rule-engine" / "config" / "payment_policy.mwp.json"
    )
    diagnosis_profiles_file = (
        project_root / "tests" / "fixtures" / "diagnosis" / "sample_diagnosis_profiles.jsonl"
    )

    service = ReviewerWorkspaceService(
        rule_file,
        catalog_dir,
        policy_file,
        payment_policy_file,
        diagnosis_profiles_file=diagnosis_profiles_file,
    )
    preview = service.run_preview(xml_file, "2026-03-30")

    assert preview.diagnosis_validation_results is not None
    assert len(preview.diagnosis_validation_results) == 1
