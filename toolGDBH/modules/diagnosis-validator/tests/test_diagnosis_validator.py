from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "shared" / "types"))
sys.path.insert(0, str(PROJECT_ROOT / "modules" / "diagnosis-validator" / "src"))

from claim_models import ClaimHeader, ClaimLine, ClinicalNote, ClinicalResult, ParsedClaim
from diagnosis_validator import DiagnosisGuidelineProfile, DiagnosisValidatorService


def test_service_should_build_case_record_from_parsed_claim() -> None:
    claim = ParsedClaim(
        header=ClaimHeader(
            claim_id="HS001",
            facility_id="79001",
            patient_id="BN001",
            insurance_card_no="TE001",
            visit_type="03",
            admission_time="2026-03-30T08:00:00",
            discharge_time="2026-03-30T12:00:00",
            primary_diagnosis_code="C50",
            route_code="1",
            total_amount=Decimal("300000"),
            insurance_amount=Decimal("240000"),
            patient_pay_amount=Decimal("60000"),
            claim_effective_date="2026-03-30",
            secondary_diagnosis_codes=["D64.9"],
        ),
        lines=[
            ClaimLine(
                line_id="L001",
                claim_id="HS001",
                line_type="service",
                item_code="12.0001",
                item_name="CT sọ não",
                quantity=Decimal("1"),
                unit_price=Decimal("100000"),
                amount=Decimal("100000"),
                execution_time="2026-03-30T09:00:00",
            ),
            ClaimLine(
                line_id="L002",
                claim_id="HS001",
                line_type="drug",
                item_code="40P.26",
                item_name="Na131I",
                quantity=Decimal("1"),
                unit_price=Decimal("200000"),
                amount=Decimal("200000"),
                execution_time="2026-03-30T10:00:00",
            ),
        ],
        clinical_notes=[
            ClinicalNote(
                note_id="XML5-1",
                claim_id="HS001",
                note_text="Benh nhan met moi, dau dau, nghi di can nao.",
                note_time="2026-03-30T08:30:00",
                source_xml="XML5",
                source_node_path="XML5/NOTE",
            )
        ],
        clinical_results=[
            ClinicalResult(
                result_id="XML4-1",
                claim_id="HS001",
                service_code="CT-SO-NAO",
                indicator_name="CT sọ não",
                conclusion="Hinh anh goi y di can nao",
                result_time="2026-03-30T09:30:00",
            )
        ],
    )
    service = DiagnosisValidatorService()

    record = service.build_case_record(claim)

    assert record.claim_id == "HS001"
    assert record.primary_diagnosis_code == "C50"
    assert record.secondary_diagnosis_codes == ["D64.9"]
    assert "12.0001" in record.service_codes
    assert "40P.26" in record.drug_codes
    assert "CT-SO-NAO" in record.result_codes
    assert "met" in record.clinical_keywords
    assert "can" in record.result_keywords or "nao" in record.result_keywords
    assert "XML5-1" in record.note_refs
    assert len(record.timeline_refs) == 4


def test_service_should_save_and_load_profiles(tmp_path: Path) -> None:
    profile_path = tmp_path / "profiles.jsonl"
    service = DiagnosisValidatorService()
    profiles = [
        DiagnosisGuidelineProfile(
            profile_id="DX.C50.001",
            diagnosis_codes=["C50"],
            diagnosis_label="Ung thu vu",
            required_symptoms=["u vu", "hach nach"],
            required_tests=["GPB", "CDHA"],
        )
    ]

    service.save_profiles(profiles, profile_path)
    loaded = service.load_profiles(profile_path)

    assert len(loaded) == 1
    assert loaded[0].profile_id == "DX.C50.001"
    assert loaded[0].diagnosis_codes == ["C50"]
    assert loaded[0].required_tests == ["GPB", "CDHA"]


def test_service_should_create_empty_validation_result() -> None:
    service = DiagnosisValidatorService()

    result = service.build_empty_validation_result("HS001", "C50", "DX.C50.001")

    assert result.claim_id == "HS001"
    assert result.diagnosis_code == "C50"
    assert result.profile_id == "DX.C50.001"
    assert result.validation_status == "missing_evidence"
    assert result.recommended_action == "request_more"


def test_service_should_validate_case_record_against_matching_profile() -> None:
    service = DiagnosisValidatorService()
    case_record = service.load_case_records(
        PROJECT_ROOT / "runtime" / "diagnosis-validation" / "case-records" / "diagnosis_case_records.jsonl"
    )[0]
    profiles = service.load_profiles(
        PROJECT_ROOT / "runtime" / "diagnosis-validation" / "profiles" / "sample_diagnosis_profiles.jsonl"
    )

    result = service.validate_case_record(case_record, profiles)

    assert result.profile_id == "DX.C50.001"
    assert result.validation_status in {"strong_match", "partial_match"}
    assert result.recommended_action in {"accept", "review"}


def test_service_should_return_missing_profile_when_no_profile_matches() -> None:
    service = DiagnosisValidatorService()
    record = service.load_case_records(
        PROJECT_ROOT / "runtime" / "diagnosis-validation" / "case-records" / "diagnosis_case_records.jsonl"
    )[0]
    record.primary_diagnosis_code = "Z99"

    result = service.validate_case_record(record, [])

    assert result.validation_status == "missing_profile"
    assert result.profile_id is None


def test_service_should_not_trigger_exclusion_on_scattered_tokens() -> None:
    service = DiagnosisValidatorService()
    case_record = service.load_case_records(
        PROJECT_ROOT / "runtime" / "diagnosis-validation" / "case-records" / "diagnosis_case_records.jsonl"
    )[2]
    profiles = service.load_profiles(
        PROJECT_ROOT / "runtime" / "diagnosis-validation" / "profiles" / "sample_diagnosis_profiles.jsonl"
    )

    result = service.validate_case_record(case_record, profiles)

    assert "khong thay khoi u phoi" not in result.conflicting_evidence
    assert result.validation_status in {"strong_match", "partial_match"}
