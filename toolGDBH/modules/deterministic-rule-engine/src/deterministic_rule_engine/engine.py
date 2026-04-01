from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timedelta
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from claim_models import EligibilityResult, EngineResult, MasterDataSnapshot, ParsedClaim, RuleHit
from rule_registry import RuleDefinition, RuleRegistry

DRUG_CONTEXT_HEURISTICS: tuple[dict[str, tuple[str, ...]], ...] = (
    {
        "group": "khang_sinh",
        "drug_keywords": ("fisulty", "vicimadol", "biticans", "cef", "cillin", "floxacin"),
        "context_keywords": (
            "nhiễm trùng",
            "nhiem trung",
            "viêm",
            "viem",
            "sốt",
            "sot",
            "kháng sinh",
            "khang sinh",
        ),
    },
    {
        "group": "giam_dau_khang_viem",
        "drug_keywords": ("paracetamol", "diclofenac"),
        "context_keywords": ("đau", "dau", "sốt", "sot", "viêm", "viem"),
    },
    {
        "group": "corticoid",
        "drug_keywords": ("solu-medrol", "pdsolone", "pred", "methylpred"),
        "context_keywords": ("dị ứng", "di ung", "viêm", "viem", "phù", "phu", "hen"),
    },
    {
        "group": "dinh_duong_truyen",
        "drug_keywords": ("nutriflex", "glucose", "natri clorid"),
        "context_keywords": (
            "dinh dưỡng",
            "dinh duong",
            "nuôi dưỡng",
            "nuoi duong",
            "sonde",
            "ăn kém",
            "an kem",
            "buon non",
            "hoa chat",
            "oxaliplatin",
            "5fu",
            "irinotecan",
            "truyền",
            "truyen",
        ),
    },
)

SERVICE_CONTEXT_HEURISTICS: tuple[dict[str, tuple[str, ...]], ...] = (
    {
        "group": "x_quang_nguc",
        "service_keywords": ("x-quang ngực", "xquang ngực", "x quang ngực", "x-quang nguc"),
        "context_keywords": ("phổi", "phoi", "ngực", "nguc", "ho", "khó thở", "kho tho", "hô hấp", "ho hap"),
    },
    {
        "group": "sieu_am_o_bung",
        "service_keywords": ("siêu âm ổ bụng", "sieu am o bung"),
        "context_keywords": ("bụng", "bung", "gan", "mật", "than", "thận", "đau bụng", "dau bung"),
    },
    {
        "group": "dien_tim",
        "service_keywords": ("điện tim", "dien tim", "ecg"),
        "context_keywords": ("tim", "mạch", "mach", "huyết áp", "huyet ap", "ngực", "nguc"),
    },
    {
        "group": "ct_nguc_co_can_quang",
        "service_keywords": ("ct nguc co can quang",),
        "context_keywords": ("ung thu phoi", "phoi", "nguc", "ho", "egfr", "tki", "di can"),
    },
    {
        "group": "ct_tang_tren_o_bung",
        "service_keywords": ("ct tang tren o bung",),
        "context_keywords": ("da day", "bung", "gan", "di can", "hoa chat"),
    },
    {
        "group": "xa_hinh_xuong",
        "service_keywords": ("xa hinh xuong", "99mtc-mdp"),
        "context_keywords": ("xuong", "di can", "dau xuong", "ung thu"),
    },
    {
        "group": "truyen_hoa_chat_tinh_mach",
        "service_keywords": ("truyen hoa chat tinh mach",),
        "context_keywords": ("hoa chat", "phac do", "ung thu", "tki", "oxaliplatin", "5fu", "irinotecan", "phoi", "ho", "dau nguc", "di can"),
    },
)

CLS_CONTEXT_HEURISTICS: tuple[dict[str, tuple[str, ...]], ...] = (
    {
        "group": "huyet_hoc",
        "service_codes": ("22.0120.1370",),
        "context_keywords": ("da niêm mạc", "da niem mac", "thiếu máu", "thieu mau", "nhiễm trùng", "nhiem trung", "sốt", "sot", "mệt", "met"),
    },
    {
        "group": "sinh_hoa_mau",
        "service_codes": ("23.0058.1487", "23.0166.1494", "23.0051.1494", "23.0075.1494", "23.0007.1494", "23.0020.1493", "23.0019.1493"),
        "context_keywords": ("ăn kém", "an kem", "nuôi dưỡng", "nuoi duong", "bụng", "bung", "viêm", "viem", "nhiễm trùng", "nhiem trung", "theo dõi", "theo doi"),
    },
    {
        "group": "nuoc_tieu",
        "service_codes": ("23.0206.1596",),
        "context_keywords": ("nước tiểu", "nuoc tieu", "thận", "than", "bụng", "bung", "theo dõi", "theo doi"),
    },
)

DEPARTMENT_CONTEXT_HEURISTICS: dict[str, tuple[str, ...]] = {
    "K01": ("ung bướu", "ung buou", "u ác", "u ac", "c13", "hạ hầu", "ha hau"),
    "K19": ("viêm", "viem", "nhiễm trùng", "nhiem trung", "bụng", "bung", "theo dõi", "theo doi"),
    "K02": ("cấp cứu", "cap cuu", "hồi sức", "hoi suc", "mạch", "mach", "huyết áp", "huyet ap"),
    "K03": ("nội", "noi", "bụng", "bung", "theo dõi", "theo doi", "ăn kém", "an kem"),
    "K03.1": ("nội", "noi", "bụng", "bung", "theo dõi", "theo doi", "ăn kém", "an kem"),
    "K19.1": ("tai", "mũi", "mui", "họng", "hong", "đầu", "dau", "cổ", "co", "ung bướu", "ung buou"),
    "K19.2": ("vú", "vu", "phụ khoa", "phu khoa", "u", "ung bướu", "ung buou"),
    "K26": ("phẫu thuật", "phau thuat", "gây mê", "gay me", "hồi sức", "hoi suc"),
    "K33": (
        "xạ",
        "xa",
        "hạt nhân",
        "hat nhan",
        "ung bướu",
        "ung buou",
        "ung thu",
        "hoa chat",
        "phoi",
        "ho",
        "nguc",
        "egfr",
        "tki",
        "di can",
    ),
    "K48": ("hồi sức", "hoi suc", "tích cực", "tich cuc", "thở", "tho", "mạch", "mach"),
    "K48.1": ("giảm nhẹ", "giam nhe", "đau", "dau", "chăm sóc", "cham soc"),
}

DIAGNOSIS_CONTEXT_ALIASES: dict[str, tuple[str, ...]] = {
    "C13": ("ung thu ha hau", "ha hau", "mo thong da day", "chan sonde", "nuoi duong"),
    "C16": ("ung thu da day", "k da day", "da day", "hoa chat", "oxaliplatin", "5fu", "irinotecan", "an kem", "buon non"),
    "C22": ("ung thu gan", "hcc", "u gan", "tace", "sorafenib", "dau suon"),
    "C34": ("ung thu phoi", "phoi", "tki", "tkis", "egfr", "ho", "dau nguc", "di can"),
    "C50": ("ung thu vu", "u vu", "hoa chat", "paclitaxel", "docetaxel", "vinorelbine", "navelbin"),
}

EQUIPMENT_REQUIRED_SERVICE_HEURISTICS: tuple[dict[str, tuple[str, ...]], ...] = (
    {
        "group": "x_quang",
        "service_keywords": ("x-quang", "x quang"),
        "equipment_prefixes": ("XQ.",),
    },
    {
        "group": "sieu_am",
        "service_keywords": ("siêu âm", "sieu am"),
        "equipment_prefixes": ("SA.",),
    },
    {
        "group": "dien_tim",
        "service_keywords": ("điện tim", "dien tim", "ecg"),
        "equipment_prefixes": ("ÐT.", "DT."),
    },
    {
        "group": "xet_nghiem_huyet_hoc",
        "service_keywords": ("tổng phân tích tế bào máu", "huyết học", "huyet hoc"),
        "equipment_prefixes": ("HH.",),
    },
    {
        "group": "xet_nghiem_sinh_hoa",
        "service_keywords": ("định lượng", "dinh luong", "điện giải", "dien giai", "albumin", "ast", "alt"),
        "equipment_prefixes": ("SH.",),
    },
    {
        "group": "noi_soi",
        "service_keywords": ("nội soi", "noi soi"),
        "equipment_prefixes": ("NS.", "MNS."),
    },
)

SERVICE_DUPLICATE_THRESHOLDS: tuple[dict[str, object], ...] = (
    {"group": "giuong", "match_prefixes": ("K",), "max_per_day": 99},
    {"group": "cls_thong_thuong", "match_prefixes": ("22.", "23.", "18.", "02."), "max_per_day": 1},
    {"group": "kham", "match_prefixes": ("12.",), "max_per_day": 1},
)

CLS_DUPLICATE_THRESHOLDS: tuple[dict[str, object], ...] = (
    {"group": "cong_thuc_mau", "service_codes": ("22.0120.1370",), "max_per_day": 2},
    {"group": "nuoc_tieu", "service_codes": ("23.0206.1596",), "max_per_day": 2},
    {
        "group": "sinh_hoa_mau",
        "service_codes": ("23.0058.1487", "23.0166.1494", "23.0051.1494", "23.0075.1494", "23.0007.1494", "23.0020.1493", "23.0019.1493"),
        "max_per_day": 1,
    },
)


@dataclass(slots=True)
class PaymentPolicy:
    included_in_price_codes: dict[str, tuple[str, ...]]
    included_in_price_keywords: dict[str, tuple[str, ...]]
    source_ref: str = "payment-policy@0.1.0"

    @classmethod
    def from_json_file(cls, file_path: str | Path) -> "PaymentPolicy":
        payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
        codes = {
            key: tuple(str(item).strip() for item in values if str(item).strip())
            for key, values in payload.get("included_in_price_codes", {}).items()
        }
        keywords = {
            key: tuple(str(item).strip().lower() for item in values if str(item).strip())
            for key, values in payload.get("included_in_price_keywords", {}).items()
        }
        return cls(
            included_in_price_codes=codes,
            included_in_price_keywords=keywords,
            source_ref=payload.get("source_ref", "payment-policy@0.1.0"),
        )


@dataclass(slots=True)
class PaymentRuleEntry:
    match_type: str
    item_type: str
    match_value: str
    group_code: str | None = None
    keyword: str | None = None
    coverage_percent: Decimal | None = None
    unit_price_max: Decimal | None = None
    quantity_max: Decimal | None = None
    amount_max: Decimal | None = None
    legal_basis: tuple[str, ...] = ()
    effective_from: str | None = None
    effective_to: str | None = None
    notes: str | None = None


@dataclass(slots=True)
class PaymentRuleConfig:
    rule_id: str
    enabled: bool
    description_vi: str
    rule_kind: str
    item_types: tuple[str, ...]
    suggested_action: str
    severity: str
    impact_formula: str
    effective_from: str
    effective_to: str | None
    legal_basis: tuple[str, ...]
    matchers: tuple[PaymentRuleEntry, ...]


@dataclass(slots=True)
class PaymentRules:
    source_ref: str
    schema_version: str
    default_currency: str
    match_priority: tuple[str, ...]
    rules: dict[str, PaymentRuleConfig]

    @classmethod
    def from_json_file(cls, file_path: str | Path) -> "PaymentRules":
        payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
        rules: dict[str, PaymentRuleConfig] = {}
        for raw_rule in payload.get("rules", []):
            matcher_entries: list[PaymentRuleEntry] = []
            for matcher in raw_rule.get("matchers", []):
                match_type = str(matcher.get("match_type", "")).strip().lower()
                item_type = str(matcher.get("item_type", "")).strip().lower()
                for value in matcher.get("values", []):
                    matcher_entries.append(
                        PaymentRuleEntry(
                            match_type=match_type,
                            item_type=item_type,
                            match_value=str(value).strip(),
                        )
                    )
                for entry in matcher.get("entries", []):
                    match_value = str(
                        entry.get("match_value")
                        or entry.get("group_code")
                        or entry.get("keyword")
                        or ""
                    ).strip()
                    matcher_entries.append(
                        PaymentRuleEntry(
                            match_type=match_type,
                            item_type=item_type,
                            match_value=match_value,
                            group_code=str(entry.get("group_code")).strip() if entry.get("group_code") else None,
                            keyword=str(entry.get("keyword")).strip() if entry.get("keyword") else None,
                            coverage_percent=Decimal(str(entry["coverage_percent"])) if entry.get("coverage_percent") is not None else None,
                            unit_price_max=Decimal(str(entry["unit_price_max"])) if entry.get("unit_price_max") is not None else None,
                            quantity_max=Decimal(str(entry["quantity_max"])) if entry.get("quantity_max") is not None else None,
                            amount_max=Decimal(str(entry["amount_max"])) if entry.get("amount_max") is not None else None,
                            legal_basis=tuple(str(item).strip() for item in entry.get("legal_basis", []) if str(item).strip()),
                            effective_from=str(entry.get("effective_from")).strip() if entry.get("effective_from") else None,
                            effective_to=str(entry.get("effective_to")).strip() if entry.get("effective_to") else None,
                            notes=str(entry.get("notes")).strip() if entry.get("notes") else None,
                        )
                    )
            rule_config = PaymentRuleConfig(
                rule_id=str(raw_rule.get("rule_id", "")),
                enabled=bool(raw_rule.get("enabled", True)),
                description_vi=str(raw_rule.get("description_vi", "")),
                rule_kind=str(raw_rule.get("rule_kind", "")),
                item_types=tuple(
                    str(item).strip().lower()
                    for item in raw_rule.get("item_types", [])
                    if str(item).strip()
                ),
                suggested_action=str(raw_rule.get("suggested_action", "warn")),
                severity=str(raw_rule.get("severity", "warning")),
                impact_formula=str(raw_rule.get("impact_formula", "")),
                effective_from=str(raw_rule.get("effective_from", "1900-01-01")),
                effective_to=str(raw_rule.get("effective_to")).strip() if raw_rule.get("effective_to") else None,
                legal_basis=tuple(str(item).strip() for item in raw_rule.get("legal_basis", []) if str(item).strip()),
                matchers=tuple(matcher_entries),
            )
            rules[rule_config.rule_id] = rule_config
        return cls(
            source_ref=str(payload.get("source_ref", "payment-rules@0.1.0")),
            schema_version=str(payload.get("schema_version", "1.0")),
            default_currency=str(payload.get("default_currency", "VND")),
            match_priority=tuple(
                str(item).strip().lower()
                for item in payload.get("match_priority", ["code", "group", "keyword"])
                if str(item).strip()
            ),
            rules=rules,
        )


@dataclass(slots=True)
class InternalCodeAlias:
    code: str
    item_types: tuple[str, ...]
    item_codes: tuple[str, ...] = ()
    item_name_keywords: tuple[str, ...] = ()
    note_keywords: tuple[str, ...] = ()
    result_codes: tuple[str, ...] = ()
    result_keywords: tuple[str, ...] = ()


@dataclass(slots=True)
class InternalCodePolicy:
    source_ref: str
    aliases: dict[str, InternalCodeAlias]

    @classmethod
    def from_json_file(cls, file_path: str | Path) -> "InternalCodePolicy":
        payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
        aliases: dict[str, InternalCodeAlias] = {}
        for raw_alias in payload.get("aliases", []):
            alias = InternalCodeAlias(
                code=str(raw_alias.get("code", "")).strip(),
                item_types=tuple(
                    str(item).strip().lower()
                    for item in raw_alias.get("item_types", [])
                    if str(item).strip()
                ),
                item_codes=tuple(
                    str(item).strip()
                    for item in raw_alias.get("item_codes", [])
                    if str(item).strip()
                ),
                item_name_keywords=tuple(
                    str(item).strip().lower()
                    for item in raw_alias.get("item_name_keywords", [])
                    if str(item).strip()
                ),
                note_keywords=tuple(
                    str(item).strip().lower()
                    for item in raw_alias.get("note_keywords", [])
                    if str(item).strip()
                ),
                result_codes=tuple(
                    str(item).strip()
                    for item in raw_alias.get("result_codes", [])
                    if str(item).strip()
                ),
                result_keywords=tuple(
                    str(item).strip().lower()
                    for item in raw_alias.get("result_keywords", [])
                    if str(item).strip()
                ),
            )
            if alias.code:
                aliases[alias.code] = alias
        return cls(
            source_ref=str(payload.get("source_ref", "internal-code-policy@0.1.0")),
            aliases=aliases,
        )


@dataclass(slots=True)
class GuidelineDraftRequirement:
    evidence_type: str
    codes: tuple[str, ...]
    keywords: tuple[str, ...]
    min_count: int
    time_window: str | None


@dataclass(slots=True)
class GuidelineDraftRule:
    draft_rule_id: str
    statement_id: str
    severity: str
    suggested_action: str
    applies_to_codes: tuple[str, ...]
    decision_logic_text: str
    required_evidence: tuple[GuidelineDraftRequirement, ...]

    @classmethod
    def from_json(cls, payload: dict[str, object]) -> "GuidelineDraftRule":
        trigger = dict(payload.get("trigger", {}))
        requirements = tuple(
            GuidelineDraftRequirement(
                evidence_type=str(item.get("evidence_type", "")).strip().lower(),
                codes=tuple(
                    str(code).strip()
                    for code in item.get("codes", [])
                    if str(code).strip()
                ),
                keywords=tuple(
                    str(keyword).strip().lower()
                    for keyword in item.get("keywords", [])
                    if str(keyword).strip()
                ),
                min_count=int(item.get("min_count", 1)),
                time_window=str(item.get("time_window")).strip() if item.get("time_window") else None,
            )
            for item in payload.get("required_evidence", [])
        )
        return cls(
            draft_rule_id=str(payload.get("draft_rule_id", "")).strip(),
            statement_id=str(payload.get("statement_id", "")).strip(),
            severity=str(payload.get("severity", "pending")).strip(),
            suggested_action=str(payload.get("suggested_action", "request_more")).strip(),
            applies_to_codes=tuple(
                str(code).strip()
                for code in trigger.get("applies_to_codes", [])
                if str(code).strip()
            ),
            decision_logic_text=str(payload.get("decision_logic_text", "")).strip(),
            required_evidence=requirements,
        )


@dataclass(slots=True)
class DiseaseLineRule:
    rule_id: str
    line_types: tuple[str, ...]
    item_codes: tuple[str, ...] = ()
    item_code_prefixes: tuple[str, ...] = ()
    item_name_keywords: tuple[str, ...] = ()
    department_codes: tuple[str, ...] = ()
    required_note_keywords: tuple[str, ...] = ()
    required_note_match: str = "any"
    context_label: str | None = None

    @classmethod
    def from_json(cls, payload: dict[str, object]) -> "DiseaseLineRule":
        return cls(
            rule_id=str(payload.get("rule_id", "")).strip(),
            line_types=tuple(
                str(item).strip().lower()
                for item in payload.get("line_types", [])
                if str(item).strip()
            ),
            item_codes=tuple(
                str(item).strip()
                for item in payload.get("item_codes", [])
                if str(item).strip()
            ),
            item_code_prefixes=tuple(
                str(item).strip().upper()
                for item in payload.get("item_code_prefixes", [])
                if str(item).strip()
            ),
            item_name_keywords=tuple(
                str(item).strip().lower()
                for item in payload.get("item_name_keywords", [])
                if str(item).strip()
            ),
            department_codes=tuple(
                str(item).strip()
                for item in payload.get("department_codes", [])
                if str(item).strip()
            ),
            required_note_keywords=tuple(
                str(item).strip().lower()
                for item in payload.get("required_note_keywords", [])
                if str(item).strip()
            ),
            required_note_match=str(payload.get("required_note_match", "any")).strip().lower() or "any",
            context_label=str(payload.get("context_label")).strip() if payload.get("context_label") else None,
        )


@dataclass(slots=True)
class DiseaseResultRule:
    rule_id: str
    service_codes: tuple[str, ...] = ()
    indicator_keywords: tuple[str, ...] = ()
    required_note_keywords: tuple[str, ...] = ()
    required_note_match: str = "any"
    context_label: str | None = None

    @classmethod
    def from_json(cls, payload: dict[str, object]) -> "DiseaseResultRule":
        return cls(
            rule_id=str(payload.get("rule_id", "")).strip(),
            service_codes=tuple(
                str(item).strip()
                for item in payload.get("service_codes", [])
                if str(item).strip()
            ),
            indicator_keywords=tuple(
                str(item).strip().lower()
                for item in payload.get("indicator_keywords", [])
                if str(item).strip()
            ),
            required_note_keywords=tuple(
                str(item).strip().lower()
                for item in payload.get("required_note_keywords", [])
                if str(item).strip()
            ),
            required_note_match=str(payload.get("required_note_match", "any")).strip().lower() or "any",
            context_label=str(payload.get("context_label")).strip() if payload.get("context_label") else None,
        )


@dataclass(slots=True)
class DiseaseClinicalProfile:
    profile_id: str
    diagnosis_code_prefixes: tuple[str, ...]
    diagnosis_aliases: tuple[str, ...]
    department_context_keywords: dict[str, tuple[str, ...]]
    line_rules: tuple[DiseaseLineRule, ...]
    result_rules: tuple[DiseaseResultRule, ...]

    @classmethod
    def from_json(cls, payload: dict[str, object]) -> "DiseaseClinicalProfile":
        return cls(
            profile_id=str(payload.get("profile_id", "")).strip(),
            diagnosis_code_prefixes=tuple(
                str(item).strip().upper()
                for item in payload.get("diagnosis_code_prefixes", [])
                if str(item).strip()
            ),
            diagnosis_aliases=tuple(
                str(item).strip().lower()
                for item in payload.get("diagnosis_aliases", [])
                if str(item).strip()
            ),
            department_context_keywords={
                str(key).strip(): tuple(
                    str(item).strip().lower()
                    for item in values
                    if str(item).strip()
                )
                for key, values in dict(payload.get("department_context_keywords", {})).items()
            },
            line_rules=tuple(
                DiseaseLineRule.from_json(dict(item))
                for item in payload.get("line_rules", [])
            ),
            result_rules=tuple(
                DiseaseResultRule.from_json(dict(item))
                for item in payload.get("result_rules", [])
            ),
        )


@dataclass(slots=True)
class ClinicalPolicy:
    drug_context_heuristics: tuple[dict[str, tuple[str, ...]], ...]
    service_context_heuristics: tuple[dict[str, tuple[str, ...]], ...]
    cls_context_heuristics: tuple[dict[str, tuple[str, ...]], ...]
    department_context_heuristics: dict[str, tuple[str, ...]]
    diagnosis_context_aliases: dict[str, tuple[str, ...]]
    disease_profiles: tuple[DiseaseClinicalProfile, ...]
    equipment_required_service_heuristics: tuple[dict[str, tuple[str, ...]], ...]
    service_duplicate_thresholds: tuple[dict[str, object], ...]
    cls_duplicate_thresholds: tuple[dict[str, object], ...]
    source_ref: str = "clinical-policy@0.1.0"

    @classmethod
    def from_defaults(cls) -> "ClinicalPolicy":
        return cls(
            drug_context_heuristics=DRUG_CONTEXT_HEURISTICS,
            service_context_heuristics=SERVICE_CONTEXT_HEURISTICS,
            cls_context_heuristics=CLS_CONTEXT_HEURISTICS,
            department_context_heuristics=DEPARTMENT_CONTEXT_HEURISTICS,
            diagnosis_context_aliases=DIAGNOSIS_CONTEXT_ALIASES,
            disease_profiles=(),
            equipment_required_service_heuristics=EQUIPMENT_REQUIRED_SERVICE_HEURISTICS,
            service_duplicate_thresholds=SERVICE_DUPLICATE_THRESHOLDS,
            cls_duplicate_thresholds=CLS_DUPLICATE_THRESHOLDS,
        )

    @classmethod
    def from_json_file(cls, file_path: str | Path) -> "ClinicalPolicy":
        payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
        return cls(
            drug_context_heuristics=cls._normalize_tuple_mapping_list(
                payload.get("drug_context_heuristics", [])
            ),
            service_context_heuristics=cls._normalize_tuple_mapping_list(
                payload.get("service_context_heuristics", [])
            ),
            cls_context_heuristics=cls._normalize_tuple_mapping_list(
                payload.get("cls_context_heuristics", [])
            ),
            department_context_heuristics={
                str(key): tuple(str(item).strip().lower() for item in values if str(item).strip())
                for key, values in dict(payload.get("department_context_heuristics", {})).items()
            },
            diagnosis_context_aliases={
                str(key).strip().upper(): tuple(
                    str(item).strip().lower() for item in values if str(item).strip()
                )
                for key, values in dict(payload.get("diagnosis_context_aliases", {})).items()
            },
            disease_profiles=tuple(
                DiseaseClinicalProfile.from_json(dict(item))
                for item in payload.get("disease_profiles", [])
            ),
            equipment_required_service_heuristics=cls._normalize_tuple_mapping_list(
                payload.get("equipment_required_service_heuristics", [])
            ),
            service_duplicate_thresholds=tuple(payload.get("service_duplicate_thresholds", [])),
            cls_duplicate_thresholds=tuple(payload.get("cls_duplicate_thresholds", [])),
            source_ref=payload.get("source_ref", "clinical-policy@0.1.0"),
        )

    @staticmethod
    def _normalize_tuple_mapping_list(values: object) -> tuple[dict[str, tuple[str, ...]], ...]:
        normalized: list[dict[str, object]] = []
        for item in list(values):
            mapping: dict[str, object] = {}
            for key, raw_value in dict(item).items():
                if str(key) == "group":
                    if isinstance(raw_value, list):
                        mapping[str(key)] = str(raw_value[0]).strip().lower() if raw_value else ""
                    else:
                        mapping[str(key)] = str(raw_value).strip().lower()
                    continue
                if isinstance(raw_value, list):
                    mapping[str(key)] = tuple(
                        str(entry).strip().lower() for entry in raw_value if str(entry).strip()
                    )
                else:
                    mapping[str(key)] = tuple([str(raw_value).strip().lower()])
            normalized.append(mapping)
        return tuple(normalized)  # type: ignore[return-value]


class DeterministicRuleEngine:
    def __init__(
        self,
        registry: RuleRegistry,
        payment_policy_file: str | Path | None = None,
        payment_rules_file: str | Path | None = None,
        clinical_policy_file: str | Path | None = None,
        guideline_rule_drafts_file: str | Path | None = None,
        internal_code_policy_file: str | Path | None = None,
    ):
        self._registry = registry
        self._current_target_date = ""
        self._payment_policy = self._load_payment_policy(payment_policy_file)
        self._payment_rules = self._load_payment_rules(payment_rules_file)
        self._clinical_policy = self._load_clinical_policy(clinical_policy_file)
        self._guideline_rule_drafts = self._load_guideline_rule_drafts(guideline_rule_drafts_file)
        self._internal_code_policy = self._load_internal_code_policy(internal_code_policy_file)
        self._evaluators = {
            "ELIG.CARD_STATUS.001": self._eval_card_status,
            "ELIG.ROUTE.001": self._eval_route,
            "LOGIC.CLINICAL_CONTEXT.001": self._eval_clinical_context,
            "LOGIC.DUPLICATE_LINE.001": self._eval_duplicate_line,
            "MASTER.ITEM_CODE.001": self._eval_item_code,
            "MASTER.ITEM_EFFECTIVE.001": self._eval_item_effective,
            "MASTER.EQUIPMENT_REFERENCE.001": self._eval_equipment_reference,
            "PAY.OUT_OF_SCOPE.001": self._eval_pay_out_of_scope,
            "PAY.LIMIT.COVERAGE_PERCENT.001": self._eval_pay_limit,
            "PAY.LIMIT.UNIT_PRICE_MAX.001": self._eval_pay_limit,
            "PAY.LIMIT.QUANTITY_MAX.001": self._eval_pay_limit,
            "PAY.LIMIT.AMOUNT_MAX.001": self._eval_pay_limit,
            "PAY.INCLUDED_IN_PRICE.001": self._eval_included_in_price,
            "MASTER.PRACTITIONER_DEPARTMENT.001": self._eval_practitioner_department,
            "MASTER.PRACTITIONER_EXISTS.001": self._eval_practitioner_exists,
            "MASTER.PRACTITIONER_SCOPE.001": self._eval_practitioner_scope,
            "STRUCT.LINK_KEY.001": self._eval_link_key,
            "STRUCT.LINE_AMOUNT.001": self._eval_line_amount,
            "STRUCT.ADMISSION_DISCHARGE.001": self._eval_admission_discharge,
            "STRUCT.HEADER_SUM.001": self._eval_header_sum,
            "LOGIC.TIME_WINDOW.001": self._eval_time_window,
        }

    def evaluate(
        self,
        claim: ParsedClaim,
        target_date: str,
        eligibility_result: EligibilityResult | None = None,
        master_snapshot: MasterDataSnapshot | None = None,
    ) -> EngineResult:
        self._current_target_date = target_date
        active_rules = self._registry.list_effective_rules(target_date)
        hits: list[RuleHit] = []

        for rule in active_rules:
            evaluator = self._evaluators.get(rule.rule_id)
            if evaluator is None:
                continue
            hits.extend(evaluator(claim, rule, eligibility_result, master_snapshot))

        hits.extend(self._eval_guideline_rule_drafts(claim))
        return EngineResult(claim_id=claim.header.claim_id, hits=hits)

    def _parse_datetime(self, raw_value: str) -> datetime:
        normalized = raw_value.strip()
        if "T" in normalized or "-" in normalized or ":" in normalized:
            return datetime.fromisoformat(normalized)
        if len(normalized) == 12:
            return datetime.strptime(normalized, "%Y%m%d%H%M")
        if len(normalized) == 14:
            return datetime.strptime(normalized, "%Y%m%d%H%M%S")
        raise ValueError(f"Unsupported datetime format: {raw_value}")

    def _safe_parse_datetime(self, raw_value: str | None) -> datetime | None:
        if not raw_value:
            return None
        try:
            return self._parse_datetime(raw_value)
        except ValueError:
            return None

    def _clinical_diagnosis_tokens(self, claim: ParsedClaim) -> set[str]:
        tokens = {self._normalize_match_text(claim.header.primary_diagnosis_code)}
        tokens.update(self._normalize_match_text(code) for code in claim.header.secondary_diagnosis_codes)
        return {token for token in tokens if token}

    def _clinical_diagnosis_aliases(self, claim: ParsedClaim) -> set[str]:
        aliases: set[str] = set()
        for profile in self._matched_disease_profiles(claim):
            aliases.update(profile.diagnosis_aliases)
        diagnosis_codes = [claim.header.primary_diagnosis_code, *claim.header.secondary_diagnosis_codes]
        for raw_code in diagnosis_codes:
            normalized_code = self._normalize_match_text(raw_code).upper()
            if not normalized_code:
                continue
            for code_prefix, code_aliases in self._clinical_policy.diagnosis_context_aliases.items():
                if normalized_code.startswith(code_prefix):
                    aliases.update(code_aliases)
        return aliases

    def _matched_disease_profiles(self, claim: ParsedClaim) -> tuple[DiseaseClinicalProfile, ...]:
        diagnosis_codes = [claim.header.primary_diagnosis_code, *claim.header.secondary_diagnosis_codes]
        normalized_codes = [
            self._normalize_match_text(code).upper()
            for code in diagnosis_codes
            if self._normalize_match_text(code)
        ]
        matched: list[DiseaseClinicalProfile] = []
        for profile in self._clinical_policy.disease_profiles:
            if any(
                normalized_code.startswith(prefix)
                for normalized_code in normalized_codes
                for prefix in profile.diagnosis_code_prefixes
                if prefix
            ):
                matched.append(profile)
        return tuple(matched)

    def _department_context_keywords_for_line(
        self,
        line,
        matched_profiles: tuple[DiseaseClinicalProfile, ...],
    ) -> tuple[str, ...]:
        department_code = (line.department_code or "").strip()
        profile_keywords: list[str] = []
        if department_code:
            for profile in matched_profiles:
                profile_keywords.extend(profile.department_context_keywords.get(department_code, ()))
        if profile_keywords:
            return tuple(dict.fromkeys(profile_keywords))
        return self._clinical_policy.department_context_heuristics.get(department_code, ())

    def _matches_keyword_rule(self, related_text: str, keywords: tuple[str, ...], match_mode: str) -> bool:
        if not keywords:
            return True
        if match_mode == "all":
            return all(keyword in related_text for keyword in keywords)
        return any(keyword in related_text for keyword in keywords)

    def _match_disease_line_rule(
        self,
        line,
        matched_profiles: tuple[DiseaseClinicalProfile, ...],
    ) -> tuple[DiseaseClinicalProfile, DiseaseLineRule] | None:
        line_type = (line.line_type or "").strip().lower()
        item_code = (line.item_code or "").strip()
        item_code_upper = item_code.upper()
        normalized_name = self._normalize_match_text(line.item_name)
        department_code = (line.department_code or "").strip()
        for profile in matched_profiles:
            for profile_rule in profile.line_rules:
                if profile_rule.line_types and line_type not in profile_rule.line_types:
                    continue
                if profile_rule.department_codes and department_code not in profile_rule.department_codes:
                    continue
                has_item_matcher = bool(
                    profile_rule.item_codes
                    or profile_rule.item_code_prefixes
                    or profile_rule.item_name_keywords
                )
                if profile_rule.item_codes and item_code in profile_rule.item_codes:
                    return profile, profile_rule
                if profile_rule.item_code_prefixes and any(
                    item_code_upper.startswith(prefix) for prefix in profile_rule.item_code_prefixes
                ):
                    return profile, profile_rule
                if profile_rule.item_name_keywords and any(
                    keyword in normalized_name for keyword in profile_rule.item_name_keywords
                ):
                    return profile, profile_rule
                if not has_item_matcher:
                    return profile, profile_rule
        return None

    def _match_disease_result_rule(
        self,
        result,
        matched_profiles: tuple[DiseaseClinicalProfile, ...],
    ) -> tuple[DiseaseClinicalProfile, DiseaseResultRule] | None:
        result_text = self._result_search_text(result)
        service_code = (result.service_code or "").strip()
        for profile in matched_profiles:
            for profile_rule in profile.result_rules:
                has_matcher = bool(profile_rule.service_codes or profile_rule.indicator_keywords)
                if profile_rule.service_codes and service_code in profile_rule.service_codes:
                    return profile, profile_rule
                if profile_rule.indicator_keywords and any(
                    keyword in result_text for keyword in profile_rule.indicator_keywords
                ):
                    return profile, profile_rule
                if not has_matcher:
                    return profile, profile_rule
        return None

    def _normalize_match_text(self, raw_value: str | None) -> str:
        normalized = unicodedata.normalize("NFD", (raw_value or "").strip().lower())
        normalized = normalized.replace("đ", "d")
        return "".join(character for character in normalized if unicodedata.category(character) != "Mn")

    def _note_has_diagnosis_context(
        self,
        note_text: str,
        diagnosis_tokens: set[str],
        diagnosis_aliases: set[str],
    ) -> bool:
        normalized = self._normalize_match_text(note_text)
        if "chan doan" in normalized:
            return True
        return any(token in normalized for token in diagnosis_tokens | diagnosis_aliases)

    def _match_drug_heuristic(self, item_name: str) -> dict[str, tuple[str, ...]] | None:
        normalized = item_name.lower()
        for heuristic in self._clinical_policy.drug_context_heuristics:
            if any(keyword in normalized for keyword in heuristic["drug_keywords"]):
                return heuristic
        return None

    def _match_service_heuristic(self, item_name: str) -> dict[str, tuple[str, ...]] | None:
        normalized = item_name.lower()
        for heuristic in self._clinical_policy.service_context_heuristics:
            if any(keyword in normalized for keyword in heuristic["service_keywords"]):
                return heuristic
        return None

    def _match_cls_heuristic(self, service_code: str) -> dict[str, tuple[str, ...]] | None:
        for heuristic in self._clinical_policy.cls_context_heuristics:
            if service_code in heuristic["service_codes"]:
                return heuristic
        return None

    def _match_equipment_required_heuristic(self, item_name: str) -> dict[str, tuple[str, ...]] | None:
        normalized = item_name.lower()
        for heuristic in self._clinical_policy.equipment_required_service_heuristics:
            if any(keyword in normalized for keyword in heuristic["service_keywords"]):
                return heuristic
        return None

    def _service_duplicate_threshold(self, item_code: str) -> int:
        for rule in self._clinical_policy.service_duplicate_thresholds:
            if any(item_code.startswith(prefix) for prefix in rule["match_prefixes"]):
                return int(rule["max_per_day"])
        return 1

    def _cls_duplicate_threshold(self, service_code: str) -> int:
        for rule in self._clinical_policy.cls_duplicate_thresholds:
            if service_code in rule["service_codes"]:
                return int(rule["max_per_day"])
        return 1

    def _related_clinical_notes(
        self,
        claim: ParsedClaim,
        parsed_notes: list[tuple[object, datetime | None]],
        reference_time: datetime,
    ) -> list[object]:
        related_notes: list[object] = []
        for note, note_time in parsed_notes:
            if note_time is None:
                continue
            if note_time <= reference_time and reference_time - note_time <= timedelta(days=1):
                related_notes.append(note)
                continue
            if claim.header.visit_type != "03":
                continue
            if note_time.date() == reference_time.date():
                related_notes.append(note)
                continue
            if note_time < reference_time and reference_time - note_time <= timedelta(hours=36):
                related_notes.append(note)
        return related_notes

    def _load_payment_policy(self, payment_policy_file: str | Path | None) -> PaymentPolicy:
        default_path = Path(__file__).resolve().parents[2] / "config" / "payment_policy.mwp.json"
        target_file = Path(payment_policy_file) if payment_policy_file is not None else default_path
        if not target_file.exists():
            return PaymentPolicy(included_in_price_codes={}, included_in_price_keywords={})
        return PaymentPolicy.from_json_file(target_file)

    def _load_payment_rules(self, payment_rules_file: str | Path | None) -> PaymentRules:
        default_path = Path(__file__).resolve().parents[2] / "config" / "payment_rules.mwp.json"
        target_file = Path(payment_rules_file) if payment_rules_file is not None else default_path
        if not target_file.exists():
            return PaymentRules(
                source_ref="payment-rules@0.1.0",
                schema_version="1.0",
                default_currency="VND",
                match_priority=("code", "group", "keyword"),
                rules={},
            )
        return PaymentRules.from_json_file(target_file)

    def _load_clinical_policy(self, clinical_policy_file: str | Path | None) -> ClinicalPolicy:
        default_path = Path(__file__).resolve().parents[2] / "config" / "clinical_policy.mwp.json"
        target_file = Path(clinical_policy_file) if clinical_policy_file is not None else default_path
        if not target_file.exists():
            return ClinicalPolicy.from_defaults()
        return ClinicalPolicy.from_json_file(target_file)

    def _load_guideline_rule_drafts(
        self,
        guideline_rule_drafts_file: str | Path | None,
    ) -> tuple[GuidelineDraftRule, ...]:
        default_path = (
            Path(__file__).resolve().parents[4]
            / "runtime"
            / "guideline-rules"
            / "drafts"
            / "guideline_rule_drafts.jsonl"
        )
        target_file = Path(guideline_rule_drafts_file) if guideline_rule_drafts_file is not None else default_path
        if not target_file.exists():
            return ()
        drafts: list[GuidelineDraftRule] = []
        for raw_line in target_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            drafts.append(GuidelineDraftRule.from_json(json.loads(line)))
        return tuple(drafts)

    def _load_internal_code_policy(
        self,
        internal_code_policy_file: str | Path | None,
    ) -> InternalCodePolicy:
        default_path = Path(__file__).resolve().parents[2] / "config" / "internal_code_policy.mwp.json"
        target_file = Path(internal_code_policy_file) if internal_code_policy_file is not None else default_path
        if not target_file.exists():
            return InternalCodePolicy(source_ref="internal-code-policy@0.1.0", aliases={})
        return InternalCodePolicy.from_json_file(target_file)

    def _normalize_code_token(self, raw_value: str | None) -> str:
        normalized = self._normalize_match_text(raw_value)
        normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
        return " ".join(part for part in normalized.split() if part)

    def _code_reference_matches_line(self, code_ref: str, line) -> bool:
        reference = (code_ref or "").strip()
        if not reference:
            return False
        if line.item_code and line.item_code == reference:
            return True
        normalized_name = self._normalize_match_text(line.item_name)
        normalized_ref = self._normalize_code_token(reference)
        if normalized_ref and normalized_ref in normalized_name:
            return True
        if not reference.startswith("INT."):
            return False
        alias = self._internal_code_policy.aliases.get(reference)
        if alias is None:
            return False
        line_type = (line.line_type or "").strip().lower()
        if alias.item_types and line_type not in alias.item_types:
            return False
        if alias.item_codes and line.item_code in alias.item_codes:
            return True
        return any(keyword in normalized_name for keyword in alias.item_name_keywords)

    def _result_search_text(self, result) -> str:
        return self._normalize_match_text(
            " ".join(
                filter(
                    None,
                    [
                        result.service_code,
                        result.indicator_code,
                        result.indicator_name,
                        result.description,
                        result.conclusion,
                        result.value,
                    ],
                )
            )
        )

    def _code_reference_matches_result(self, code_ref: str, result) -> bool:
        reference = (code_ref or "").strip()
        if not reference:
            return False
        if result.service_code and result.service_code == reference:
            return True
        result_text = self._result_search_text(result)
        normalized_ref = self._normalize_code_token(reference)
        if normalized_ref and normalized_ref in result_text:
            return True
        if not reference.startswith("INT."):
            return False
        alias = self._internal_code_policy.aliases.get(reference)
        if alias is None:
            return False
        if alias.result_codes and result.service_code in alias.result_codes:
            return True
        return any(keyword in result_text for keyword in alias.result_keywords)

    def _code_reference_matches_note_text(self, code_ref: str, note_text: str) -> bool:
        reference = (code_ref or "").strip()
        if not reference:
            return False
        normalized_note = self._normalize_match_text(note_text)
        normalized_ref = self._normalize_code_token(reference)
        if normalized_ref and normalized_ref in normalized_note:
            return True
        if not reference.startswith("INT."):
            return False
        alias = self._internal_code_policy.aliases.get(reference)
        if alias is None:
            return False
        return any(keyword in normalized_note for keyword in alias.note_keywords)

    def _requirement_matches_note(self, requirement: GuidelineDraftRequirement, note) -> bool:
        normalized_text = self._normalize_match_text(note.note_text)
        has_keyword = any(keyword in normalized_text for keyword in requirement.keywords)
        has_code = any(self._code_reference_matches_note_text(code, note.note_text) for code in requirement.codes)
        return has_keyword or has_code

    def _requirement_matches_line(self, requirement: GuidelineDraftRequirement, line) -> bool:
        normalized_name = self._normalize_match_text(line.item_name)
        has_keyword = any(keyword in normalized_name for keyword in requirement.keywords)
        has_code = any(self._code_reference_matches_line(code, line) for code in requirement.codes)
        if requirement.codes or requirement.keywords:
            return has_keyword or has_code
        return False

    def _requirement_matches_result(self, requirement: GuidelineDraftRequirement, result) -> bool:
        result_text = self._result_search_text(result)
        has_keyword = any(keyword in result_text for keyword in requirement.keywords)
        has_code = any(self._code_reference_matches_result(code, result) for code in requirement.codes)
        if requirement.codes or requirement.keywords:
            return has_keyword or has_code
        return False

    def _evidence_match_count(self, claim: ParsedClaim, requirement: GuidelineDraftRequirement) -> int:
        evidence_type = requirement.evidence_type
        if evidence_type == "xml5_note":
            return sum(1 for note in claim.clinical_notes if self._requirement_matches_note(requirement, note))
        if evidence_type in {"order", "procedure_note"}:
            return sum(1 for line in claim.lines if self._requirement_matches_line(requirement, line))
        if evidence_type in {"imaging", "lab_result"}:
            result_matches = sum(
                1 for result in claim.clinical_results if self._requirement_matches_result(requirement, result)
            )
            line_matches = sum(1 for line in claim.lines if self._requirement_matches_line(requirement, line))
            return result_matches + line_matches
        return 0

    def _guideline_target_lines(self, claim: ParsedClaim, draft: GuidelineDraftRule) -> list:
        if not draft.applies_to_codes:
            return []
        return [
            line
            for line in claim.lines
            if any(self._code_reference_matches_line(code_ref, line) for code_ref in draft.applies_to_codes)
        ]

    def _missing_guideline_evidence(
        self,
        claim: ParsedClaim,
        draft: GuidelineDraftRule,
    ) -> list[GuidelineDraftRequirement]:
        return [
            requirement
            for requirement in draft.required_evidence
            if self._evidence_match_count(claim, requirement) < max(1, requirement.min_count)
        ]

    def _guideline_missing_evidence_labels(
        self,
        requirements: list[GuidelineDraftRequirement],
    ) -> list[str]:
        labels: list[str] = []
        for requirement in requirements:
            details = list(requirement.codes or ()) or list(requirement.keywords or ())
            if details:
                labels.append(f"{requirement.evidence_type}:{details[0]}")
            else:
                labels.append(requirement.evidence_type)
        return labels

    def _eval_guideline_rule_drafts(self, claim: ParsedClaim) -> list[RuleHit]:
        if not self._guideline_rule_drafts:
            return []
        hits: list[RuleHit] = []
        for draft in self._guideline_rule_drafts:
            target_lines = self._guideline_target_lines(claim, draft)
            if not target_lines:
                continue
            missing_requirements = self._missing_guideline_evidence(claim, draft)
            if not missing_requirements:
                continue
            missing_labels = self._guideline_missing_evidence_labels(missing_requirements)
            matched_codes = ", ".join(draft.applies_to_codes)
            for line in target_lines:
                hits.append(
                    RuleHit(
                        rule_hit_id=f"{claim.header.claim_id}:{draft.draft_rule_id}:{line.line_id}",
                        claim_id=claim.header.claim_id,
                        line_id=line.line_id,
                        rule_id=draft.draft_rule_id,
                        severity=draft.severity,
                        legal_basis="guideline-rule-draft",
                        message=(
                            f"Dong {line.line_id} ({line.item_name}) khop guideline draft theo {matched_codes} "
                            f"nhung chua du chung cu: {', '.join(missing_labels)}."
                        ),
                        suggested_action=draft.suggested_action,
                        estimated_amount_impact=line.amount,
                        required_evidence=missing_labels,
                    )
                )
        return hits

    def _eval_header_sum(
        self,
        claim: ParsedClaim,
        rule: RuleDefinition,
        eligibility_result: EligibilityResult | None = None,
        master_snapshot: MasterDataSnapshot | None = None,
    ) -> list[RuleHit]:
        line_sum = sum((line.amount for line in claim.lines), Decimal("0"))
        if line_sum == claim.header.total_amount:
            return []

        impact = abs(claim.header.total_amount - line_sum)
        return [
            RuleHit(
                rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}",
                claim_id=claim.header.claim_id,
                rule_id=rule.rule_id,
                severity=rule.severity,
                legal_basis=rule.legal_basis,
                message=(
                    f"Tong tien header {claim.header.total_amount} khong khop tong line {line_sum}"
                ),
                suggested_action=rule.suggested_action,
                estimated_amount_impact=impact,
            )
        ]

    def _eval_link_key(
        self,
        claim: ParsedClaim,
        rule: RuleDefinition,
        eligibility_result: EligibilityResult | None = None,
        master_snapshot: MasterDataSnapshot | None = None,
    ) -> list[RuleHit]:
        hits: list[RuleHit] = []
        claim_id = claim.header.claim_id
        for line in claim.lines:
            if line.claim_id == claim_id:
                continue
            hits.append(
                RuleHit(
                    rule_hit_id=f"{claim_id}:{rule.rule_id}:{line.line_id}",
                    claim_id=claim_id,
                    line_id=line.line_id,
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    legal_basis=rule.legal_basis,
                    message=(
                        f"Dong {line.line_id} co claim_id {line.claim_id} khong trung MA_LK {claim_id}."
                    ),
                    suggested_action=rule.suggested_action,
                    estimated_amount_impact=line.amount,
                    required_evidence=[line.source_xml or "claim_line"],
                )
            )
        for result in claim.clinical_results:
            if result.claim_id == claim_id:
                continue
            hits.append(
                RuleHit(
                    rule_hit_id=f"{claim_id}:{rule.rule_id}:{result.result_id}",
                    claim_id=claim_id,
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    legal_basis=rule.legal_basis,
                    message=(
                        f"Ket qua {result.result_id} co claim_id {result.claim_id} khong trung MA_LK {claim_id}."
                    ),
                    suggested_action=rule.suggested_action,
                    required_evidence=[result.source_xml or "clinical_result"],
                )
            )
        for note in claim.clinical_notes:
            if note.claim_id == claim_id:
                continue
            hits.append(
                RuleHit(
                    rule_hit_id=f"{claim_id}:{rule.rule_id}:{note.note_id}",
                    claim_id=claim_id,
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    legal_basis=rule.legal_basis,
                    message=(
                        f"Dien bien {note.note_id} co claim_id {note.claim_id} khong trung MA_LK {claim_id}."
                    ),
                    suggested_action=rule.suggested_action,
                    required_evidence=[note.source_xml or "clinical_note"],
                )
            )
        for document in claim.documents:
            if document.claim_id == claim_id:
                continue
            hits.append(
                RuleHit(
                    rule_hit_id=f"{claim_id}:{rule.rule_id}:{document.document_id}",
                    claim_id=claim_id,
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    legal_basis=rule.legal_basis,
                    message=(
                        f"Tai lieu {document.document_id} co claim_id {document.claim_id} khong trung MA_LK {claim_id}."
                    ),
                    suggested_action=rule.suggested_action,
                    required_evidence=[document.document_type or "document"],
                )
            )
        return hits

    def _eval_line_amount(
        self,
        claim: ParsedClaim,
        rule: RuleDefinition,
        eligibility_result: EligibilityResult | None = None,
        master_snapshot: MasterDataSnapshot | None = None,
    ) -> list[RuleHit]:
        hits: list[RuleHit] = []
        for line in claim.lines:
            expected_amount = (line.quantity or Decimal("0")) * (line.unit_price or Decimal("0"))
            if abs(expected_amount - line.amount) <= Decimal("0.01"):
                continue
            hits.append(
                RuleHit(
                    rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{line.line_id}",
                    claim_id=claim.header.claim_id,
                    line_id=line.line_id,
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    legal_basis=rule.legal_basis,
                    message=(
                        f"Dong {line.line_id} co thanh tien {line.amount} khong khop cong thuc "
                        f"{line.quantity} * {line.unit_price} = {expected_amount}."
                    ),
                    suggested_action=rule.suggested_action,
                    estimated_amount_impact=abs(expected_amount - line.amount),
                    required_evidence=[line.source_xml or "claim_line"],
                )
            )
        return hits

    def _eval_admission_discharge(
        self,
        claim: ParsedClaim,
        rule: RuleDefinition,
        eligibility_result: EligibilityResult | None = None,
        master_snapshot: MasterDataSnapshot | None = None,
    ) -> list[RuleHit]:
        admission_time = self._safe_parse_datetime(claim.header.admission_time)
        discharge_time = self._safe_parse_datetime(claim.header.discharge_time)
        if admission_time is None or discharge_time is None or admission_time <= discharge_time:
            return []
        return [
            RuleHit(
                rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}",
                claim_id=claim.header.claim_id,
                rule_id=rule.rule_id,
                severity=rule.severity,
                legal_basis=rule.legal_basis,
                message=(
                    f"Ngay vao vien {claim.header.admission_time} lon hon ngay ra vien {claim.header.discharge_time}."
                ),
                suggested_action=rule.suggested_action,
                estimated_amount_impact=claim.header.total_amount,
                required_evidence=["XML1"],
            )
        ]

    def _eval_time_window(
        self,
        claim: ParsedClaim,
        rule: RuleDefinition,
        eligibility_result: EligibilityResult | None = None,
        master_snapshot: MasterDataSnapshot | None = None,
    ) -> list[RuleHit]:
        discharge_time = self._parse_datetime(claim.header.discharge_time)
        hits: list[RuleHit] = []

        for line in claim.lines:
            if not line.execution_time:
                continue
            execution_time = self._parse_datetime(line.execution_time)
            if execution_time <= discharge_time:
                continue
            hits.append(
                RuleHit(
                    rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{line.line_id}",
                    claim_id=claim.header.claim_id,
                    line_id=line.line_id,
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    legal_basis=rule.legal_basis,
                    message=(
                        f"Dong {line.line_id} phat sinh sau thoi diem ra vien {claim.header.discharge_time}"
                    ),
                    suggested_action=rule.suggested_action,
                    estimated_amount_impact=line.amount,
                )
            )

        return hits

    def _eval_card_status(
        self,
        claim: ParsedClaim,
        rule: RuleDefinition,
        eligibility_result: EligibilityResult | None = None,
        master_snapshot: MasterDataSnapshot | None = None,
    ) -> list[RuleHit]:
        if eligibility_result is None or eligibility_result.card_valid:
            return []

        return [
            RuleHit(
                rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}",
                claim_id=claim.header.claim_id,
                rule_id=rule.rule_id,
                severity=rule.severity,
                legal_basis=rule.legal_basis,
                message="The BHYT khong hop le theo eligibility policy dang ap dung.",
                suggested_action=rule.suggested_action,
                estimated_amount_impact=claim.header.insurance_amount,
            )
        ]

    def _eval_clinical_context(
        self,
        claim: ParsedClaim,
        rule: RuleDefinition,
        eligibility_result: EligibilityResult | None = None,
        master_snapshot: MasterDataSnapshot | None = None,
    ) -> list[RuleHit]:
        hits: list[RuleHit] = []
        line_codes = {line.item_code for line in claim.lines if line.item_code}

        if claim.header.visit_type == "03" and not claim.clinical_notes:
            hits.append(
                RuleHit(
                    rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:clinical-notes",
                    claim_id=claim.header.claim_id,
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    legal_basis=rule.legal_basis,
                    message="Ho so dieu tri chua co dien bien lam sang XML5 de doi chieu boi canh dieu tri.",
                    suggested_action=rule.suggested_action,
                    required_evidence=["XML5"],
                )
            )

        for result in claim.clinical_results:
            if not result.service_code or result.service_code in line_codes:
                continue
            hits.append(
                RuleHit(
                    rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{result.result_id}",
                    claim_id=claim.header.claim_id,
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    legal_basis=rule.legal_basis,
                    message=(
                        f"Ket qua can lam sang {result.result_id} co ma dich vu {result.service_code} "
                        "nhung chua thay dong chi phi tuong ung trong ho so."
                    ),
                    suggested_action=rule.suggested_action,
                    required_evidence=["XML3", "XML4"],
                )
            )

        if claim.clinical_notes:
            diagnosis_tokens = self._clinical_diagnosis_tokens(claim)
            diagnosis_aliases = self._clinical_diagnosis_aliases(claim)
            matched_profiles = self._matched_disease_profiles(claim)
            parsed_notes = [
                (note, self._safe_parse_datetime(note.note_time))
                for note in claim.clinical_notes
            ]
            for line in claim.lines:
                if line.line_type not in {"drug", "service"}:
                    continue
                reference_time = self._safe_parse_datetime(line.execution_time or line.ordering_time)
                if reference_time is None:
                    continue
                related_notes = self._related_clinical_notes(claim, parsed_notes, reference_time)
                if not related_notes:
                    hits.append(
                        RuleHit(
                            rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{line.line_id}:timeline",
                            claim_id=claim.header.claim_id,
                            line_id=line.line_id,
                            rule_id=rule.rule_id,
                            severity=rule.severity,
                            legal_basis=rule.legal_basis,
                            message=(
                                f"Dong {line.line_id} ({line.item_name}) chua co dien bien lam sang XML5 "
                                "gan thoi diem phat sinh de doi chieu."
                            ),
                            suggested_action=rule.suggested_action,
                            estimated_amount_impact=line.amount,
                            required_evidence=["XML2/XML3", "XML5"],
                        )
                    )
                    continue
                related_text = self._normalize_match_text("\n".join(note.note_text for note in related_notes))
                if any(
                    self._note_has_diagnosis_context(note.note_text, diagnosis_tokens, diagnosis_aliases)
                    for note in related_notes
                ):
                    disease_line_rule = self._match_disease_line_rule(line, matched_profiles)
                    if disease_line_rule is not None:
                        profile, profile_rule = disease_line_rule
                        if not self._matches_keyword_rule(
                            related_text,
                            profile_rule.required_note_keywords,
                            profile_rule.required_note_match,
                        ):
                            context_label = profile_rule.context_label or profile_rule.rule_id
                            hits.append(
                                RuleHit(
                                    rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{line.line_id}:{profile.profile_id}:{profile_rule.rule_id}",
                                    claim_id=claim.header.claim_id,
                                    line_id=line.line_id,
                                    rule_id=rule.rule_id,
                                    severity=rule.severity,
                                    legal_basis=rule.legal_basis,
                                    message=(
                                        f"Dong {line.line_id} ({line.item_name}) khop profile benh {profile.profile_id} "
                                        f"voi mau {context_label} nhung XML5 chua thay boi canh dieu tri phu hop."
                                    ),
                                    suggested_action=rule.suggested_action,
                                    estimated_amount_impact=line.amount,
                                    required_evidence=["XML2", "XML5"] if line.line_type == "drug" else ["XML3", "XML5"],
                                )
                            )
                        continue
                    department_keywords = self._department_context_keywords_for_line(line, matched_profiles)
                    if department_keywords is not None and not any(
                        keyword in related_text for keyword in department_keywords
                    ):
                        hits.append(
                            RuleHit(
                                rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{line.line_id}:department-context",
                                claim_id=claim.header.claim_id,
                                line_id=line.line_id,
                                rule_id=rule.rule_id,
                                severity=rule.severity,
                                legal_basis=rule.legal_basis,
                                message=(
                                    f"Dong {line.line_id} ({line.item_name}) thuoc khoa {line.department_code} "
                                    "nhung chua thay tu khoa boi canh dieu tri phu hop trong XML5."
                                ),
                                suggested_action=rule.suggested_action,
                                estimated_amount_impact=line.amount,
                                required_evidence=["XML3", "XML5"],
                            )
                        )
                    if line.line_type == "drug":
                        heuristic = self._match_drug_heuristic(line.item_name or "")
                        if heuristic is not None and not any(
                            keyword in related_text for keyword in heuristic["context_keywords"]
                        ):
                            hits.append(
                                RuleHit(
                                    rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{line.line_id}:drug-context",
                                    claim_id=claim.header.claim_id,
                                    line_id=line.line_id,
                                    rule_id=rule.rule_id,
                                    severity=rule.severity,
                                    legal_basis=rule.legal_basis,
                                    message=(
                                        f"Dong {line.line_id} ({line.item_name}) thuoc nhom {heuristic['group']} "
                                        "nhung chua thay tu khoa boi canh dieu tri phu hop trong XML5 gan thoi diem phat sinh."
                                    ),
                                    suggested_action=rule.suggested_action,
                                    estimated_amount_impact=line.amount,
                                    required_evidence=["XML2", "XML5"],
                                )
                            )
                        continue
                    if line.line_type == "service":
                        heuristic = self._match_service_heuristic(line.item_name or "")
                        if heuristic is not None and not any(
                            keyword in related_text for keyword in heuristic["context_keywords"]
                        ):
                            hits.append(
                                RuleHit(
                                    rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{line.line_id}:service-context",
                                    claim_id=claim.header.claim_id,
                                    line_id=line.line_id,
                                    rule_id=rule.rule_id,
                                    severity=rule.severity,
                                    legal_basis=rule.legal_basis,
                                    message=(
                                        f"Dong {line.line_id} ({line.item_name}) thuoc nhom {heuristic['group']} "
                                        "nhung chua thay tu khoa boi canh phu hop trong XML5 gan thoi diem phat sinh."
                                    ),
                                    suggested_action=rule.suggested_action,
                                    estimated_amount_impact=line.amount,
                                    required_evidence=["XML3", "XML5"],
                                )
                            )
                        continue
                    continue
                hits.append(
                    RuleHit(
                        rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{line.line_id}:diagnosis",
                        claim_id=claim.header.claim_id,
                        line_id=line.line_id,
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        legal_basis=rule.legal_basis,
                        message=(
                            f"Dong {line.line_id} ({line.item_name}) chua tim thay dien bien XML5 "
                            "gan thoi diem phat sinh co chuan doan hoac boi canh dieu tri phu hop."
                        ),
                        suggested_action=rule.suggested_action,
                        estimated_amount_impact=line.amount,
                        required_evidence=["XML2/XML3", "XML5"],
                    )
                )

            parsed_note_times = [item for item in parsed_notes if item[1] is not None]
            for result in claim.clinical_results:
                disease_result_rule = self._match_disease_result_rule(result, matched_profiles)
                if disease_result_rule is not None:
                    reference_time = self._safe_parse_datetime(result.result_time)
                    if reference_time is None:
                        continue
                    related_notes = [
                        note
                        for note, note_time in parsed_note_times
                        if note_time <= reference_time and reference_time - note_time <= timedelta(days=1)
                    ]
                    if not related_notes:
                        continue
                    related_text = self._normalize_match_text("\n".join(note.note_text for note in related_notes))
                    profile, profile_rule = disease_result_rule
                    if self._matches_keyword_rule(
                        related_text,
                        profile_rule.required_note_keywords,
                        profile_rule.required_note_match,
                    ):
                        continue
                    context_label = profile_rule.context_label or profile_rule.rule_id
                    hits.append(
                        RuleHit(
                            rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{result.result_id}:{profile.profile_id}:{profile_rule.rule_id}",
                            claim_id=claim.header.claim_id,
                            rule_id=rule.rule_id,
                            severity=rule.severity,
                            legal_basis=rule.legal_basis,
                            message=(
                                f"Ket qua {result.result_id} khop profile benh {profile.profile_id} voi mau {context_label} "
                                "nhung XML5 chua thay boi canh phu hop."
                            ),
                            suggested_action=rule.suggested_action,
                            required_evidence=["XML4", "XML5"],
                        )
                    )
                    continue
                heuristic = self._match_cls_heuristic(result.service_code or "")
                if heuristic is None:
                    continue
                reference_time = self._safe_parse_datetime(result.result_time)
                if reference_time is None:
                    continue
                related_notes = [
                    note
                    for note, note_time in parsed_note_times
                    if note_time <= reference_time and reference_time - note_time <= timedelta(days=1)
                ]
                if not related_notes:
                    continue
                related_text = self._normalize_match_text("\n".join(note.note_text for note in related_notes))
                if any(keyword in related_text for keyword in heuristic["context_keywords"]):
                    continue
                hits.append(
                    RuleHit(
                        rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{result.result_id}:cls-context",
                        claim_id=claim.header.claim_id,
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        legal_basis=rule.legal_basis,
                        message=(
                            f"Ket qua {result.result_id} ma {result.service_code} thuoc nhom {heuristic['group']} "
                            "nhung chua thay tu khoa boi canh phu hop trong XML5 gan thoi diem co ket qua."
                        ),
                        suggested_action=rule.suggested_action,
                        required_evidence=["XML4", "XML5"],
                    )
                )

        return hits

    def _eval_equipment_reference(
        self,
        claim: ParsedClaim,
        rule: RuleDefinition,
        eligibility_result: EligibilityResult | None = None,
        master_snapshot: MasterDataSnapshot | None = None,
    ) -> list[RuleHit]:
        hits: list[RuleHit] = []
        known_equipment_refs = set()
        if master_snapshot is not None:
            known_equipment_refs = {
                item.equipment_id for item in master_snapshot.equipment_items if item.equipment_id
            }
        for line in claim.lines:
            if line.line_type != "service":
                continue
            equipment_heuristic = self._match_equipment_required_heuristic(line.item_name or "")
            if equipment_heuristic is None:
                continue
            equipment_ref = (line.equipment_ref or "").strip()
            if not equipment_ref:
                hits.append(
                    RuleHit(
                        rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{line.line_id}:equipment-missing",
                        claim_id=claim.header.claim_id,
                        line_id=line.line_id,
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        legal_basis=rule.legal_basis,
                        message=(
                            f"Dong {line.line_id} ({line.item_name}) thuoc nhom "
                            f"{equipment_heuristic['group']} nhung chua khai bao MA_MAY."
                        ),
                        suggested_action=rule.suggested_action,
                        estimated_amount_impact=line.amount,
                        required_evidence=["XML3", "FileTrangThietBi.xlsx"],
                    )
                )
                continue
            if known_equipment_refs and equipment_ref not in known_equipment_refs:
                hits.append(
                    RuleHit(
                        rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{line.line_id}:equipment-unknown",
                        claim_id=claim.header.claim_id,
                        line_id=line.line_id,
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        legal_basis=rule.legal_basis,
                        message=(
                            f"Dong {line.line_id} ({line.item_name}) khai bao MA_MAY {equipment_ref} "
                            "nhung chua thay trong danh muc trang thiet bi."
                        ),
                        suggested_action=rule.suggested_action,
                        estimated_amount_impact=line.amount,
                        required_evidence=["XML3", "FileTrangThietBi.xlsx"],
                    )
                )
                continue
            if any(
                equipment_ref.upper().startswith(prefix.upper())
                for prefix in equipment_heuristic["equipment_prefixes"]
            ):
                continue
            hits.append(
                RuleHit(
                    rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{line.line_id}:equipment-group",
                    claim_id=claim.header.claim_id,
                    line_id=line.line_id,
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    legal_basis=rule.legal_basis,
                    message=(
                        f"Dong {line.line_id} ({line.item_name}) thuoc nhom {equipment_heuristic['group']} "
                        f"nhung MA_MAY {equipment_ref} khong dung nhom thiet bi mong doi."
                    ),
                    suggested_action=rule.suggested_action,
                    estimated_amount_impact=line.amount,
                    required_evidence=["XML3", "FileTrangThietBi.xlsx"],
                )
            )
        return hits

    def _eval_duplicate_line(
        self,
        claim: ParsedClaim,
        rule: RuleDefinition,
        eligibility_result: EligibilityResult | None = None,
        master_snapshot: MasterDataSnapshot | None = None,
    ) -> list[RuleHit]:
        hits: list[RuleHit] = []
        service_counts: dict[tuple[str, str], list[object]] = {}
        for line in claim.lines:
            if line.line_type != "service":
                continue
            if (line.item_code or "").startswith("K"):
                continue
            day_key = (line.execution_time or line.ordering_time or "")[:8]
            if not day_key:
                continue
            service_counts.setdefault((line.item_code, day_key), []).append(line)

        for (item_code, day_key), lines in service_counts.items():
            threshold = self._service_duplicate_threshold(item_code)
            if len(lines) <= threshold:
                continue
            for line in lines:
                hits.append(
                    RuleHit(
                        rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{line.line_id}",
                        claim_id=claim.header.claim_id,
                        line_id=line.line_id,
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        legal_basis=rule.legal_basis,
                        message=(
                            f"Dong DVKT {line.line_id} co ma {item_code} lap {len(lines)} lan trong ngay {day_key}, "
                            f"vuot nguong {threshold}."
                        ),
                        suggested_action=rule.suggested_action,
                        estimated_amount_impact=line.amount,
                        required_evidence=["XML3"],
                    )
                )

        cls_counts: dict[tuple[str, str, str, str], list[object]] = {}
        for result in claim.clinical_results:
            day_key = (result.result_time or "")[:8]
            indicator_key = (result.indicator_code or "").strip().lower()
            indicator_name = (result.indicator_name or "").strip().lower()
            if not day_key or not indicator_key:
                continue
            cls_counts.setdefault((result.service_code, indicator_key, indicator_name, day_key), []).append(result)

        for (service_code, indicator_key, indicator_name, day_key), results in cls_counts.items():
            threshold = self._cls_duplicate_threshold(service_code)
            if len(results) <= threshold:
                continue
            for result in results:
                hits.append(
                    RuleHit(
                        rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{result.result_id}",
                        claim_id=claim.header.claim_id,
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        legal_basis=rule.legal_basis,
                        message=(
                            f"Chi so CLS {indicator_key}/{indicator_name} cua ma {service_code} "
                            f"lap {len(results)} lan trong ngay {day_key}, vuot nguong {threshold}."
                        ),
                        suggested_action=rule.suggested_action,
                        required_evidence=["XML4"],
                    )
                )

        return hits

    def _eval_item_code(
        self,
        claim: ParsedClaim,
        rule: RuleDefinition,
        eligibility_result: EligibilityResult | None = None,
        master_snapshot: MasterDataSnapshot | None = None,
    ) -> list[RuleHit]:
        if master_snapshot is None:
            return []

        hits: list[RuleHit] = []
        service_known_codes = {
            service.service_code for service in master_snapshot.all_service_items if service.service_code
        }
        drug_known_codes = {
            drug.drug_code for drug in master_snapshot.all_drug_items if drug.drug_code
        }
        supply_known_codes = {
            supply.supply_code for supply in master_snapshot.all_supply_items if supply.supply_code
        }

        for line in claim.lines:
            if not line.item_code:
                continue
            if line.line_type == "service":
                known_codes = service_known_codes
                item_label = "ma dich vu"
                evidence = ["XML3", "FileDichVuBV.xlsx"]
            elif line.line_type == "drug":
                known_codes = drug_known_codes
                item_label = "ma thuoc"
                evidence = ["XML2", "FileThuoc.xlsx"]
            elif line.line_type == "supply":
                known_codes = supply_known_codes
                item_label = "ma vat tu"
                evidence = ["XML3", "FileVatTuYTe.xlsx"]
            else:
                continue
            if line.item_code in known_codes:
                continue
            hits.append(
                RuleHit(
                    rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{line.line_id}",
                    claim_id=claim.header.claim_id,
                    line_id=line.line_id,
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    legal_basis=rule.legal_basis,
                    message=(
                        f"Dong {line.line_id} co {item_label} {line.item_code} "
                        "chua ton tai trong danh muc."
                    ),
                    suggested_action=rule.suggested_action,
                    estimated_amount_impact=line.amount,
                    required_evidence=evidence,
                )
            )

        for result in claim.clinical_results:
            if not result.service_code or result.service_code in service_known_codes:
                continue
            hits.append(
                RuleHit(
                    rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{result.result_id}",
                    claim_id=claim.header.claim_id,
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    legal_basis=rule.legal_basis,
                    message=(
                        f"Ket qua {result.result_id} co ma dich vu {result.service_code} "
                        "chua ton tai trong danh muc dich vu."
                    ),
                    suggested_action=rule.suggested_action,
                    required_evidence=["XML4", "FileDichVuBV.xlsx"],
                )
            )

        return hits

    def _eval_item_effective(
        self,
        claim: ParsedClaim,
        rule: RuleDefinition,
        eligibility_result: EligibilityResult | None = None,
        master_snapshot: MasterDataSnapshot | None = None,
    ) -> list[RuleHit]:
        if master_snapshot is None:
            return []

        service_active_codes = {
            service.service_code for service in master_snapshot.service_items if service.service_code
        }
        service_known_codes = {
            service.service_code for service in master_snapshot.all_service_items if service.service_code
        }
        drug_active_codes = {
            drug.drug_code for drug in master_snapshot.drug_items if drug.drug_code
        }
        drug_known_codes = {
            drug.drug_code for drug in master_snapshot.all_drug_items if drug.drug_code
        }
        supply_active_codes = {
            supply.supply_code for supply in master_snapshot.supply_items if supply.supply_code
        }
        supply_known_codes = {
            supply.supply_code for supply in master_snapshot.all_supply_items if supply.supply_code
        }
        hits: list[RuleHit] = []

        for line in claim.lines:
            if not line.item_code:
                continue
            if line.line_type == "service":
                active_codes = service_active_codes
                known_codes = service_known_codes
                item_label = "ma dich vu"
                evidence = ["XML3", "FileDichVuBV.xlsx"]
            elif line.line_type == "drug":
                active_codes = drug_active_codes
                known_codes = drug_known_codes
                item_label = "ma thuoc"
                evidence = ["XML2", "FileThuoc.xlsx"]
            elif line.line_type == "supply":
                active_codes = supply_active_codes
                known_codes = supply_known_codes
                item_label = "ma vat tu"
                evidence = ["XML3", "FileVatTuYTe.xlsx"]
            else:
                continue
            if line.item_code in active_codes or line.item_code not in known_codes:
                continue
            hits.append(
                RuleHit(
                    rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{line.line_id}",
                    claim_id=claim.header.claim_id,
                    line_id=line.line_id,
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    legal_basis=rule.legal_basis,
                    message=(
                        f"Dong {line.line_id} co {item_label} {line.item_code} ton tai trong danh muc "
                        "nhung khong con hieu luc tai ngay ap dung."
                    ),
                    suggested_action=rule.suggested_action,
                    estimated_amount_impact=line.amount,
                    required_evidence=evidence,
                )
            )

        for result in claim.clinical_results:
            if (
                not result.service_code
                or result.service_code in service_active_codes
                or result.service_code not in service_known_codes
            ):
                continue
            hits.append(
                RuleHit(
                    rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{result.result_id}",
                    claim_id=claim.header.claim_id,
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    legal_basis=rule.legal_basis,
                    message=(
                        f"Ket qua {result.result_id} co ma dich vu {result.service_code} ton tai trong danh muc "
                        "nhung khong con hieu luc tai ngay ap dung."
                    ),
                    suggested_action=rule.suggested_action,
                    required_evidence=["XML4", "FileDichVuBV.xlsx"],
                )
            )

        return hits

    def _eval_included_in_price(
        self,
        claim: ParsedClaim,
        rule: RuleDefinition,
        eligibility_result: EligibilityResult | None = None,
        master_snapshot: MasterDataSnapshot | None = None,
    ) -> list[RuleHit]:
        hits: list[RuleHit] = []

        for line in claim.lines:
            line_type = (line.line_type or "").strip().lower()
            if line_type not in {"service", "drug", "supply"}:
                continue
            item_code = (line.item_code or "").strip()
            item_name = self._normalize_match_text(line.item_name)
            configured_codes = self._payment_policy.included_in_price_codes.get(line_type, ())
            configured_keywords = self._payment_policy.included_in_price_keywords.get(line_type, ())
            if item_code not in configured_codes and not any(
                self._normalize_match_text(keyword) in item_name for keyword in configured_keywords
            ):
                continue
            hits.append(
                RuleHit(
                    rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{line.line_id}",
                    claim_id=claim.header.claim_id,
                    line_id=line.line_id,
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    legal_basis=rule.legal_basis,
                    message=(
                        f"Dong {line.line_id} ({line.item_name}) nam trong danh sach khoan "
                        "duoc cau hinh la da ket cau trong gia, khong nen thanh toan rieng."
                    ),
                    suggested_action=rule.suggested_action,
                    estimated_amount_impact=line.amount,
                    required_evidence=["payment_policy", line.source_xml or "claim_line"],
                )
            )

        return hits

    def _eval_route(
        self,
        claim: ParsedClaim,
        rule: RuleDefinition,
        eligibility_result: EligibilityResult | None = None,
        master_snapshot: MasterDataSnapshot | None = None,
    ) -> list[RuleHit]:
        if eligibility_result is None or eligibility_result.route_eligible:
            return []

        return [
            RuleHit(
                rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}",
                claim_id=claim.header.claim_id,
                rule_id=rule.rule_id,
                severity=rule.severity,
                legal_basis=rule.legal_basis,
                message=(
                    f"Ma tuyen {claim.header.route_code} khong hop le theo eligibility policy dang ap dung."
                ),
                suggested_action=rule.suggested_action,
                estimated_amount_impact=claim.header.insurance_amount,
            )
        ]

    def _eval_practitioner_exists(
        self,
        claim: ParsedClaim,
        rule: RuleDefinition,
        eligibility_result: EligibilityResult | None = None,
        master_snapshot: MasterDataSnapshot | None = None,
    ) -> list[RuleHit]:
        if master_snapshot is None:
            return []

        known_practitioners = {
            staff.practitioner_id for staff in master_snapshot.staff_members if staff.practitioner_id
        }
        hits: list[RuleHit] = []

        for line in claim.lines:
            practitioner_id = (line.practitioner_id or "").strip()
            if not practitioner_id or practitioner_id in known_practitioners:
                continue
            hits.append(
                RuleHit(
                    rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{line.line_id}",
                    claim_id=claim.header.claim_id,
                    line_id=line.line_id,
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    legal_basis=rule.legal_basis,
                    message=(
                        f"Dong {line.line_id} co practitioner_id {practitioner_id} "
                        "khong ton tai trong danh muc nhan luc."
                    ),
                    suggested_action=rule.suggested_action,
                    estimated_amount_impact=line.amount,
                )
            )

        return hits

    def _eval_practitioner_department(
        self,
        claim: ParsedClaim,
        rule: RuleDefinition,
        eligibility_result: EligibilityResult | None = None,
        master_snapshot: MasterDataSnapshot | None = None,
    ) -> list[RuleHit]:
        if master_snapshot is None:
            return []

        staff_by_id = {
            staff.practitioner_id: staff for staff in master_snapshot.staff_members if staff.practitioner_id
        }
        hits: list[RuleHit] = []

        for line in claim.lines:
            practitioner_id = (line.practitioner_id or "").strip()
            department_code = (line.department_code or "").strip()
            if not practitioner_id or not department_code:
                continue
            staff = staff_by_id.get(practitioner_id)
            if staff is None or not staff.department_code:
                continue
            if staff.department_code == department_code:
                continue
            hits.append(
                RuleHit(
                    rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{line.line_id}",
                    claim_id=claim.header.claim_id,
                    line_id=line.line_id,
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    legal_basis=rule.legal_basis,
                    message=(
                        f"Dong {line.line_id} thuoc khoa {department_code} "
                        f"nhung practitioner_id {practitioner_id} dang khai bao khoa {staff.department_code}."
                    ),
                    suggested_action=rule.suggested_action,
                    estimated_amount_impact=line.amount,
                )
            )

        return hits

    def _eval_practitioner_scope(
        self,
        claim: ParsedClaim,
        rule: RuleDefinition,
        eligibility_result: EligibilityResult | None = None,
        master_snapshot: MasterDataSnapshot | None = None,
    ) -> list[RuleHit]:
        if master_snapshot is None:
            return []

        staff_by_id = {
            staff.practitioner_id: staff for staff in master_snapshot.staff_members if staff.practitioner_id
        }
        known_service_codes = {
            service.service_code for service in master_snapshot.service_items if service.service_code
        }
        hits: list[RuleHit] = []

        for line in claim.lines:
            practitioner_id = (line.practitioner_id or "").strip()
            if not practitioner_id:
                continue
            staff = staff_by_id.get(practitioner_id)
            if staff is None:
                continue
            if line.item_code not in known_service_codes:
                continue
            if line.item_code in staff.extra_service_codes:
                continue
            if (staff.practice_scope or "").strip():
                continue
            hits.append(
                RuleHit(
                    rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{line.line_id}",
                    claim_id=claim.header.claim_id,
                    line_id=line.line_id,
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    legal_basis=rule.legal_basis,
                    message=(
                        f"Dong {line.line_id} co dich vu {line.item_code} chua thay trong "
                        f"DVKT_KHAC va practitioner_id {practitioner_id} cung khong co PHAMVI_CM."
                    ),
                    suggested_action=rule.suggested_action,
                    estimated_amount_impact=line.amount,
                )
            )

        return hits

    def _is_effective_on(self, target_date: str, effective_from: str | None, effective_to: str | None) -> bool:
        if effective_from and target_date < effective_from:
            return False
        if effective_to and target_date > effective_to:
            return False
        return True

    def _payment_rule_config(self, rule_id: str, target_date: str) -> PaymentRuleConfig | None:
        payment_rule = self._payment_rules.rules.get(rule_id)
        if payment_rule is None or not payment_rule.enabled:
            return None
        if not self._is_effective_on(target_date, payment_rule.effective_from, payment_rule.effective_to):
            return None
        return payment_rule

    def _payment_group_matches(self, line_code: str, item_name: str, entry: PaymentRuleEntry) -> bool:
        group_value = self._normalize_match_text(entry.group_code or entry.match_value)
        if not group_value:
            return False
        normalized_code = (line_code or "").strip().upper()
        return normalized_code.startswith(group_value.upper()) or group_value in item_name

    def _payment_entry_matches(
        self,
        line,
        entry: PaymentRuleEntry,
        target_date: str,
    ) -> bool:
        if (line.line_type or "").strip().lower() != entry.item_type:
            return False
        if not self._is_effective_on(target_date, entry.effective_from, entry.effective_to):
            return False
        item_code = (line.item_code or "").strip()
        item_name = self._normalize_match_text(line.item_name)
        if entry.match_type == "code":
            return bool(item_code) and item_code == entry.match_value
        if entry.match_type == "keyword":
            keyword = self._normalize_match_text(entry.keyword or entry.match_value)
            return bool(keyword) and keyword in item_name
        if entry.match_type == "group":
            return self._payment_group_matches(item_code, item_name, entry)
        return False

    def _find_payment_entry(
        self,
        payment_rule: PaymentRuleConfig,
        line,
        target_date: str,
    ) -> PaymentRuleEntry | None:
        for match_type in self._payment_rules.match_priority:
            for entry in payment_rule.matchers:
                if entry.match_type != match_type:
                    continue
                if self._payment_entry_matches(line, entry, target_date):
                    return entry
        return None

    def _payment_legal_basis(self, payment_rule: PaymentRuleConfig, entry: PaymentRuleEntry | None) -> str:
        if entry is not None and entry.legal_basis:
            return "; ".join(entry.legal_basis)
        return "; ".join(payment_rule.legal_basis)

    def _payment_evidence(self, line) -> list[str]:
        return [line.source_xml or "claim_line", self._payment_rules.source_ref]

    def _normalize_coverage_percent(self, raw_value: Decimal | None) -> Decimal | None:
        if raw_value is None:
            return None
        if raw_value > Decimal("1"):
            return raw_value / Decimal("100")
        return raw_value

    def _eval_pay_out_of_scope(
        self,
        claim: ParsedClaim,
        rule: RuleDefinition,
        eligibility_result: EligibilityResult | None = None,
        master_snapshot: MasterDataSnapshot | None = None,
    ) -> list[RuleHit]:
        payment_rule = self._payment_rule_config(rule.rule_id, self._current_target_date or claim.header.claim_effective_date)
        if payment_rule is None:
            return []

        hits: list[RuleHit] = []
        for line in claim.lines:
            entry = self._find_payment_entry(payment_rule, line, self._current_target_date or claim.header.claim_effective_date)
            if entry is None:
                continue
            match_value = entry.keyword or entry.group_code or entry.match_value
            hits.append(
                RuleHit(
                    rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{line.line_id}",
                    claim_id=claim.header.claim_id,
                    line_id=line.line_id,
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    legal_basis=self._payment_legal_basis(payment_rule, entry) or rule.legal_basis,
                    message=(
                        f"Dong {line.line_id} ({line.item_name}) nam ngoai pham vi thanh toan BHYT "
                        f"theo match {entry.match_type}={match_value}."
                    ),
                    suggested_action=rule.suggested_action,
                    estimated_amount_impact=line.amount,
                    required_evidence=self._payment_evidence(line),
                )
            )
        return hits

    def _payment_limit_impact(self, line, payment_rule: PaymentRuleConfig, entry: PaymentRuleEntry) -> Decimal:
        if payment_rule.rule_kind == "coverage_percent":
            coverage_percent = self._normalize_coverage_percent(entry.coverage_percent)
            if coverage_percent is None:
                return Decimal("0")
            return max(Decimal("0"), line.amount * (Decimal("1") - coverage_percent))
        if payment_rule.rule_kind == "unit_price_max":
            if entry.unit_price_max is None:
                return Decimal("0")
            return max(Decimal("0"), (line.unit_price - entry.unit_price_max) * line.quantity)
        if payment_rule.rule_kind == "quantity_max":
            if entry.quantity_max is None:
                return Decimal("0")
            return max(Decimal("0"), (line.quantity - entry.quantity_max) * line.unit_price)
        if payment_rule.rule_kind == "amount_max":
            if entry.amount_max is None:
                return Decimal("0")
            return max(Decimal("0"), line.amount - entry.amount_max)
        return Decimal("0")

    def _payment_limit_message(self, line, payment_rule: PaymentRuleConfig, entry: PaymentRuleEntry) -> str:
        if payment_rule.rule_kind == "coverage_percent":
            coverage_percent = self._normalize_coverage_percent(entry.coverage_percent)
            return (
                f"Dong {line.line_id} ({line.item_name}) vuot ty le thanh toan cho phep "
                f"{coverage_percent}."
            )
        if payment_rule.rule_kind == "unit_price_max":
            return (
                f"Dong {line.line_id} ({line.item_name}) co don gia {line.unit_price} "
                f"vuot muc toi da {entry.unit_price_max}."
            )
        if payment_rule.rule_kind == "quantity_max":
            return (
                f"Dong {line.line_id} ({line.item_name}) co so luong {line.quantity} "
                f"vuot muc toi da {entry.quantity_max}."
            )
        return (
            f"Dong {line.line_id} ({line.item_name}) co thanh tien {line.amount} "
            f"vuot muc toi da {entry.amount_max}."
        )

    def _eval_pay_limit(
        self,
        claim: ParsedClaim,
        rule: RuleDefinition,
        eligibility_result: EligibilityResult | None = None,
        master_snapshot: MasterDataSnapshot | None = None,
    ) -> list[RuleHit]:
        payment_rule = self._payment_rule_config(rule.rule_id, self._current_target_date or claim.header.claim_effective_date)
        if payment_rule is None:
            return []

        hits: list[RuleHit] = []
        for line in claim.lines:
            entry = self._find_payment_entry(payment_rule, line, self._current_target_date or claim.header.claim_effective_date)
            if entry is None:
                continue
            impact = self._payment_limit_impact(line, payment_rule, entry)
            if impact <= Decimal("0"):
                continue
            hits.append(
                RuleHit(
                    rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{line.line_id}",
                    claim_id=claim.header.claim_id,
                    line_id=line.line_id,
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    legal_basis=self._payment_legal_basis(payment_rule, entry) or rule.legal_basis,
                    message=self._payment_limit_message(line, payment_rule, entry),
                    suggested_action=rule.suggested_action,
                    estimated_amount_impact=impact,
                    required_evidence=self._payment_evidence(line),
                )
            )
        return hits

    def _note_has_diagnosis_context(
        self,
        note_text: str,
        diagnosis_tokens: set[str],
        diagnosis_aliases: set[str],
    ) -> bool:
        normalized = self._normalize_match_text(note_text)
        if "chan doan" in normalized:
            return True
        return any(token in normalized for token in diagnosis_tokens | diagnosis_aliases)

    def _match_drug_heuristic(self, item_name: str) -> dict[str, tuple[str, ...]] | None:
        normalized = self._normalize_match_text(item_name)
        for heuristic in self._clinical_policy.drug_context_heuristics:
            if any(keyword in normalized for keyword in heuristic["drug_keywords"]):
                return heuristic
        return None

    def _match_service_heuristic(self, item_name: str) -> dict[str, tuple[str, ...]] | None:
        normalized = self._normalize_match_text(item_name)
        for heuristic in self._clinical_policy.service_context_heuristics:
            if any(keyword in normalized for keyword in heuristic["service_keywords"]):
                return heuristic
        return None

    def _match_equipment_required_heuristic(self, item_name: str) -> dict[str, tuple[str, ...]] | None:
        normalized = self._normalize_match_text(item_name)
        for heuristic in self._clinical_policy.equipment_required_service_heuristics:
            if any(keyword in normalized for keyword in heuristic["service_keywords"]):
                return heuristic
        return None

    def _eval_item_code(
        self,
        claim: ParsedClaim,
        rule: RuleDefinition,
        eligibility_result: EligibilityResult | None = None,
        master_snapshot: MasterDataSnapshot | None = None,
    ) -> list[RuleHit]:
        if master_snapshot is None:
            return []

        hits: list[RuleHit] = []
        service_known_codes = {
            service.service_code for service in master_snapshot.all_service_items if service.service_code
        }
        drug_known_codes = {
            drug.drug_code for drug in master_snapshot.all_drug_items if drug.drug_code
        }
        supply_known_codes = {
            supply.supply_code for supply in master_snapshot.all_supply_items if supply.supply_code
        }

        for line in claim.lines:
            if not line.item_code:
                continue
            if line.line_type == "service":
                known_codes = service_known_codes
                catalog_loaded = bool(master_snapshot.service_items or master_snapshot.all_service_items)
                item_label = "ma dich vu"
                evidence = ["XML3", "FileDichVuBV.xlsx"]
            elif line.line_type == "drug":
                known_codes = drug_known_codes
                catalog_loaded = bool(master_snapshot.drug_items or master_snapshot.all_drug_items)
                item_label = "ma thuoc"
                evidence = ["XML2", "FileThuoc.xlsx"]
            elif line.line_type == "supply":
                known_codes = supply_known_codes
                catalog_loaded = bool(master_snapshot.supply_items or master_snapshot.all_supply_items)
                item_label = "ma vat tu"
                evidence = ["XML3", "FileVatTuYTe.xlsx"]
            else:
                continue
            if not catalog_loaded or line.item_code in known_codes:
                continue
            hits.append(
                RuleHit(
                    rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{line.line_id}",
                    claim_id=claim.header.claim_id,
                    line_id=line.line_id,
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    legal_basis=rule.legal_basis,
                    message=(
                        f"Dong {line.line_id} co {item_label} {line.item_code} "
                        "chua ton tai trong danh muc."
                    ),
                    suggested_action=rule.suggested_action,
                    estimated_amount_impact=line.amount,
                    required_evidence=evidence,
                )
            )

        if not (master_snapshot.service_items or master_snapshot.all_service_items):
            return hits

        for result in claim.clinical_results:
            if not result.service_code or result.service_code in service_known_codes:
                continue
            hits.append(
                RuleHit(
                    rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{result.result_id}",
                    claim_id=claim.header.claim_id,
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    legal_basis=rule.legal_basis,
                    message=(
                        f"Ket qua {result.result_id} co ma dich vu {result.service_code} "
                        "chua ton tai trong danh muc dich vu."
                    ),
                    suggested_action=rule.suggested_action,
                    required_evidence=["XML4", "FileDichVuBV.xlsx"],
                )
            )

        return hits

    def _eval_item_effective(
        self,
        claim: ParsedClaim,
        rule: RuleDefinition,
        eligibility_result: EligibilityResult | None = None,
        master_snapshot: MasterDataSnapshot | None = None,
    ) -> list[RuleHit]:
        if master_snapshot is None:
            return []

        service_active_codes = {
            service.service_code for service in master_snapshot.service_items if service.service_code
        }
        service_known_codes = {
            service.service_code for service in master_snapshot.all_service_items if service.service_code
        }
        drug_active_codes = {
            drug.drug_code for drug in master_snapshot.drug_items if drug.drug_code
        }
        drug_known_codes = {
            drug.drug_code for drug in master_snapshot.all_drug_items if drug.drug_code
        }
        supply_active_codes = {
            supply.supply_code for supply in master_snapshot.supply_items if supply.supply_code
        }
        supply_known_codes = {
            supply.supply_code for supply in master_snapshot.all_supply_items if supply.supply_code
        }
        hits: list[RuleHit] = []

        for line in claim.lines:
            if not line.item_code:
                continue
            if line.line_type == "service":
                active_codes = service_active_codes
                known_codes = service_known_codes
                catalog_loaded = bool(master_snapshot.service_items or master_snapshot.all_service_items)
                item_label = "ma dich vu"
                evidence = ["XML3", "FileDichVuBV.xlsx"]
            elif line.line_type == "drug":
                active_codes = drug_active_codes
                known_codes = drug_known_codes
                catalog_loaded = bool(master_snapshot.drug_items or master_snapshot.all_drug_items)
                item_label = "ma thuoc"
                evidence = ["XML2", "FileThuoc.xlsx"]
            elif line.line_type == "supply":
                active_codes = supply_active_codes
                known_codes = supply_known_codes
                catalog_loaded = bool(master_snapshot.supply_items or master_snapshot.all_supply_items)
                item_label = "ma vat tu"
                evidence = ["XML3", "FileVatTuYTe.xlsx"]
            else:
                continue
            if not catalog_loaded or line.item_code in active_codes or line.item_code not in known_codes:
                continue
            hits.append(
                RuleHit(
                    rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{line.line_id}",
                    claim_id=claim.header.claim_id,
                    line_id=line.line_id,
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    legal_basis=rule.legal_basis,
                    message=(
                        f"Dong {line.line_id} co {item_label} {line.item_code} ton tai trong danh muc "
                        "nhung khong con hieu luc tai ngay ap dung."
                    ),
                    suggested_action=rule.suggested_action,
                    estimated_amount_impact=line.amount,
                    required_evidence=evidence,
                )
            )

        if not (master_snapshot.service_items or master_snapshot.all_service_items):
            return hits

        for result in claim.clinical_results:
            if (
                not result.service_code
                or result.service_code in service_active_codes
                or result.service_code not in service_known_codes
            ):
                continue
            hits.append(
                RuleHit(
                    rule_hit_id=f"{claim.header.claim_id}:{rule.rule_id}:{result.result_id}",
                    claim_id=claim.header.claim_id,
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    legal_basis=rule.legal_basis,
                    message=(
                        f"Ket qua {result.result_id} co ma dich vu {result.service_code} ton tai trong danh muc "
                        "nhung khong con hieu luc tai ngay ap dung."
                    ),
                    suggested_action=rule.suggested_action,
                    required_evidence=["XML4", "FileDichVuBV.xlsx"],
                )
            )

        return hits
