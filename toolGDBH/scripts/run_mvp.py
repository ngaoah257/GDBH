from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
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
sys.path.insert(0, str(ROOT / "modules" / "case-triage" / "src"))
sys.path.insert(0, str(ROOT / "modules" / "audit-reporting" / "src"))

from audit_reporting import AuditReportingService
from case_triage import CaseTriageService
from deterministic_rule_engine import DeterministicRuleEngine
from eligibility_service import EligibilityService
from master_data_service import MasterDataService
from parser_normalizer import ParserNormalizerService
from rule_registry import RuleRegistry


def resolve_existing_path(candidates: list[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def resolve_path_from_env(env_name: str, fallback_candidates: list[Path]) -> Path | None:
    raw_value = os.getenv(env_name, "").strip()
    if raw_value:
        return Path(raw_value)
    return resolve_existing_path(fallback_candidates)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_mvp.py <path-to-giamdinhhs.xml> [effective-date]")
        return 1

    xml_path = Path(sys.argv[1]).resolve()
    effective_date = sys.argv[2] if len(sys.argv) > 2 else "2026-03-30"
    catalog_dir = resolve_path_from_env(
        "TOOLGDBH_CATALOG_DIR",
        [ROOT / "Danhmuc", ROOT.parent / "Danhmuc"],
    )
    eligibility_policy_file = resolve_path_from_env(
        "TOOLGDBH_ELIGIBILITY_POLICY_FILE",
        [ROOT / "modules" / "eligibility-service" / "config" / "policy.mwp.json"],
    )
    rule_file = ROOT / "modules" / "rule-registry" / "config" / "rules.mwp.json"

    claim = ParserNormalizerService().parse_file(xml_path)
    registry = RuleRegistry.from_json_file(rule_file)
    engine = DeterministicRuleEngine(registry)
    master_snapshot = None
    if catalog_dir is not None and catalog_dir.exists():
        master_snapshot = MasterDataService(catalog_dir).load_snapshot(
            effective_date,
            facility_id=claim.header.facility_id,
        )

    eligibility = None
    if eligibility_policy_file is not None and eligibility_policy_file.exists():
        eligibility = EligibilityService.from_json_file(eligibility_policy_file).evaluate(claim.header)

    result = engine.evaluate(claim, effective_date, eligibility, master_snapshot)
    triage = CaseTriageService().triage(result)
    audit_service = AuditReportingService(ROOT / "runtime" / "audit")

    audit_events = [
        audit_service.log_event(
            module_name="parser-normalizer",
            entity_type="claim",
            entity_id=claim.header.claim_id,
            action="parse",
            action_result="success",
            version_ref="parser@0.1.0",
            details={"line_count": len(claim.lines)},
        ),
        audit_service.log_event(
            module_name="deterministic-rule-engine",
            entity_type="claim",
            entity_id=claim.header.claim_id,
            action="evaluate",
            action_result="success",
            version_ref="engine@0.1.0",
            details={"hit_count": len(result.hits)},
        ),
        audit_service.log_event(
            module_name="case-triage",
            entity_type="claim",
            entity_id=claim.header.claim_id,
            action="triage",
            action_result="success",
            version_ref="triage@0.1.0",
            details={"triage_level": triage.triage_level},
        ),
    ]
    if master_snapshot is not None:
        audit_events.insert(
            1,
            audit_service.log_event(
                module_name="master-data-service",
                entity_type="claim",
                entity_id=claim.header.claim_id,
                action="snapshot",
                action_result="success",
                version_ref=master_snapshot.dataset_version,
                details={
                    "staff_count": len(master_snapshot.staff_members),
                    "equipment_count": len(master_snapshot.equipment_items),
                },
            ),
        )
    if eligibility is not None:
        insert_index = 2 if master_snapshot is not None else 1
        audit_events.insert(
            insert_index,
            audit_service.log_event(
                module_name="eligibility-service",
                entity_type="claim",
                entity_id=claim.header.claim_id,
                action="evaluate",
                action_result="success",
                version_ref=eligibility.source_ref,
                details={
                    "card_valid": eligibility.card_valid,
                    "route_eligible": eligibility.route_eligible,
                    "benefit_level": str(eligibility.benefit_level),
                },
            ),
        )

    output = {
        "claim": asdict(claim),
        "master_data_snapshot": asdict(master_snapshot) if master_snapshot is not None else None,
        "eligibility_result": asdict(eligibility) if eligibility is not None else None,
        "engine_result": asdict(result),
        "triage_result": asdict(triage),
        "audit_events": [asdict(event) for event in audit_events],
        "effective_rule_count": len(registry.list_effective_rules(effective_date)),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
