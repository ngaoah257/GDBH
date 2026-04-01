from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from case_triage import CaseTriageService
from claim_models import EngineResult, ParsedClaim, RetrievalResult, TriageResult, XML5NoteRecord
from deterministic_rule_engine import DeterministicRuleEngine
from diagnosis_validator import DiagnosisValidationResult, DiagnosisValidatorService
from evidence_service import EvidenceRetrievalService
from eligibility_service import EligibilityService
from master_data_service import MasterDataService
from parser_normalizer import ParserNormalizerService, XML5KnowledgeBaseBuilder
from rule_registry import RuleRegistry


@dataclass(slots=True)
class RuleEditorRecord:
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

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "RuleEditorRecord":
        return cls(
            rule_id=str(payload["rule_id"]),
            rule_name=str(payload["rule_name"]),
            rule_group=str(payload["rule_group"]),
            severity=str(payload["severity"]),
            legal_basis=str(payload["legal_basis"]),
            effective_from=str(payload["effective_from"]),
            effective_to=str(payload["effective_to"]) if payload.get("effective_to") else None,
            input_scope=str(payload["input_scope"]),
            decision_logic=str(payload["decision_logic"]),
            suggested_action=str(payload["suggested_action"]),
            owner=str(payload["owner"]),
            enabled=bool(payload.get("enabled", True)),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "rule_group": self.rule_group,
            "severity": self.severity,
            "legal_basis": self.legal_basis,
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
            "input_scope": self.input_scope,
            "decision_logic": self.decision_logic,
            "suggested_action": self.suggested_action,
            "owner": self.owner,
            "enabled": self.enabled,
        }


@dataclass(slots=True)
class PreviewRunResult:
    xml_file: Path
    effective_date: str
    claim: ParsedClaim
    engine_result: EngineResult
    triage_result: TriageResult
    effective_rule_count: int
    guideline_draft_count: int = 0
    diagnosis_validation_results: list[DiagnosisValidationResult] | None = None


@dataclass(slots=True)
class XML5RetrievalPreviewResult:
    xml_file: Path
    effective_date: str
    note_records: list[XML5NoteRecord]
    retrieval_results: list[RetrievalResult]


@dataclass(slots=True)
class PaymentPolicyRecord:
    source_ref: str
    included_in_price_codes: dict[str, list[str]]
    included_in_price_keywords: dict[str, list[str]]

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "PaymentPolicyRecord":
        code_payload = payload.get("included_in_price_codes", {})
        keyword_payload = payload.get("included_in_price_keywords", {})
        return cls(
            source_ref=str(payload.get("source_ref", "payment-policy@0.1.0")),
            included_in_price_codes={
                key: [str(item) for item in value]
                for key, value in dict(code_payload).items()
            },
            included_in_price_keywords={
                key: [str(item) for item in value]
                for key, value in dict(keyword_payload).items()
            },
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "source_ref": self.source_ref,
            "included_in_price_codes": self.included_in_price_codes,
            "included_in_price_keywords": self.included_in_price_keywords,
        }


@dataclass(slots=True)
class ClinicalPolicyRecord:
    source_ref: str
    payload: dict[str, object]

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ClinicalPolicyRecord":
        return cls(
            source_ref=str(payload.get("source_ref", "clinical-policy@0.1.0")),
            payload=dict(payload),
        )

    def to_dict(self) -> dict[str, object]:
        merged = dict(self.payload)
        merged["source_ref"] = self.source_ref
        return merged


@dataclass(slots=True)
class DiseaseLineDraftRecord:
    line_rule_id: str
    line_types: list[str]
    line_item_codes: list[str]
    line_item_code_prefixes: list[str]
    line_item_name_keywords: list[str]
    line_department_codes: list[str]
    line_required_note_keywords: list[str]
    line_required_note_match: str
    line_context_label: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.line_rule_id,
            "line_types": self.line_types,
            "item_codes": self.line_item_codes,
            "item_code_prefixes": self.line_item_code_prefixes,
            "item_name_keywords": self.line_item_name_keywords,
            "department_codes": self.line_department_codes,
            "required_note_keywords": self.line_required_note_keywords,
            "required_note_match": self.line_required_note_match,
            "context_label": self.line_context_label,
        }


@dataclass(slots=True)
class DiseaseResultDraftRecord:
    result_rule_id: str
    result_service_codes: list[str]
    result_indicator_keywords: list[str]
    result_required_note_keywords: list[str]
    result_required_note_match: str = "any"
    result_context_label: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.result_rule_id,
            "service_codes": self.result_service_codes,
            "indicator_keywords": self.result_indicator_keywords,
            "required_note_keywords": self.result_required_note_keywords,
            "required_note_match": self.result_required_note_match,
            "context_label": self.result_context_label,
        }


@dataclass(slots=True)
class DiseaseProfileDraftRecord:
    profile_id: str
    diagnosis_code_prefixes: list[str]
    diagnosis_aliases: list[str]
    department_codes: list[str]
    department_context_keywords: list[str]
    line_rules: list[DiseaseLineDraftRecord]
    result_rules: list[DiseaseResultDraftRecord]

    def to_dict(self) -> dict[str, object]:
        department_context_keywords = {
            department_code: list(self.department_context_keywords)
            for department_code in self.department_codes
            if department_code
        }
        return {
            "profile_id": self.profile_id,
            "diagnosis_code_prefixes": self.diagnosis_code_prefixes,
            "diagnosis_aliases": self.diagnosis_aliases,
            "department_context_keywords": department_context_keywords,
            "line_rules": [item.to_dict() for item in self.line_rules],
            "result_rules": [item.to_dict() for item in self.result_rules],
        }


class ReviewerWorkspaceService:
    def __init__(
        self,
        rule_file: str | Path,
        catalog_dir: str | Path | None = None,
        eligibility_policy_file: str | Path | None = None,
        payment_policy_file: str | Path | None = None,
        clinical_policy_file: str | Path | None = None,
        kb_chunks_file: str | Path | None = None,
        guideline_rule_drafts_file: str | Path | None = None,
        internal_code_policy_file: str | Path | None = None,
        diagnosis_profiles_file: str | Path | None = None,
    ):
        self._rule_file = Path(rule_file)
        self._catalog_dir = Path(catalog_dir) if catalog_dir is not None else None
        self._eligibility_policy_file = (
            Path(eligibility_policy_file) if eligibility_policy_file is not None else None
        )
        self._payment_policy_file = (
            Path(payment_policy_file) if payment_policy_file is not None else None
        )
        self._clinical_policy_file = (
            Path(clinical_policy_file) if clinical_policy_file is not None else None
        )
        self._kb_chunks_file = Path(kb_chunks_file) if kb_chunks_file is not None else None
        self._guideline_rule_drafts_file = (
            Path(guideline_rule_drafts_file) if guideline_rule_drafts_file is not None else None
        )
        self._internal_code_policy_file = (
            Path(internal_code_policy_file) if internal_code_policy_file is not None else None
        )
        self._diagnosis_profiles_file = (
            Path(diagnosis_profiles_file) if diagnosis_profiles_file is not None else None
        )

    @property
    def rule_file(self) -> Path:
        return self._rule_file

    @property
    def catalog_dir(self) -> Path | None:
        return self._catalog_dir

    @property
    def eligibility_policy_file(self) -> Path | None:
        return self._eligibility_policy_file

    @property
    def payment_policy_file(self) -> Path | None:
        return self._payment_policy_file

    @property
    def clinical_policy_file(self) -> Path | None:
        return self._clinical_policy_file

    @property
    def kb_chunks_file(self) -> Path | None:
        return self._kb_chunks_file

    @property
    def guideline_rule_drafts_file(self) -> Path | None:
        return self._guideline_rule_drafts_file

    @property
    def internal_code_policy_file(self) -> Path | None:
        return self._internal_code_policy_file

    @property
    def diagnosis_profiles_file(self) -> Path | None:
        return self._diagnosis_profiles_file

    def guideline_draft_count(self) -> int:
        target_file = self._guideline_rule_drafts_file
        if target_file is None or not target_file.exists():
            return 0
        return sum(1 for line in target_file.read_text(encoding="utf-8").splitlines() if line.strip())

    def list_rules(self) -> list[RuleEditorRecord]:
        raw = json.loads(self._rule_file.read_text(encoding="utf-8"))
        return [RuleEditorRecord.from_dict(item) for item in raw]

    def save_rules(self, rules: list[RuleEditorRecord]) -> None:
        payload = [rule.to_dict() for rule in rules]
        self._rule_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def update_rule(self, updated_rule: RuleEditorRecord) -> None:
        rules = self.list_rules()
        replaced = False
        for index, rule in enumerate(rules):
            if rule.rule_id != updated_rule.rule_id:
                continue
            rules[index] = updated_rule
            replaced = True
            break
        if not replaced:
            rules.append(updated_rule)
        self.save_rules(rules)

    def get_payment_policy(self) -> PaymentPolicyRecord:
        if self._payment_policy_file is None:
            raise ValueError("payment_policy_file is not configured.")
        if not self._payment_policy_file.exists():
            return PaymentPolicyRecord(
                source_ref="payment-policy@0.1.0",
                included_in_price_codes={"service": [], "drug": [], "supply": []},
                included_in_price_keywords={"service": [], "drug": [], "supply": []},
            )
        payload = json.loads(self._payment_policy_file.read_text(encoding="utf-8"))
        return PaymentPolicyRecord.from_dict(payload)

    def save_payment_policy(self, payment_policy: PaymentPolicyRecord) -> None:
        if self._payment_policy_file is None:
            raise ValueError("payment_policy_file is not configured.")
        self._payment_policy_file.write_text(
            json.dumps(payment_policy.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def get_clinical_policy(self) -> ClinicalPolicyRecord:
        if self._clinical_policy_file is None:
            raise ValueError("clinical_policy_file is not configured.")
        if not self._clinical_policy_file.exists():
            return ClinicalPolicyRecord(
                source_ref="clinical-policy@0.1.0",
                payload={"source_ref": "clinical-policy@0.1.0"},
            )
        payload = json.loads(self._clinical_policy_file.read_text(encoding="utf-8"))
        return ClinicalPolicyRecord.from_dict(payload)

    def save_clinical_policy(self, clinical_policy: ClinicalPolicyRecord) -> None:
        if self._clinical_policy_file is None:
            raise ValueError("clinical_policy_file is not configured.")
        self._clinical_policy_file.write_text(
            json.dumps(clinical_policy.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def append_disease_profile(self, profile: DiseaseProfileDraftRecord) -> ClinicalPolicyRecord:
        clinical_policy = self.get_clinical_policy()
        payload = dict(clinical_policy.to_dict())
        raw_profiles = list(payload.get("disease_profiles", []))
        raw_profiles = [
            item
            for item in raw_profiles
            if str(dict(item).get("profile_id", "")).strip() != profile.profile_id
        ]
        raw_profiles.append(profile.to_dict())
        payload["disease_profiles"] = raw_profiles
        updated = ClinicalPolicyRecord(
            source_ref=clinical_policy.source_ref,
            payload=payload,
        )
        self.save_clinical_policy(updated)
        return updated

    def run_preview(self, xml_file: str | Path, effective_date: str) -> PreviewRunResult:
        if self._catalog_dir is None:
            raise ValueError("catalog_dir is required to run preview.")
        if self._eligibility_policy_file is None:
            raise ValueError("eligibility_policy_file is required to run preview.")

        xml_path = Path(xml_file).resolve()
        claim = ParserNormalizerService().parse_file(xml_path)
        master_snapshot = MasterDataService(self._catalog_dir).load_snapshot(
            effective_date,
            facility_id=claim.header.facility_id,
        )
        eligibility = EligibilityService.from_json_file(self._eligibility_policy_file).evaluate(
            claim.header
        )
        registry = RuleRegistry.from_json_file(self._rule_file)
        engine_result = DeterministicRuleEngine(
            registry,
            payment_policy_file=self._payment_policy_file,
            clinical_policy_file=self._clinical_policy_file,
            guideline_rule_drafts_file=self._guideline_rule_drafts_file,
            internal_code_policy_file=self._internal_code_policy_file,
        ).evaluate(
            claim,
            effective_date,
            eligibility,
            master_snapshot,
        )
        diagnosis_validation_results: list[DiagnosisValidationResult] = []
        if self._diagnosis_profiles_file is not None and self._diagnosis_profiles_file.exists():
            diagnosis_service = DiagnosisValidatorService()
            case_record = diagnosis_service.build_case_record(claim)
            profiles = diagnosis_service.load_profiles(self._diagnosis_profiles_file)
            diagnosis_validation_results = diagnosis_service.validate_case_records([case_record], profiles)
        triage_result = CaseTriageService().triage(engine_result)
        return PreviewRunResult(
            xml_file=xml_path,
            effective_date=effective_date,
            claim=claim,
            engine_result=engine_result,
            triage_result=triage_result,
            effective_rule_count=len(registry.list_effective_rules(effective_date)),
            guideline_draft_count=self.guideline_draft_count(),
            diagnosis_validation_results=diagnosis_validation_results,
        )

    def run_xml5_retrieval_preview(
        self,
        xml_file: str | Path,
        effective_date: str,
    ) -> XML5RetrievalPreviewResult:
        if self._kb_chunks_file is None or not self._kb_chunks_file.exists():
            raise ValueError("kb_chunks_file is not configured or does not exist.")

        xml_path = Path(xml_file).resolve()
        note_records = ParserNormalizerService().build_xml5_note_records_from_file(xml_path)
        builder = XML5KnowledgeBaseBuilder()
        queries = builder.build_queries(note_records)
        retriever = EvidenceRetrievalService()
        chunks = retriever.load_jsonl(self._kb_chunks_file)
        retrieval_results = [
            retriever.retrieve_for_query(query, chunks, top_k=5)
            for query in queries
        ]
        return XML5RetrievalPreviewResult(
            xml_file=xml_path,
            effective_date=effective_date,
            note_records=note_records,
            retrieval_results=retrieval_results,
        )
