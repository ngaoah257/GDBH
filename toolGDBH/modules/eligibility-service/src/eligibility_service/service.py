from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from claim_models import ClaimHeader, EligibilityCheck, EligibilityResult
from errors import EligibilityServiceError


@dataclass(slots=True)
class EligibilityPolicy:
    allowed_route_codes: list[str]
    invalid_card_prefixes: list[str]
    benefit_level_by_route: dict[str, Decimal]
    default_benefit_level: Decimal
    source_ref: str = "eligibility-policy@0.1.0"

    @classmethod
    def from_json_file(cls, file_path: str | Path) -> "EligibilityPolicy":
        raw = json.loads(Path(file_path).read_text(encoding="utf-8"))
        try:
            benefit_level_by_route = {
                key: Decimal(str(value))
                for key, value in raw.get("benefit_level_by_route", {}).items()
            }
            return cls(
                allowed_route_codes=list(raw["allowed_route_codes"]),
                invalid_card_prefixes=list(raw.get("invalid_card_prefixes", [])),
                benefit_level_by_route=benefit_level_by_route,
                default_benefit_level=Decimal(str(raw["default_benefit_level"])),
                source_ref=raw.get("source_ref", "eligibility-policy@0.1.0"),
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise EligibilityServiceError(
                "ELIGIBILITY.CONFIG.INVALID",
                "Policy eligibility khong hop le",
            ) from exc


class EligibilityService:
    def __init__(self, policy: EligibilityPolicy):
        self._policy = policy

    @classmethod
    def from_json_file(cls, file_path: str | Path) -> "EligibilityService":
        return cls(EligibilityPolicy.from_json_file(file_path))

    def evaluate(self, header: ClaimHeader) -> EligibilityResult:
        checks: list[EligibilityCheck] = []

        card_valid = bool(header.insurance_card_no.strip()) and not any(
            header.insurance_card_no.startswith(prefix)
            for prefix in self._policy.invalid_card_prefixes
        )
        if card_valid:
            checks.append(
                EligibilityCheck(
                    check_code="ELIG.CARD_STATUS",
                    status="pass",
                    message="The BHYT hop le theo policy MVP.",
                )
            )
        else:
            checks.append(
                EligibilityCheck(
                    check_code="ELIG.CARD_STATUS",
                    status="fail",
                    message="The BHYT khong hop le hoac nam trong danh sach chan.",
                )
            )

        route_eligible = header.route_code in self._policy.allowed_route_codes
        if route_eligible:
            checks.append(
                EligibilityCheck(
                    check_code="ELIG.ROUTE",
                    status="pass",
                    message="Ma tuyen duoc phep theo policy MVP.",
                )
            )
        else:
            checks.append(
                EligibilityCheck(
                    check_code="ELIG.ROUTE",
                    status="fail",
                    message="Ma tuyen khong nam trong policy MVP.",
                )
            )

        benefit_level = self._policy.benefit_level_by_route.get(
            header.route_code,
            self._policy.default_benefit_level,
        )
        checks.append(
            EligibilityCheck(
                check_code="ELIG.BENEFIT_LEVEL",
                status="pass" if card_valid else "review",
                message=f"Muc huong MVP ap dung: {benefit_level}.",
            )
        )

        return EligibilityResult(
            claim_id=header.claim_id,
            card_valid=card_valid,
            route_eligible=route_eligible,
            benefit_level=benefit_level if card_valid else Decimal("0"),
            checks=checks,
            source_ref=self._policy.source_ref,
        )
