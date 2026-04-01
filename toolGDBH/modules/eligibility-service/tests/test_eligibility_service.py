from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from eligibility_service import EligibilityService
from parser_normalizer import ParserNormalizerService


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "tests" / "fixtures" / "sample_giamdinhhs.xml"
POLICY_FILE = ROOT / "modules" / "eligibility-service" / "config" / "policy.mwp.json"


def test_eligibility_service_should_return_mvp_defaults_for_valid_sample() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    service = EligibilityService.from_json_file(POLICY_FILE)

    result = service.evaluate(claim.header)

    assert result.claim_id == "HS001"
    assert result.card_valid is True
    assert result.route_eligible is True
    assert result.benefit_level == Decimal("0.80")


def test_eligibility_service_should_flag_invalid_card_prefix() -> None:
    claim = ParserNormalizerService().parse_file(FIXTURE)
    claim.header.insurance_card_no = "INVALID-001"
    service = EligibilityService.from_json_file(POLICY_FILE)

    result = service.evaluate(claim.header)

    assert result.card_valid is False
    assert result.benefit_level == Decimal("0")
    assert result.checks[0].check_code == "ELIG.CARD_STATUS"
    assert result.checks[0].status == "fail"
