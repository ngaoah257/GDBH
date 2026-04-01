from __future__ import annotations

import json
import os
import sys
from decimal import Decimal
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "shared" / "types"))
sys.path.insert(0, str(ROOT / "shared"))
sys.path.insert(0, str(ROOT / "modules" / "parser-normalizer" / "src"))
sys.path.insert(0, str(ROOT / "modules" / "eligibility-service" / "src"))
sys.path.insert(0, str(ROOT / "modules" / "master-data-service" / "src"))
sys.path.insert(0, str(ROOT / "modules" / "rule-registry" / "src"))
sys.path.insert(0, str(ROOT / "modules" / "deterministic-rule-engine" / "src"))

from deterministic_rule_engine import DeterministicRuleEngine
from eligibility_service import EligibilityService
from master_data_service import MasterDataService
from parser_normalizer import ParserNormalizerService
from rule_registry import RuleRegistry


REAL_XML_FILES = [
    "data_111096_CK2383823080273_25001726_3176.xml",
    "data_112645_HT3382796012783_25029071_3176.xml",
    "data_115373_HT3382797064202_25018502_3176.xml",
    "data_120060_GD4383822650957_26000568_3176.xml",
    "data_121472_CK2383822366571_25000934_3176.xml",
]


def resolve_path_from_env(env_name: str, fallback_candidates: list[Path]) -> Path | None:
    raw_value = os.getenv(env_name, "").strip()
    if raw_value:
        return Path(raw_value)
    for candidate in fallback_candidates:
        if candidate.exists():
            return candidate
    return None


def normalize_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def normalize_hit(hit) -> dict[str, object]:
    return {
        "rule_id": hit.rule_id,
        "line_id": hit.line_id,
        "severity": hit.severity,
        "suggested_action": hit.suggested_action,
        "estimated_amount_impact": normalize_decimal(hit.estimated_amount_impact),
        "required_evidence": list(hit.required_evidence),
    }


def main() -> int:
    xml_dir = resolve_path_from_env(
        "TOOLGDBH_XML_DIR",
        [ROOT.parent / "xulyXML" / "XML", ROOT / "xulyXML" / "XML"],
    )
    catalog_dir = resolve_path_from_env(
        "TOOLGDBH_CATALOG_DIR",
        [ROOT / "Danhmuc", ROOT.parent / "Danhmuc"],
    )
    output_file = (
        Path(sys.argv[1]).resolve()
        if len(sys.argv) > 1
        else (ROOT / "tests" / "regression" / "fixtures" / "real_claim_rule_hits.json").resolve()
    )
    if xml_dir is None or not xml_dir.exists():
        print("Input XML directory not found.")
        return 1
    if catalog_dir is None or not catalog_dir.exists():
        print("Catalog directory not found.")
        return 1

    rule_file = ROOT / "modules" / "rule-registry" / "config" / "rules.mwp.json"
    policy_file = ROOT / "modules" / "eligibility-service" / "config" / "policy.mwp.json"
    payment_policy_file = ROOT / "modules" / "deterministic-rule-engine" / "config" / "payment_policy.mwp.json"
    payment_rules_file = ROOT / "modules" / "deterministic-rule-engine" / "config" / "payment_rules.mwp.json"
    clinical_policy_file = ROOT / "modules" / "deterministic-rule-engine" / "config" / "clinical_policy.mwp.json"
    internal_code_policy_file = ROOT / "modules" / "deterministic-rule-engine" / "config" / "internal_code_policy.mwp.json"

    parser = ParserNormalizerService()
    registry = RuleRegistry.from_json_file(rule_file)
    engine = DeterministicRuleEngine(
        registry,
        payment_policy_file=payment_policy_file,
        payment_rules_file=payment_rules_file,
        clinical_policy_file=clinical_policy_file,
        internal_code_policy_file=internal_code_policy_file,
    )
    eligibility_service = EligibilityService.from_json_file(policy_file)
    master_data_service = MasterDataService(catalog_dir)

    payload: list[dict[str, object]] = []
    for file_name in REAL_XML_FILES:
        xml_path = xml_dir / file_name
        if not xml_path.exists():
            continue
        claim = parser.parse_file(xml_path)
        effective_date = claim.header.claim_effective_date or "2026-03-30"
        master_snapshot = master_data_service.load_snapshot(
            effective_date,
            facility_id=claim.header.facility_id,
        )
        eligibility = eligibility_service.evaluate(claim.header)
        result = engine.evaluate(claim, effective_date, eligibility, master_snapshot)
        payload.append(
            {
                "xml_file": file_name,
                "claim_id": claim.header.claim_id,
                "effective_date": effective_date,
                "hit_count": len(result.hits),
                "hits": [normalize_hit(hit) for hit in sorted(result.hits, key=lambda item: (item.rule_id, item.line_id or "", item.severity))],
            }
        )

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "xml_dir": str(xml_dir),
                "output_file": str(output_file),
                "claim_count": len(payload),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
