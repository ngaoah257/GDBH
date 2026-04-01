from __future__ import annotations

from decimal import Decimal

from case_triage import CaseTriageService
from claim_models import EngineResult, RuleHit


def test_triage_should_return_green_when_no_hit() -> None:
    service = CaseTriageService()
    result = service.triage(EngineResult(claim_id="HS001", hits=[]))

    assert result.triage_level == "xanh"


def test_triage_should_return_red_when_reject_exists() -> None:
    service = CaseTriageService()
    engine_result = EngineResult(
        claim_id="HS002",
        hits=[
            RuleHit(
                rule_hit_id="1",
                claim_id="HS002",
                rule_id="PAY.OUT_OF_SCOPE.001",
                severity="reject",
                legal_basis="TT",
                message="Ngoai pham vi thanh toan",
                suggested_action="reject",
                estimated_amount_impact=Decimal("100000"),
            )
        ],
    )

    result = service.triage(engine_result)

    assert result.triage_level == "do"
    assert result.reason_codes == ["PAY.OUT_OF_SCOPE.001"]
