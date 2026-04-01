from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from claim_models import (
    ClinicalNote,
    ClinicalResult,
    ClaimHeader,
    ClaimLine,
    DrugItem,
    EquipmentItem,
    MasterDataSnapshot,
    ParsedClaim,
    ServiceItem,
    StaffMember,
    SupplyItem,
)
from deterministic_rule_engine import DeterministicRuleEngine
from eligibility_service import EligibilityService
from parser_normalizer import ParserNormalizerService
from rule_registry import RuleRegistry


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "tests" / "fixtures" / "sample_giamdinhhs.xml"
RULE_FILE = ROOT / "modules" / "rule-registry" / "config" / "rules.mwp.json"
POLICY_FILE = ROOT / "modules" / "eligibility-service" / "config" / "policy.mwp.json"
PAYMENT_RULES_FILE = ROOT / "modules" / "deterministic-rule-engine" / "config" / "payment_rules.mwp.json"


def test_engine_should_return_no_hit_for_valid_sample() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)

    result = engine.evaluate(claim, "2026-03-30")

    assert result.claim_id == "HS001"
    assert result.hits == []


def test_engine_should_return_reject_hit_for_invalid_card() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.header.insurance_card_no = "INVALID-001"
    registry = RuleRegistry.from_json_file(RULE_FILE)
    eligibility = EligibilityService.from_json_file(POLICY_FILE).evaluate(claim.header)
    engine = DeterministicRuleEngine(registry)

    result = engine.evaluate(claim, "2026-03-30", eligibility)

    assert len(result.hits) == 1
    assert result.hits[0].rule_id == "ELIG.CARD_STATUS.001"
    assert result.hits[0].estimated_amount_impact == Decimal("240000")


def test_engine_should_warn_when_line_amount_formula_mismatched() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].quantity = Decimal("2")
    claim.lines[0].unit_price = Decimal("100000")
    claim.lines[0].amount = Decimal("150000")
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)

    result = engine.evaluate(claim, "2026-03-30")

    assert any(
        hit.rule_id == "STRUCT.LINE_AMOUNT.001"
        and hit.line_id == claim.lines[0].line_id
        and hit.estimated_amount_impact == Decimal("50000")
        for hit in result.hits
    )


def test_engine_should_warn_when_admission_after_discharge() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.header.admission_time = "2026-03-31T10:00:00"
    claim.header.discharge_time = "2026-03-30T10:00:00"
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)

    result = engine.evaluate(claim, "2026-03-30")

    assert any(hit.rule_id == "STRUCT.ADMISSION_DISCHARGE.001" for hit in result.hits)


def test_engine_should_warn_when_link_key_mismatched_between_tables() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].claim_id = "HS999"
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)

    result = engine.evaluate(claim, "2026-03-30")

    assert any(
        hit.rule_id == "STRUCT.LINK_KEY.001"
        and hit.line_id == claim.lines[0].line_id
        for hit in result.hits
    )


def test_default_payment_rules_config_should_ship_non_empty_matchers_for_pay_rules() -> None:
    payload = json.loads(PAYMENT_RULES_FILE.read_text(encoding="utf-8"))
    rules = {item["rule_id"]: item for item in payload["rules"]}

    assert rules["PAY.OUT_OF_SCOPE.001"]["matchers"]
    assert any(matcher.get("entries") for matcher in rules["PAY.OUT_OF_SCOPE.001"]["matchers"])
    assert any(matcher.get("entries") for matcher in rules["PAY.LIMIT.COVERAGE_PERCENT.001"]["matchers"])
    assert any(matcher.get("entries") for matcher in rules["PAY.LIMIT.UNIT_PRICE_MAX.001"]["matchers"])
    assert any(matcher.get("entries") for matcher in rules["PAY.LIMIT.QUANTITY_MAX.001"]["matchers"])
    assert any(matcher.get("entries") for matcher in rules["PAY.LIMIT.AMOUNT_MAX.001"]["matchers"])


def test_default_payment_rules_config_should_trigger_out_of_scope_keyword_match() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].item_name = "Dich vu theo yeu cau"
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry, payment_rules_file=PAYMENT_RULES_FILE)

    result = engine.evaluate(claim, "2026-03-30")

    assert any(
        hit.rule_id == "PAY.OUT_OF_SCOPE.001" and hit.line_id == claim.lines[0].line_id
        for hit in result.hits
    )


def test_default_payment_rules_config_should_trigger_limit_rules() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].item_code = "DV.UNITMAX.001"
    claim.lines[0].item_name = "DV max"
    claim.lines[0].quantity = Decimal("3")
    claim.lines[0].unit_price = Decimal("120000")
    claim.lines[0].amount = Decimal("360000")
    claim.lines[1].item_code = "TH.COVER.001"
    claim.lines[1].item_name = "Thuoc coverage"
    claim.lines[1].quantity = Decimal("4")
    claim.lines[1].unit_price = Decimal("50000")
    claim.lines[1].amount = Decimal("200000")
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry, payment_rules_file=PAYMENT_RULES_FILE)

    result = engine.evaluate(claim, "2026-03-30")
    hit_ids = {(hit.rule_id, hit.line_id) for hit in result.hits}

    assert ("PAY.LIMIT.UNIT_PRICE_MAX.001", claim.lines[0].line_id) in hit_ids
    assert ("PAY.LIMIT.AMOUNT_MAX.001", claim.lines[0].line_id) not in hit_ids
    assert ("PAY.LIMIT.COVERAGE_PERCENT.001", claim.lines[1].line_id) in hit_ids


def test_default_payment_rules_config_should_trigger_quantity_max_group_match() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[1].item_code = "TH.QTY.001"
    claim.lines[1].item_name = "Thuoc quantity"
    claim.lines[1].quantity = Decimal("5")
    claim.lines[1].unit_price = Decimal("10000")
    claim.lines[1].amount = Decimal("50000")
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry, payment_rules_file=PAYMENT_RULES_FILE)

    result = engine.evaluate(claim, "2026-03-30")

    assert any(
        hit.rule_id == "PAY.LIMIT.QUANTITY_MAX.001" and hit.line_id == claim.lines[1].line_id
        for hit in result.hits
    )


def test_default_payment_rules_config_should_trigger_amount_max_match() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].item_code = "DV.AMOUNTMAX.001"
    claim.lines[0].item_name = "DV amount max"
    claim.lines[0].quantity = Decimal("1")
    claim.lines[0].unit_price = Decimal("220000")
    claim.lines[0].amount = Decimal("220000")
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry, payment_rules_file=PAYMENT_RULES_FILE)

    result = engine.evaluate(claim, "2026-03-30")

    assert any(
        hit.rule_id == "PAY.LIMIT.AMOUNT_MAX.001"
        and hit.line_id == claim.lines[0].line_id
        and hit.estimated_amount_impact == Decimal("70000")
        for hit in result.hits
    )


def test_engine_should_return_warning_hits_when_practitioner_missing_from_master_data() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)
    master_snapshot = MasterDataSnapshot(
        dataset_version="test",
        effective_date="2026-03-30",
        staff_members=[
            StaffMember(
                practitioner_id="KNOWN001",
                practitioner_name="Known User",
            )
        ],
        service_items=[
            ServiceItem(service_code="DV001", approved_name="Khám bệnh"),
        ],
        all_service_items=[
            ServiceItem(service_code="DV001", approved_name="Khám bệnh"),
        ],
    )

    result = engine.evaluate(claim, "2026-03-30", master_snapshot=master_snapshot)

    assert len(result.hits) == 2
    assert {hit.rule_id for hit in result.hits} == {"MASTER.PRACTITIONER_EXISTS.001"}
    assert {hit.line_id for hit in result.hits} == {"L001", "L002"}


def test_engine_should_return_warning_hit_when_practitioner_department_mismatch() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].practitioner_id = "3820222623"
    claim.lines[0].department_code = "K01"
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)
    master_snapshot = MasterDataSnapshot(
        dataset_version="test",
        effective_date="2026-03-30",
        staff_members=[
            StaffMember(
                practitioner_id="3820222623",
                practitioner_name="Lê Quang Đức",
                department_code="K02",
            )
        ],
    )

    result = engine.evaluate(claim, "2026-03-30", master_snapshot=master_snapshot)

    assert any(hit.rule_id == "MASTER.PRACTITIONER_DEPARTMENT.001" for hit in result.hits)


def test_engine_should_return_warning_hit_when_service_outside_practitioner_scope() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].practitioner_id = "3823062968"
    claim.lines[0].item_code = "99.9999"
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)
    master_snapshot = MasterDataSnapshot(
        dataset_version="test",
        effective_date="2026-03-30",
        staff_members=[
            StaffMember(
                practitioner_id="3823062968",
                practitioner_name="Lê Văn Tuấn Anh",
                extra_service_codes=["02.0045"],
                practice_scope="",
            )
        ],
        service_items=[
            ServiceItem(
                service_code="99.9999",
                approved_name="DV test",
            )
        ],
    )

    result = engine.evaluate(claim, "2026-03-30", master_snapshot=master_snapshot)

    assert any(hit.rule_id == "MASTER.PRACTITIONER_SCOPE.001" for hit in result.hits)


def test_engine_should_not_warn_when_practice_scope_exists_even_if_service_not_in_dvkt_khac() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].practitioner_id = "3823062968"
    claim.lines[0].item_code = "99.9999"
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)
    master_snapshot = MasterDataSnapshot(
        dataset_version="test",
        effective_date="2026-03-30",
        staff_members=[
            StaffMember(
                practitioner_id="3823062968",
                practitioner_name="Scoped User",
                extra_service_codes=[],
                practice_scope="129",
            )
        ],
        service_items=[
            ServiceItem(
                service_code="99.9999",
                approved_name="DV test",
            )
        ],
    )

    result = engine.evaluate(claim, "2026-03-30", master_snapshot=master_snapshot)

    assert all(hit.rule_id != "MASTER.PRACTITIONER_SCOPE.001" for hit in result.hits)


def test_engine_should_warn_when_inpatient_claim_has_no_clinical_notes() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.header.visit_type = "03"
    claim.clinical_notes.clear()
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)

    result = engine.evaluate(claim, "2026-03-30")

    assert any(hit.rule_id == "LOGIC.CLINICAL_CONTEXT.001" for hit in result.hits)
    assert any("XML5" in hit.required_evidence for hit in result.hits)


def test_engine_should_warn_when_clinical_result_has_no_matching_billed_service() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.clinical_results = [
        ClinicalResult(
            result_id="XML4-1",
            claim_id=claim.header.claim_id,
            service_code="CLS.4040",
            indicator_name="Xet nghiem test",
            source_xml="XML4",
            source_node_path="DSACH_CHI_TIET_CLS/CHI_TIET_CLS",
        )
    ]
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)

    result = engine.evaluate(claim, "2026-03-30")

    assert any(hit.rule_id == "LOGIC.CLINICAL_CONTEXT.001" for hit in result.hits)
    assert any(hit.required_evidence == ["XML3", "XML4"] for hit in result.hits)


def test_engine_should_warn_when_drug_has_no_recent_clinical_note() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].line_type = "drug"
    claim.lines[0].execution_time = "2026-03-30T08:00:00"
    claim.clinical_notes = [
        ClinicalNote(
            note_id="XML5-1",
            claim_id=claim.header.claim_id,
            note_text="Chẩn đoán: A09. Theo dõi ổn định.",
            note_time="2026-03-28T08:00:00",
            source_xml="XML5",
            source_node_path="XML5/NOTE",
        )
    ]
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)

    result = engine.evaluate(claim, "2026-03-30")

    assert any(
        hit.rule_id == "LOGIC.CLINICAL_CONTEXT.001" and hit.line_id == claim.lines[0].line_id
        for hit in result.hits
    )


def test_engine_should_accept_inpatient_note_on_same_day_after_execution_time() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.header.visit_type = "03"
    claim.lines[0].line_type = "service"
    claim.lines[0].execution_time = "2026-03-28T06:00:00"
    claim.header.primary_diagnosis_code = "C16"
    claim.clinical_notes = [
        ClinicalNote(
            note_id="XML5-1",
            claim_id=claim.header.claim_id,
            note_text="K da day, an kem, tiep tuc dieu tri hoa chat.",
            note_time="2026-03-28T08:30:00",
            source_xml="XML5",
            source_node_path="XML5/NOTE",
        )
    ]
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)

    result = engine.evaluate(claim, "2026-03-30")

    assert all(
        not (
            hit.rule_id == "LOGIC.CLINICAL_CONTEXT.001"
            and hit.line_id == claim.lines[0].line_id
            and hit.required_evidence == ["XML2/XML3", "XML5"]
        )
        for hit in result.hits
    )


def test_engine_should_accept_inpatient_note_within_36_hours() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.header.visit_type = "03"
    claim.lines[0].line_type = "service"
    claim.lines[0].execution_time = "2026-03-29T18:00:00"
    claim.header.primary_diagnosis_code = "C34"
    claim.clinical_notes = [
        ClinicalNote(
            note_id="XML5-1",
            claim_id=claim.header.claim_id,
            note_text="Ung thu phoi, ho, dau nguc, tiep tuc theo doi.",
            note_time="2026-03-28T08:30:00",
            source_xml="XML5",
            source_node_path="XML5/NOTE",
        )
    ]
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)

    result = engine.evaluate(claim, "2026-03-30")

    assert all(
        not (
            hit.rule_id == "LOGIC.CLINICAL_CONTEXT.001"
            and hit.line_id == claim.lines[0].line_id
            and hit.required_evidence == ["XML2/XML3", "XML5"]
        )
        for hit in result.hits
    )


def test_engine_should_warn_when_recent_clinical_note_has_no_diagnosis_context() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].line_type = "drug"
    claim.lines[0].execution_time = "2026-03-28T09:00:00"
    claim.header.primary_diagnosis_code = "A09"
    claim.clinical_notes = [
        ClinicalNote(
            note_id="XML5-1",
            claim_id=claim.header.claim_id,
            note_text="Theo dõi mạch, nhiệt độ, ăn uống được.",
            note_time="2026-03-28T08:30:00",
            source_xml="XML5",
            source_node_path="XML5/NOTE",
        )
    ]
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)

    result = engine.evaluate(claim, "2026-03-30")

    assert any(
        hit.rule_id == "LOGIC.CLINICAL_CONTEXT.001" and hit.line_id == claim.lines[0].line_id
        for hit in result.hits
    )


def test_engine_should_warn_when_drug_group_context_keywords_missing() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].line_type = "drug"
    claim.lines[0].item_name = "Fisulty 2 g"
    claim.lines[0].execution_time = "2026-03-28T09:00:00"
    claim.header.primary_diagnosis_code = "A09"
    claim.clinical_notes = [
        ClinicalNote(
            note_id="XML5-1",
            claim_id=claim.header.claim_id,
            note_text="Chẩn đoán: A09. Theo dõi bụng mềm, ăn uống kém.",
            note_time="2026-03-28T08:30:00",
            source_xml="XML5",
            source_node_path="XML5/NOTE",
        )
    ]
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)

    result = engine.evaluate(claim, "2026-03-30")

    assert any(
        hit.rule_id == "LOGIC.CLINICAL_CONTEXT.001"
        and hit.line_id == claim.lines[0].line_id
        and hit.required_evidence == ["XML2", "XML5"]
        for hit in result.hits
    )


def test_engine_should_warn_when_service_group_context_keywords_missing() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].line_type = "service"
    claim.lines[0].item_name = "Điện tim thường"
    claim.lines[0].execution_time = "2026-03-28T09:00:00"
    claim.header.primary_diagnosis_code = "A09"
    claim.clinical_notes = [
        ClinicalNote(
            note_id="XML5-1",
            claim_id=claim.header.claim_id,
            note_text="Chẩn đoán: A09. Theo dõi bụng mềm, ăn uống kém.",
            note_time="2026-03-28T08:30:00",
            source_xml="XML5",
            source_node_path="XML5/NOTE",
        )
    ]
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)

    result = engine.evaluate(claim, "2026-03-30")

    assert any(
        hit.rule_id == "LOGIC.CLINICAL_CONTEXT.001"
        and hit.line_id == claim.lines[0].line_id
        and hit.required_evidence == ["XML3", "XML5"]
        for hit in result.hits
    )


def test_engine_should_warn_when_cls_context_keywords_missing() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.clinical_results = [
        ClinicalResult(
            result_id="XML4-1",
            claim_id=claim.header.claim_id,
            service_code="22.0120.1370",
            indicator_name="Số lượng bạch cầu",
            result_time="2026-03-28T09:00:00",
            source_xml="XML4",
            source_node_path="DSACH_CHI_TIET_CLS/CHI_TIET_CLS",
        )
    ]
    claim.clinical_notes = [
        ClinicalNote(
            note_id="XML5-1",
            claim_id=claim.header.claim_id,
            note_text="Chẩn đoán: A09. Theo dõi bụng mềm, ăn uống được.",
            note_time="2026-03-28T08:30:00",
            source_xml="XML5",
            source_node_path="XML5/NOTE",
        )
    ]
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)

    result = engine.evaluate(claim, "2026-03-30")

    assert any(
        hit.rule_id == "LOGIC.CLINICAL_CONTEXT.001"
        and hit.required_evidence == ["XML4", "XML5"]
        for hit in result.hits
    )


def test_engine_should_warn_when_department_context_keywords_missing() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].line_type = "service"
    claim.lines[0].department_code = "K01"
    claim.lines[0].item_name = "Khám Ung bướu"
    claim.lines[0].execution_time = "2026-03-28T09:00:00"
    claim.header.primary_diagnosis_code = "A09"
    claim.clinical_notes = [
        ClinicalNote(
            note_id="XML5-1",
            claim_id=claim.header.claim_id,
            note_text="Chẩn đoán: A09. Theo dõi bụng mềm, ăn uống kém.",
            note_time="2026-03-28T08:30:00",
            source_xml="XML5",
            source_node_path="XML5/NOTE",
        )
    ]
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)

    result = engine.evaluate(claim, "2026-03-30")

    assert any(
        hit.rule_id == "LOGIC.CLINICAL_CONTEXT.001"
        and hit.line_id == claim.lines[0].line_id
        and hit.required_evidence == ["XML3", "XML5"]
        for hit in result.hits
    )


def test_engine_should_accept_oncology_note_alias_for_department_context() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].line_type = "service"
    claim.lines[0].department_code = "K33"
    claim.lines[0].item_name = "Giuong Noi khoa loai 1 - Khoa Ung buou"
    claim.lines[0].execution_time = "2026-03-28T09:00:00"
    claim.header.primary_diagnosis_code = "C34"
    claim.clinical_notes = [
        ClinicalNote(
            note_id="XML5-1",
            claim_id=claim.header.claim_id,
            note_text="Ung thu phoi dang dieu tri TKI, theo doi ho khan va dau nguc.",
            note_time="2026-03-28T08:30:00",
            source_xml="XML5",
            source_node_path="XML5/NOTE",
        )
    ]
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)

    result = engine.evaluate(claim, "2026-03-30")

    assert all(
        not (
            hit.rule_id == "LOGIC.CLINICAL_CONTEXT.001"
            and hit.line_id == claim.lines[0].line_id
        )
        for hit in result.hits
    )


def test_engine_should_accept_xml5_alias_for_supportive_drug_in_gastric_cancer() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].line_type = "drug"
    claim.lines[0].item_name = "Natri clorid 0,9%"
    claim.lines[0].execution_time = "2026-03-28T09:00:00"
    claim.header.primary_diagnosis_code = "C16"
    claim.clinical_notes = [
        ClinicalNote(
            note_id="XML5-1",
            claim_id=claim.header.claim_id,
            note_text="K da day dang truyen hoa chat phac do Oxaliplatin 5FU, benh nhan an kem va buon non.",
            note_time="2026-03-28T08:30:00",
            source_xml="XML5",
            source_node_path="XML5/NOTE",
        )
    ]
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)

    result = engine.evaluate(claim, "2026-03-30")

    assert all(
        not (
            hit.rule_id == "LOGIC.CLINICAL_CONTEXT.001"
            and hit.line_id == claim.lines[0].line_id
        )
        for hit in result.hits
    )


def test_engine_should_accept_xml5_alias_for_oncology_ct_service() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].line_type = "service"
    claim.lines[0].item_name = "CT nguc co can quang"
    claim.lines[0].execution_time = "2026-03-28T09:00:00"
    claim.header.primary_diagnosis_code = "C34"
    claim.clinical_notes = [
        ClinicalNote(
            note_id="XML5-1",
            claim_id=claim.header.claim_id,
            note_text="Ung thu phoi nghi di can, ho nhieu, dang theo doi EGFR truoc dieu tri.",
            note_time="2026-03-28T08:30:00",
            source_xml="XML5",
            source_node_path="XML5/NOTE",
        )
    ]
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)

    result = engine.evaluate(claim, "2026-03-30")

    assert all(
        not (
            hit.rule_id == "LOGIC.CLINICAL_CONTEXT.001"
            and hit.line_id == claim.lines[0].line_id
        )
        for hit in result.hits
    )


def test_engine_should_accept_xml5_context_for_oncology_infusion_service() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].line_type = "service"
    claim.lines[0].item_name = "Truyen hoa chat tinh mach [noi tru]"
    claim.lines[0].department_code = "K33"
    claim.lines[0].execution_time = "2026-03-28T09:00:00"
    claim.header.primary_diagnosis_code = "C34"
    claim.clinical_notes = [
        ClinicalNote(
            note_id="XML5-1",
            claim_id=claim.header.claim_id,
            note_text="Ung thu phoi, ho thung thang, dau tuc nguc, tiep tuc theo doi dieu tri.",
            note_time="2026-03-28T08:30:00",
            source_xml="XML5",
            source_node_path="XML5/NOTE",
        )
    ]
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)

    result = engine.evaluate(claim, "2026-03-30")

    assert all(
        not (
            hit.rule_id == "LOGIC.CLINICAL_CONTEXT.001"
            and hit.line_id == claim.lines[0].line_id
        )
        for hit in result.hits
    )


def test_engine_should_accept_xml5_context_for_oncology_contrast_drug() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].line_type = "drug"
    claim.lines[0].item_name = "Omnipaque"
    claim.lines[0].execution_time = "2026-03-28T09:00:00"
    claim.header.primary_diagnosis_code = "C34"
    claim.clinical_notes = [
        ClinicalNote(
            note_id="XML5-1",
            claim_id=claim.header.claim_id,
            note_text="Ung thu phoi nghi di can, chi dinh CT nguc co can quang de danh gia ton thuong.",
            note_time="2026-03-28T08:30:00",
            source_xml="XML5",
            source_node_path="XML5/NOTE",
        )
    ]
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)

    result = engine.evaluate(claim, "2026-03-30")

    assert all(
        not (
            hit.rule_id == "LOGIC.CLINICAL_CONTEXT.001"
            and hit.line_id == claim.lines[0].line_id
        )
        for hit in result.hits
    )


def test_engine_should_warn_when_service_requires_equipment_but_equipment_missing() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].line_type = "service"
    claim.lines[0].item_name = "Điện tim thường"
    claim.lines[0].equipment_ref = ""
    claim.lines[0].execution_time = "2026-03-28T09:00:00"
    claim.header.primary_diagnosis_code = "A09"
    claim.clinical_notes = [
        ClinicalNote(
            note_id="XML5-1",
            claim_id=claim.header.claim_id,
            note_text="Chẩn đoán: A09. Tim đều rõ, mạch 80 lần/phút.",
            note_time="2026-03-28T08:30:00",
            source_xml="XML5",
            source_node_path="XML5/NOTE",
        )
    ]
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)
    master_snapshot = MasterDataSnapshot(
        dataset_version="test",
        effective_date="2026-03-30",
        equipment_items=[EquipmentItem(equipment_id="MAY001", equipment_name="ECG 1")],
    )

    result = engine.evaluate(claim, "2026-03-30", master_snapshot=master_snapshot)

    assert any(
        hit.rule_id == "MASTER.EQUIPMENT_REFERENCE.001"
        and hit.line_id == claim.lines[0].line_id
        and hit.required_evidence == ["XML3", "FileTrangThietBi.xlsx"]
        for hit in result.hits
    )


def test_engine_should_warn_when_service_equipment_group_is_mismatched() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].line_type = "service"
    claim.lines[0].item_name = "Điện tim thường"
    claim.lines[0].equipment_ref = "XQ.1.001"
    claim.lines[0].execution_time = "2026-03-28T09:00:00"
    claim.header.primary_diagnosis_code = "A09"
    claim.clinical_notes = [
        ClinicalNote(
            note_id="XML5-1",
            claim_id=claim.header.claim_id,
            note_text="Chẩn đoán: A09. Tim đều rõ, mạch 80 lần/phút.",
            note_time="2026-03-28T08:30:00",
            source_xml="XML5",
            source_node_path="XML5/NOTE",
        )
    ]
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)
    master_snapshot = MasterDataSnapshot(
        dataset_version="test",
        effective_date="2026-03-30",
        equipment_items=[EquipmentItem(equipment_id="XQ.1.001", equipment_name="XQ")],
    )

    result = engine.evaluate(claim, "2026-03-30", master_snapshot=master_snapshot)

    assert any(
        hit.rule_id == "MASTER.EQUIPMENT_REFERENCE.001"
        and hit.line_id == claim.lines[0].line_id
        and hit.required_evidence == ["XML3", "FileTrangThietBi.xlsx"]
        for hit in result.hits
    )


def test_engine_should_warn_when_service_line_is_duplicated_in_same_day() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].line_type = "service"
    claim.lines[1].line_type = "service"
    claim.lines[1].item_code = claim.lines[0].item_code
    claim.lines[1].execution_time = claim.lines[0].execution_time = "2026-03-28T09:00:00"
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)

    result = engine.evaluate(claim, "2026-03-30")

    assert any(hit.rule_id == "LOGIC.DUPLICATE_LINE.001" for hit in result.hits)


def test_engine_should_warn_when_cls_indicator_is_duplicated_in_same_day() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.clinical_results = [
        ClinicalResult(
            result_id="XML4-1",
            claim_id=claim.header.claim_id,
            service_code="22.0120.1370",
            indicator_code="WBC",
            indicator_name="Số lượng bạch cầu",
            result_time="2026-03-28T09:00:00",
            source_xml="XML4",
            source_node_path="DSACH_CHI_TIET_CLS/CHI_TIET_CLS",
        ),
        ClinicalResult(
            result_id="XML4-2",
            claim_id=claim.header.claim_id,
            service_code="22.0120.1370",
            indicator_code="WBC",
            indicator_name="Số lượng bạch cầu",
            result_time="2026-03-28T10:00:00",
            source_xml="XML4",
            source_node_path="DSACH_CHI_TIET_CLS/CHI_TIET_CLS",
        ),
        ClinicalResult(
            result_id="XML4-3",
            claim_id=claim.header.claim_id,
            service_code="22.0120.1370",
            indicator_code="WBC",
            indicator_name="Số lượng bạch cầu",
            result_time="2026-03-28T11:00:00",
            source_xml="XML4",
            source_node_path="DSACH_CHI_TIET_CLS/CHI_TIET_CLS",
        ),
    ]
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)

    result = engine.evaluate(claim, "2026-03-30")

    assert any(hit.rule_id == "LOGIC.DUPLICATE_LINE.001" for hit in result.hits)


def test_engine_should_not_warn_when_cls_indicator_with_threshold_two_appears_twice() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.clinical_results = [
        ClinicalResult(
            result_id="XML4-1",
            claim_id=claim.header.claim_id,
            service_code="22.0120.1370",
            indicator_code="WBC",
            indicator_name="Số lượng bạch cầu",
            result_time="2026-03-28T09:00:00",
            source_xml="XML4",
            source_node_path="DSACH_CHI_TIET_CLS/CHI_TIET_CLS",
        ),
        ClinicalResult(
            result_id="XML4-2",
            claim_id=claim.header.claim_id,
            service_code="22.0120.1370",
            indicator_code="WBC",
            indicator_name="Số lượng bạch cầu",
            result_time="2026-03-28T10:00:00",
            source_xml="XML4",
            source_node_path="DSACH_CHI_TIET_CLS/CHI_TIET_CLS",
        ),
    ]
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)

    result = engine.evaluate(claim, "2026-03-30")

    assert all(hit.rule_id != "LOGIC.DUPLICATE_LINE.001" for hit in result.hits)


def test_engine_should_warn_when_service_code_missing_from_catalog() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].line_type = "service"
    claim.lines[0].item_code = "99.0000"
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)
    master_snapshot = MasterDataSnapshot(
        dataset_version="test",
        effective_date="2026-03-30",
        service_items=[
            ServiceItem(service_code="02.1900", approved_name="DV test"),
        ],
        all_service_items=[
            ServiceItem(service_code="02.1900", approved_name="DV test"),
        ],
    )

    result = engine.evaluate(claim, "2026-03-30", master_snapshot=master_snapshot)

    assert any(hit.rule_id == "MASTER.ITEM_CODE.001" for hit in result.hits)
    assert all(hit.rule_id != "MASTER.ITEM_EFFECTIVE.001" for hit in result.hits)


def test_engine_should_warn_when_service_code_exists_but_not_effective() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].line_type = "service"
    claim.lines[0].item_code = "02.1900"
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)
    master_snapshot = MasterDataSnapshot(
        dataset_version="test",
        effective_date="2026-03-30",
        service_items=[],
        all_service_items=[
            ServiceItem(service_code="02.1900", approved_name="DV test"),
        ],
    )

    result = engine.evaluate(claim, "2026-03-30", master_snapshot=master_snapshot)

    assert any(hit.rule_id == "MASTER.ITEM_EFFECTIVE.001" for hit in result.hits)
    assert all(hit.rule_id != "MASTER.ITEM_CODE.001" for hit in result.hits)


def test_engine_should_warn_when_drug_code_missing_from_catalog() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].line_type = "drug"
    claim.lines[0].item_code = "TH999"
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)
    master_snapshot = MasterDataSnapshot(
        dataset_version="test",
        effective_date="2026-03-30",
        drug_items=[DrugItem(drug_code="TH001", drug_name="Paracetamol")],
        all_drug_items=[DrugItem(drug_code="TH001", drug_name="Paracetamol")],
    )

    result = engine.evaluate(claim, "2026-03-30", master_snapshot=master_snapshot)

    assert any(hit.rule_id == "MASTER.ITEM_CODE.001" for hit in result.hits)
    assert any(hit.required_evidence == ["XML2", "FileThuoc.xlsx"] for hit in result.hits)


def test_engine_should_warn_when_supply_code_exists_but_not_effective() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].line_type = "supply"
    claim.lines[0].item_code = "VT001"
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)
    master_snapshot = MasterDataSnapshot(
        dataset_version="test",
        effective_date="2026-03-30",
        supply_items=[],
        all_supply_items=[SupplyItem(supply_code="VT001", supply_name="Kim tiem")],
    )

    result = engine.evaluate(claim, "2026-03-30", master_snapshot=master_snapshot)

    assert any(hit.rule_id == "MASTER.ITEM_EFFECTIVE.001" for hit in result.hits)
    assert any(hit.required_evidence == ["XML3", "FileVatTuYTe.xlsx"] for hit in result.hits)


def test_engine_should_reduce_when_item_is_configured_as_included_in_price(
    tmp_path: Path,
) -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].line_type = "supply"
    claim.lines[0].item_code = "VT001"
    claim.lines[0].item_name = "Kim tiem 5ml"
    policy_file = tmp_path / "payment_policy.mwp.json"
    policy_file.write_text(
        json.dumps(
            {
                "included_in_price_codes": {
                    "service": [],
                    "drug": [],
                    "supply": ["VT001"],
                },
                "included_in_price_keywords": {
                    "service": [],
                    "drug": [],
                    "supply": [],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry, payment_policy_file=policy_file)

    result = engine.evaluate(claim, "2026-03-30")

    assert any(hit.rule_id == "PAY.INCLUDED_IN_PRICE.001" for hit in result.hits)
    assert any(hit.suggested_action == "reduce" for hit in result.hits)


def test_engine_should_reject_when_item_matches_pay_out_of_scope_by_code(tmp_path: Path) -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].line_type = "service"
    claim.lines[0].item_code = "DV001"
    payment_rules_file = tmp_path / "payment_rules.mwp.json"
    payment_rules_file.write_text(
        json.dumps(
            {
                "source_ref": "payment-rules@test",
                "schema_version": "1.0",
                "default_currency": "VND",
                "match_priority": ["code", "group", "keyword"],
                "rules": [
                    {
                        "rule_id": "PAY.OUT_OF_SCOPE.001",
                        "enabled": True,
                        "description_vi": "Out of scope",
                        "rule_kind": "out_of_scope",
                        "item_types": ["service"],
                        "suggested_action": "reject",
                        "severity": "reject",
                        "impact_formula": "full_line_amount",
                        "effective_from": "2025-01-01",
                        "effective_to": None,
                        "legal_basis": ["TT test"],
                        "matchers": [
                            {"match_type": "code", "item_type": "service", "values": ["DV001"]}
                        ],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry, payment_rules_file=payment_rules_file)

    result = engine.evaluate(claim, "2026-03-30")

    assert any(
        hit.rule_id == "PAY.OUT_OF_SCOPE.001"
        and hit.line_id == claim.lines[0].line_id
        and hit.estimated_amount_impact == Decimal("100000")
        for hit in result.hits
    )


def test_engine_should_reject_when_item_matches_pay_out_of_scope_by_keyword(tmp_path: Path) -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[0].line_type = "drug"
    claim.lines[0].item_name = "Thuoc nam trong danh sach cam"
    payment_rules_file = tmp_path / "payment_rules.mwp.json"
    payment_rules_file.write_text(
        json.dumps(
            {
                "source_ref": "payment-rules@test",
                "schema_version": "1.0",
                "default_currency": "VND",
                "match_priority": ["keyword", "code", "group"],
                "rules": [
                    {
                        "rule_id": "PAY.OUT_OF_SCOPE.001",
                        "enabled": True,
                        "description_vi": "Out of scope",
                        "rule_kind": "out_of_scope",
                        "item_types": ["drug"],
                        "suggested_action": "reject",
                        "severity": "reject",
                        "impact_formula": "full_line_amount",
                        "effective_from": "2025-01-01",
                        "effective_to": None,
                        "legal_basis": ["TT test"],
                        "matchers": [
                            {"match_type": "keyword", "item_type": "drug", "values": ["danh sach cam"]}
                        ],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry, payment_rules_file=payment_rules_file)

    result = engine.evaluate(claim, "2026-03-30")

    assert any(
        hit.rule_id == "PAY.OUT_OF_SCOPE.001"
        and hit.line_id == claim.lines[0].line_id
        for hit in result.hits
    )


def test_engine_should_skip_pay_out_of_scope_when_entry_is_not_effective(tmp_path: Path) -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    payment_rules_file = tmp_path / "payment_rules.mwp.json"
    payment_rules_file.write_text(
        json.dumps(
            {
                "source_ref": "payment-rules@test",
                "schema_version": "1.0",
                "default_currency": "VND",
                "match_priority": ["code", "group", "keyword"],
                "rules": [
                    {
                        "rule_id": "PAY.OUT_OF_SCOPE.001",
                        "enabled": True,
                        "description_vi": "Out of scope",
                        "rule_kind": "out_of_scope",
                        "item_types": ["service"],
                        "suggested_action": "reject",
                        "severity": "reject",
                        "impact_formula": "full_line_amount",
                        "effective_from": "2025-01-01",
                        "effective_to": None,
                        "legal_basis": ["TT test"],
                        "matchers": [
                            {
                                "match_type": "code",
                                "item_type": "service",
                                "entries": [
                                    {
                                        "match_value": "DV001",
                                        "effective_from": "2027-01-01",
                                        "effective_to": None,
                                        "legal_basis": ["TT future"],
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry, payment_rules_file=payment_rules_file)

    result = engine.evaluate(claim, "2026-03-30")

    assert all(hit.rule_id != "PAY.OUT_OF_SCOPE.001" for hit in result.hits)


def test_engine_should_reduce_when_pay_limit_coverage_percent_matches(tmp_path: Path) -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    payment_rules_file = tmp_path / "payment_rules.mwp.json"
    payment_rules_file.write_text(
        json.dumps(
            {
                "source_ref": "payment-rules@test",
                "schema_version": "1.0",
                "default_currency": "VND",
                "match_priority": ["code", "group", "keyword"],
                "rules": [
                    {
                        "rule_id": "PAY.LIMIT.COVERAGE_PERCENT.001",
                        "enabled": True,
                        "description_vi": "Coverage limit",
                        "rule_kind": "coverage_percent",
                        "item_types": ["service"],
                        "suggested_action": "reduce",
                        "severity": "warning",
                        "impact_formula": "",
                        "effective_from": "2025-01-01",
                        "effective_to": None,
                        "legal_basis": ["TT test"],
                        "matchers": [
                            {
                                "match_type": "code",
                                "item_type": "service",
                                "entries": [{"match_value": "DV001", "coverage_percent": 0.8}],
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry, payment_rules_file=payment_rules_file)

    result = engine.evaluate(claim, "2026-03-30")

    assert any(
        hit.rule_id == "PAY.LIMIT.COVERAGE_PERCENT.001"
        and hit.estimated_amount_impact == Decimal("20000")
        for hit in result.hits
    )


def test_engine_should_reduce_when_pay_limit_unit_price_max_matches(tmp_path: Path) -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    payment_rules_file = tmp_path / "payment_rules.mwp.json"
    payment_rules_file.write_text(
        json.dumps(
            {
                "source_ref": "payment-rules@test",
                "schema_version": "1.0",
                "default_currency": "VND",
                "match_priority": ["code", "group", "keyword"],
                "rules": [
                    {
                        "rule_id": "PAY.LIMIT.UNIT_PRICE_MAX.001",
                        "enabled": True,
                        "description_vi": "Unit price limit",
                        "rule_kind": "unit_price_max",
                        "item_types": ["service"],
                        "suggested_action": "reduce",
                        "severity": "warning",
                        "impact_formula": "",
                        "effective_from": "2025-01-01",
                        "effective_to": None,
                        "legal_basis": ["TT test"],
                        "matchers": [
                            {
                                "match_type": "code",
                                "item_type": "service",
                                "entries": [{"match_value": "DV001", "unit_price_max": 70000}],
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry, payment_rules_file=payment_rules_file)

    result = engine.evaluate(claim, "2026-03-30")

    assert any(
        hit.rule_id == "PAY.LIMIT.UNIT_PRICE_MAX.001"
        and hit.estimated_amount_impact == Decimal("30000")
        for hit in result.hits
    )


def test_engine_should_reduce_when_pay_limit_quantity_max_matches_group(tmp_path: Path) -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.lines[1].line_type = "drug"
    payment_rules_file = tmp_path / "payment_rules.mwp.json"
    payment_rules_file.write_text(
        json.dumps(
            {
                "source_ref": "payment-rules@test",
                "schema_version": "1.0",
                "default_currency": "VND",
                "match_priority": ["group", "code", "keyword"],
                "rules": [
                    {
                        "rule_id": "PAY.LIMIT.QUANTITY_MAX.001",
                        "enabled": True,
                        "description_vi": "Quantity limit",
                        "rule_kind": "quantity_max",
                        "item_types": ["drug"],
                        "suggested_action": "reduce",
                        "severity": "warning",
                        "impact_formula": "",
                        "effective_from": "2025-01-01",
                        "effective_to": None,
                        "legal_basis": ["TT test"],
                        "matchers": [
                            {
                                "match_type": "group",
                                "item_type": "drug",
                                "entries": [{"group_code": "TH", "quantity_max": 1}],
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry, payment_rules_file=payment_rules_file)

    result = engine.evaluate(claim, "2026-03-30")

    assert any(
        hit.rule_id == "PAY.LIMIT.QUANTITY_MAX.001"
        and hit.line_id == "L002"
        and hit.estimated_amount_impact == Decimal("100000")
        for hit in result.hits
    )


def test_engine_should_reduce_when_pay_limit_amount_max_matches(tmp_path: Path) -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    payment_rules_file = tmp_path / "payment_rules.mwp.json"
    payment_rules_file.write_text(
        json.dumps(
            {
                "source_ref": "payment-rules@test",
                "schema_version": "1.0",
                "default_currency": "VND",
                "match_priority": ["code", "group", "keyword"],
                "rules": [
                    {
                        "rule_id": "PAY.LIMIT.AMOUNT_MAX.001",
                        "enabled": True,
                        "description_vi": "Amount limit",
                        "rule_kind": "amount_max",
                        "item_types": ["drug"],
                        "suggested_action": "reduce",
                        "severity": "warning",
                        "impact_formula": "",
                        "effective_from": "2025-01-01",
                        "effective_to": None,
                        "legal_basis": ["TT test"],
                        "matchers": [
                            {
                                "match_type": "code",
                                "item_type": "drug",
                                "entries": [{"match_value": "TH001", "amount_max": 150000}],
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry, payment_rules_file=payment_rules_file)

    result = engine.evaluate(claim, "2026-03-30")

    assert any(
        hit.rule_id == "PAY.LIMIT.AMOUNT_MAX.001"
        and hit.line_id == "L002"
        and hit.estimated_amount_impact == Decimal("50000")
        for hit in result.hits
    )


def test_engine_should_request_more_when_guideline_internal_code_matches_but_evidence_missing(
    tmp_path: Path,
) -> None:
    claim = ParsedClaim(
        header=ClaimHeader(
            claim_id="HS-GL-001",
            facility_id="79001",
            patient_id="BN001",
            insurance_card_no="TE123",
            visit_type="03",
            admission_time="2026-03-30T08:00:00",
            discharge_time="2026-03-30T12:00:00",
            primary_diagnosis_code="C50",
            route_code="1",
            total_amount=Decimal("500000"),
            insurance_amount=Decimal("400000"),
            patient_pay_amount=Decimal("100000"),
            claim_effective_date="2026-03-30",
        ),
        lines=[
            ClaimLine(
                line_id="L001",
                claim_id="HS-GL-001",
                line_type="service",
                item_code="DV-CHEMO-01",
                item_name="Truyen hoa chat Paclitaxel",
                quantity=Decimal("1"),
                unit_price=Decimal("500000"),
                amount=Decimal("500000"),
                execution_time="2026-03-30T09:00:00",
                source_xml="XML3",
            )
        ],
        clinical_notes=[
            ClinicalNote(
                note_id="XML5-1",
                claim_id="HS-GL-001",
                note_text="Theo doi sau truyen, benh nhan on dinh.",
                note_time="2026-03-30T09:30:00",
                source_xml="XML5",
                source_node_path="XML5/NOTE",
            )
        ],
    )
    drafts_file = tmp_path / "guideline_rule_drafts.jsonl"
    drafts_file.write_text(
        json.dumps(
            {
                "draft_rule_id": "GL.DRAFT.TEST.001",
                "statement_id": "GS.TEST.001",
                "rule_family": "GUIDELINE",
                "severity": "pending",
                "suggested_action": "request_more",
                "trigger": {
                    "statement_type": "requirement",
                    "condition": {},
                    "contraindication": {},
                    "applies_to_codes": ["INT.SVC.CHEMO_INFUSION"],
                },
                "required_evidence": [
                    {
                        "evidence_type": "xml5_note",
                        "codes": [],
                        "keywords": ["phan ve"],
                        "min_count": 1,
                        "time_window": "same_episode",
                    }
                ],
                "decision_logic_text": "Test guideline draft",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    internal_code_policy = tmp_path / "internal_code_policy.mwp.json"
    internal_code_policy.write_text(
        json.dumps(
            {
                "source_ref": "test",
                "aliases": [
                    {
                        "code": "INT.SVC.CHEMO_INFUSION",
                        "item_types": ["service"],
                        "item_codes": [],
                        "item_name_keywords": ["hoa chat"],
                        "note_keywords": ["hoa chat", "phan ve"],
                        "result_codes": [],
                        "result_keywords": [],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    engine = DeterministicRuleEngine(
        RuleRegistry([]),
        guideline_rule_drafts_file=drafts_file,
        internal_code_policy_file=internal_code_policy,
    )

    result = engine.evaluate(claim, "2026-03-30")

    assert len(result.hits) == 1
    assert result.hits[0].rule_id == "GL.DRAFT.TEST.001"
    assert result.hits[0].line_id == "L001"
    assert result.hits[0].required_evidence == ["xml5_note:phan ve"]


def test_engine_should_not_hit_when_guideline_internal_code_evidence_is_present(
    tmp_path: Path,
) -> None:
    claim = ParsedClaim(
        header=ClaimHeader(
            claim_id="HS-GL-002",
            facility_id="79001",
            patient_id="BN002",
            insurance_card_no="TE123",
            visit_type="03",
            admission_time="2026-03-30T08:00:00",
            discharge_time="2026-03-30T12:00:00",
            primary_diagnosis_code="C50",
            route_code="1",
            total_amount=Decimal("500000"),
            insurance_amount=Decimal("400000"),
            patient_pay_amount=Decimal("100000"),
            claim_effective_date="2026-03-30",
        ),
        lines=[
            ClaimLine(
                line_id="L001",
                claim_id="HS-GL-002",
                line_type="service",
                item_code="DV-CHEMO-01",
                item_name="Truyen hoa chat Paclitaxel",
                quantity=Decimal("1"),
                unit_price=Decimal("500000"),
                amount=Decimal("500000"),
                execution_time="2026-03-30T09:00:00",
                source_xml="XML3",
            )
        ],
        clinical_notes=[
            ClinicalNote(
                note_id="XML5-1",
                claim_id="HS-GL-002",
                note_text="Sau truyen hoa chat, benh nhan phan ve do Paclitaxel duoc xu tri.",
                note_time="2026-03-30T09:30:00",
                source_xml="XML5",
                source_node_path="XML5/NOTE",
            )
        ],
    )
    drafts_file = tmp_path / "guideline_rule_drafts.jsonl"
    drafts_file.write_text(
        json.dumps(
            {
                "draft_rule_id": "GL.DRAFT.TEST.001",
                "statement_id": "GS.TEST.001",
                "rule_family": "GUIDELINE",
                "severity": "pending",
                "suggested_action": "request_more",
                "trigger": {
                    "statement_type": "requirement",
                    "condition": {},
                    "contraindication": {},
                    "applies_to_codes": ["INT.SVC.CHEMO_INFUSION"],
                },
                "required_evidence": [
                    {
                        "evidence_type": "xml5_note",
                        "codes": [],
                        "keywords": ["phan ve"],
                        "min_count": 1,
                        "time_window": "same_episode",
                    }
                ],
                "decision_logic_text": "Test guideline draft",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    internal_code_policy = tmp_path / "internal_code_policy.mwp.json"
    internal_code_policy.write_text(
        json.dumps(
            {
                "source_ref": "test",
                "aliases": [
                    {
                        "code": "INT.SVC.CHEMO_INFUSION",
                        "item_types": ["service"],
                        "item_codes": [],
                        "item_name_keywords": ["hoa chat"],
                        "note_keywords": ["hoa chat", "phan ve"],
                        "result_codes": [],
                        "result_keywords": [],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    engine = DeterministicRuleEngine(
        RuleRegistry([]),
        guideline_rule_drafts_file=drafts_file,
        internal_code_policy_file=internal_code_policy,
    )

    result = engine.evaluate(claim, "2026-03-30")

    assert result.hits == []


def test_engine_should_accept_disease_profile_declared_in_policy_without_code_changes(
    tmp_path: Path,
) -> None:
    claim = ParsedClaim(
        header=ClaimHeader(
            claim_id="HS-DX-001",
            facility_id="79001",
            patient_id="BN-DX-001",
            insurance_card_no="TE123",
            visit_type="03",
            admission_time="2026-03-30T08:00:00",
            discharge_time="2026-03-30T12:00:00",
            primary_diagnosis_code="C61",
            route_code="1",
            total_amount=Decimal("500000"),
            insurance_amount=Decimal("400000"),
            patient_pay_amount=Decimal("100000"),
            claim_effective_date="2026-03-30",
        ),
        lines=[
            ClaimLine(
                line_id="L001",
                claim_id="HS-DX-001",
                line_type="service",
                item_code="02.9999.0001",
                item_name="MRI tuyen tien liet",
                quantity=Decimal("1"),
                unit_price=Decimal("500000"),
                amount=Decimal("500000"),
                execution_time="2026-03-30T09:00:00",
                department_code="K33",
                source_xml="XML3",
            )
        ],
        clinical_notes=[
            ClinicalNote(
                note_id="XML5-1",
                claim_id="HS-DX-001",
                note_text="Ung thu tuyen tien liet, tang PSA, can theo doi xam lan tai cho.",
                note_time="2026-03-30T08:30:00",
                source_xml="XML5",
                source_node_path="XML5/NOTE",
            )
        ],
    )
    clinical_policy_file = tmp_path / "clinical_policy.mwp.json"
    clinical_policy_file.write_text(
        json.dumps(
            {
                "source_ref": "test",
                "drug_context_heuristics": [],
                "service_context_heuristics": [],
                "cls_context_heuristics": [],
                "department_context_heuristics": {},
                "diagnosis_context_aliases": {},
                "disease_profiles": [
                    {
                        "profile_id": "DX.C61.001",
                        "diagnosis_code_prefixes": ["C61"],
                        "diagnosis_aliases": ["ung thu tuyen tien liet", "psa"],
                        "department_context_keywords": {
                            "K33": ["ung thu", "psa", "tuyen tien liet"]
                        },
                        "line_rules": [
                            {
                                "rule_id": "prostate_mri",
                                "line_types": ["service"],
                                "item_name_keywords": ["mri tuyen tien liet"],
                                "required_note_keywords": ["ung thu tuyen tien liet", "psa", "xam lan"],
                                "required_note_match": "any",
                                "context_label": "mri danh gia ung thu tuyen tien liet"
                            }
                        ],
                        "result_rules": []
                    }
                ],
                "equipment_required_service_heuristics": [],
                "service_duplicate_thresholds": [],
                "cls_duplicate_thresholds": []
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry, clinical_policy_file=clinical_policy_file)

    result = engine.evaluate(claim, "2026-03-30")

    assert all(hit.rule_id != "LOGIC.CLINICAL_CONTEXT.001" for hit in result.hits)


def test_engine_should_warn_when_disease_profile_context_is_missing(
    tmp_path: Path,
) -> None:
    claim = ParsedClaim(
        header=ClaimHeader(
            claim_id="HS-DX-002",
            facility_id="79001",
            patient_id="BN-DX-002",
            insurance_card_no="TE123",
            visit_type="03",
            admission_time="2026-03-30T08:00:00",
            discharge_time="2026-03-30T12:00:00",
            primary_diagnosis_code="C61",
            route_code="1",
            total_amount=Decimal("500000"),
            insurance_amount=Decimal("400000"),
            patient_pay_amount=Decimal("100000"),
            claim_effective_date="2026-03-30",
        ),
        lines=[
            ClaimLine(
                line_id="L001",
                claim_id="HS-DX-002",
                line_type="service",
                item_code="02.9999.0001",
                item_name="MRI tuyen tien liet",
                quantity=Decimal("1"),
                unit_price=Decimal("500000"),
                amount=Decimal("500000"),
                execution_time="2026-03-30T09:00:00",
                department_code="K33",
                source_xml="XML3",
            )
        ],
        clinical_notes=[
            ClinicalNote(
                note_id="XML5-1",
                claim_id="HS-DX-002",
                note_text="Ung thu tuyen tien liet, benh nhan on dinh, khong ghi ro muc dich chi dinh.",
                note_time="2026-03-30T08:30:00",
                source_xml="XML5",
                source_node_path="XML5/NOTE",
            )
        ],
    )
    clinical_policy_file = tmp_path / "clinical_policy.mwp.json"
    clinical_policy_file.write_text(
        json.dumps(
            {
                "source_ref": "test",
                "drug_context_heuristics": [],
                "service_context_heuristics": [],
                "cls_context_heuristics": [],
                "department_context_heuristics": {},
                "diagnosis_context_aliases": {},
                "disease_profiles": [
                    {
                        "profile_id": "DX.C61.001",
                        "diagnosis_code_prefixes": ["C61"],
                        "diagnosis_aliases": ["ung thu tuyen tien liet", "psa"],
                        "department_context_keywords": {
                            "K33": ["ung thu", "psa", "tuyen tien liet"]
                        },
                        "line_rules": [
                            {
                                "rule_id": "prostate_mri",
                                "line_types": ["service"],
                                "item_name_keywords": ["mri tuyen tien liet"],
                                "required_note_keywords": ["psa", "xam lan"],
                                "required_note_match": "any",
                                "context_label": "mri danh gia ung thu tuyen tien liet"
                            }
                        ],
                        "result_rules": []
                    }
                ],
                "equipment_required_service_heuristics": [],
                "service_duplicate_thresholds": [],
                "cls_duplicate_thresholds": []
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry, clinical_policy_file=clinical_policy_file)

    result = engine.evaluate(claim, "2026-03-30")

    assert any(
        hit.rule_id == "LOGIC.CLINICAL_CONTEXT.001"
        and "DX.C61.001" in hit.message
        and hit.line_id == "L001"
        for hit in result.hits
    )
