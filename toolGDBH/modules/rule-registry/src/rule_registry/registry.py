from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from errors import RuleRegistryError


@dataclass(slots=True)
class RuleDefinition:
    rule_id: str
    rule_name: str
    rule_group: str
    severity: str
    legal_basis: str
    effective_from: str
    effective_to: str | None
    input_scope: str
    decision_logic: str
    suggested_action: str
    owner: str
    enabled: bool = True

    def is_effective_on(self, target_date: str) -> bool:
        if target_date < self.effective_from:
            return False
        if self.effective_to and target_date > self.effective_to:
            return False
        return self.enabled


class RuleRegistry:
    def __init__(self, rules: list[RuleDefinition]):
        self._rules = rules

    @classmethod
    def from_json_file(cls, file_path: str | Path) -> "RuleRegistry":
        raw = json.loads(Path(file_path).read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise RuleRegistryError(
                "RULE_REGISTRY.INVALID_FORMAT",
                "Rule file phai la danh sach rule",
            )
        rules = [RuleDefinition(**item) for item in raw]
        return cls(rules)

    def list_effective_rules(self, target_date: str) -> list[RuleDefinition]:
        return [rule for rule in self._rules if rule.is_effective_on(target_date)]

    def get_rule(self, rule_id: str) -> RuleDefinition:
        for rule in self._rules:
            if rule.rule_id == rule_id:
                return rule
        raise RuleRegistryError("RULE_REGISTRY.NOT_FOUND", f"Khong tim thay rule {rule_id}")
