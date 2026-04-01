from __future__ import annotations

import json
import os
from decimal import Decimal
from pathlib import Path

import pytest

from deterministic_rule_engine import DeterministicRuleEngine
from eligibility_service import EligibilityService
from master_data_service import MasterDataService
from parser_normalizer import ParserNormalizerService
from rule_registry import RuleRegistry


PROJECT_ROOT = Path(__file__).resolve().parents[2]
XML_DIR = Path(
    os.getenv(
        "TOOLGDBH_XML_DIR",
        PROJECT_ROOT.parent / "xulyXML" / "XML",
    )
)
CATALOG_DIR = Path(os.getenv("TOOLGDBH_CATALOG_DIR", PROJECT_ROOT.parent / "Danhmuc"))
EXPECTED_FILE = PROJECT_ROOT / "tests" / "regression" / "fixtures" / "real_claim_rule_hits.json"
RULE_FILE = PROJECT_ROOT / "modules" / "rule-registry" / "config" / "rules.mwp.json"
ELIGIBILITY_POLICY_FILE = PROJECT_ROOT / "modules" / "eligibility-service" / "config" / "policy.mwp.json"
PAYMENT_POLICY_FILE = PROJECT_ROOT / "modules" / "deterministic-rule-engine" / "config" / "payment_policy.mwp.json"
PAYMENT_RULES_FILE = PROJECT_ROOT / "modules" / "deterministic-rule-engine" / "config" / "payment_rules.mwp.json"
CLINICAL_POLICY_FILE = PROJECT_ROOT / "modules" / "deterministic-rule-engine" / "config" / "clinical_policy.mwp.json"
INTERNAL_CODE_POLICY_FILE = PROJECT_ROOT / "modules" / "deterministic-rule-engine" / "config" / "internal_code_policy.mwp.json"


def _require_real_inputs() -> None:
    if not XML_DIR.exists() or not CATALOG_DIR.exists() or not EXPECTED_FILE.exists():
        pytest.skip("Khong tim thay du lieu real XML, Danhmuc hoac snapshot regression.")


def _normalize_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def _normalize_hit(hit) -> dict[str, object]:
    return {
        "rule_id": hit.rule_id,
        "line_id": hit.line_id,
        "severity": hit.severity,
        "suggested_action": hit.suggested_action,
        "estimated_amount_impact": _normalize_decimal(hit.estimated_amount_impact),
        "required_evidence": list(hit.required_evidence),
    }


def test_real_claim_rule_hits_should_match_snapshot() -> None:
    _require_real_inputs()

    expected_rows = json.loads(EXPECTED_FILE.read_text(encoding="utf-8"))
    parser = ParserNormalizerService()
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(
        registry,
        payment_policy_file=PAYMENT_POLICY_FILE,
        payment_rules_file=PAYMENT_RULES_FILE,
        clinical_policy_file=CLINICAL_POLICY_FILE,
        internal_code_policy_file=INTERNAL_CODE_POLICY_FILE,
    )
    eligibility_service = EligibilityService.from_json_file(ELIGIBILITY_POLICY_FILE)
    master_data_service = MasterDataService(CATALOG_DIR)

    actual_rows: list[dict[str, object]] = []
    for row in expected_rows:
        xml_path = XML_DIR / row["xml_file"]
        claim = parser.parse_file(xml_path)
        effective_date = str(row["effective_date"])
        master_snapshot = master_data_service.load_snapshot(
            effective_date,
            facility_id=claim.header.facility_id,
        )
        eligibility = eligibility_service.evaluate(claim.header)
        result = engine.evaluate(claim, effective_date, eligibility, master_snapshot)
        actual_rows.append(
            {
                "xml_file": row["xml_file"],
                "claim_id": claim.header.claim_id,
                "effective_date": effective_date,
                "hit_count": len(result.hits),
                "hits": [
                    _normalize_hit(hit)
                    for hit in sorted(result.hits, key=lambda item: (item.rule_id, item.line_id or "", item.severity))
                ],
            }
        )

    assert actual_rows == expected_rows
