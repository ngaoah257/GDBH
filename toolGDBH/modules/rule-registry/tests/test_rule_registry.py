from __future__ import annotations

from pathlib import Path

import pytest

from errors import RuleRegistryError
from rule_registry import RuleRegistry


RULE_FILE = (
    Path(__file__).resolve().parents[1] / "config" / "rules.mwp.json"
)


def test_registry_should_load_effective_rules_by_date() -> None:
    registry = RuleRegistry.from_json_file(RULE_FILE)

    rules_2024 = registry.list_effective_rules("2024-12-31")
    rules_2026 = registry.list_effective_rules("2026-03-30")

    assert len(rules_2024) == 0
    assert {rule.rule_id for rule in rules_2026} == {
        "ELIG.CARD_STATUS.001",
        "ELIG.ROUTE.001",
        "LOGIC.CLINICAL_CONTEXT.001",
        "LOGIC.DUPLICATE_LINE.001",
        "MASTER.EQUIPMENT_REFERENCE.001",
        "MASTER.ITEM_CODE.001",
        "MASTER.ITEM_EFFECTIVE.001",
        "MASTER.PRACTITIONER_DEPARTMENT.001",
        "MASTER.PRACTITIONER_EXISTS.001",
        "MASTER.PRACTITIONER_SCOPE.001",
        "PAY.OUT_OF_SCOPE.001",
        "PAY.LIMIT.COVERAGE_PERCENT.001",
        "PAY.LIMIT.UNIT_PRICE_MAX.001",
        "PAY.LIMIT.QUANTITY_MAX.001",
        "PAY.LIMIT.AMOUNT_MAX.001",
        "PAY.INCLUDED_IN_PRICE.001",
        "STRUCT.ADMISSION_DISCHARGE.001",
        "STRUCT.HEADER_SUM.001",
        "STRUCT.LINE_AMOUNT.001",
        "STRUCT.LINK_KEY.001",
        "LOGIC.TIME_WINDOW.001",
    }


def test_registry_should_raise_when_rule_missing() -> None:
    registry = RuleRegistry.from_json_file(RULE_FILE)

    with pytest.raises(RuleRegistryError) as exc:
        registry.get_rule("NOT.EXISTS")

    assert exc.value.error_code == "RULE_REGISTRY.NOT_FOUND"
