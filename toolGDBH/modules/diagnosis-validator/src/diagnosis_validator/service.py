from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from claim_models import ParsedClaim


@dataclass(slots=True)
class DiagnosisGuidelineSource:
    source_id: str
    title: str
    source_type: str
    source_path: str
    section_ref: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None


@dataclass(slots=True)
class DiagnosisEvidenceRule:
    rule_id: str
    evidence_type: str
    requirement_level: str
    codes: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    note: str = ""


@dataclass(slots=True)
class DiagnosisGuidelineProfile:
    profile_id: str
    diagnosis_codes: list[str]
    diagnosis_label: str
    specialty: str | None = None
    source_documents: list[DiagnosisGuidelineSource] = field(default_factory=list)
    required_symptoms: list[str] = field(default_factory=list)
    required_tests: list[str] = field(default_factory=list)
    supporting_findings: list[str] = field(default_factory=list)
    exclusion_findings: list[str] = field(default_factory=list)
    recommended_services: list[str] = field(default_factory=list)
    recommended_drugs: list[str] = field(default_factory=list)
    evidence_rules: list[DiagnosisEvidenceRule] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DiagnosisTimelineRef:
    ref_id: str
    ref_type: str
    event_time: str | None = None
    code: str | None = None
    text: str | None = None


@dataclass(slots=True)
class DiagnosisCaseRecord:
    claim_id: str
    facility_id: str
    patient_id: str
    visit_type: str
    primary_diagnosis_code: str
    secondary_diagnosis_codes: list[str] = field(default_factory=list)
    diagnosis_text_tokens: list[str] = field(default_factory=list)
    clinical_keywords: list[str] = field(default_factory=list)
    service_codes: list[str] = field(default_factory=list)
    drug_codes: list[str] = field(default_factory=list)
    supply_codes: list[str] = field(default_factory=list)
    result_codes: list[str] = field(default_factory=list)
    result_keywords: list[str] = field(default_factory=list)
    note_refs: list[str] = field(default_factory=list)
    timeline_refs: list[DiagnosisTimelineRef] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DiagnosisValidationResult:
    claim_id: str
    diagnosis_code: str
    profile_id: str | None
    validation_status: str
    matched_symptoms: list[str] = field(default_factory=list)
    matched_tests: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    conflicting_evidence: list[str] = field(default_factory=list)
    recommended_action: str = "review"
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DiagnosisValidatorService:
    def load_case_records(self, file_path: str | Path) -> list[DiagnosisCaseRecord]:
        rows = self._load_jsonl(file_path)
        records: list[DiagnosisCaseRecord] = []
        for row in rows:
            records.append(
                DiagnosisCaseRecord(
                    claim_id=str(row["claim_id"]),
                    facility_id=str(row.get("facility_id", "")),
                    patient_id=str(row.get("patient_id", "")),
                    visit_type=str(row.get("visit_type", "")),
                    primary_diagnosis_code=str(row.get("primary_diagnosis_code", "")),
                    secondary_diagnosis_codes=[str(item) for item in row.get("secondary_diagnosis_codes", [])],
                    diagnosis_text_tokens=[str(item) for item in row.get("diagnosis_text_tokens", [])],
                    clinical_keywords=[str(item) for item in row.get("clinical_keywords", [])],
                    service_codes=[str(item) for item in row.get("service_codes", [])],
                    drug_codes=[str(item) for item in row.get("drug_codes", [])],
                    supply_codes=[str(item) for item in row.get("supply_codes", [])],
                    result_codes=[str(item) for item in row.get("result_codes", [])],
                    result_keywords=[str(item) for item in row.get("result_keywords", [])],
                    note_refs=[str(item) for item in row.get("note_refs", [])],
                    timeline_refs=[DiagnosisTimelineRef(**item) for item in row.get("timeline_refs", [])],
                )
            )
        return records

    def load_profiles(self, file_path: str | Path) -> list[DiagnosisGuidelineProfile]:
        rows = self._load_jsonl(file_path)
        profiles: list[DiagnosisGuidelineProfile] = []
        for row in rows:
            profiles.append(
                DiagnosisGuidelineProfile(
                    profile_id=str(row["profile_id"]),
                    diagnosis_codes=[str(item) for item in row.get("diagnosis_codes", [])],
                    diagnosis_label=str(row.get("diagnosis_label", "")),
                    specialty=str(row.get("specialty")) if row.get("specialty") else None,
                    source_documents=[
                        DiagnosisGuidelineSource(**item)
                        for item in row.get("source_documents", [])
                    ],
                    required_symptoms=[str(item) for item in row.get("required_symptoms", [])],
                    required_tests=[str(item) for item in row.get("required_tests", [])],
                    supporting_findings=[str(item) for item in row.get("supporting_findings", [])],
                    exclusion_findings=[str(item) for item in row.get("exclusion_findings", [])],
                    recommended_services=[str(item) for item in row.get("recommended_services", [])],
                    recommended_drugs=[str(item) for item in row.get("recommended_drugs", [])],
                    evidence_rules=[
                        DiagnosisEvidenceRule(**item)
                        for item in row.get("evidence_rules", [])
                    ],
                )
            )
        return profiles

    def save_profiles(
        self,
        profiles: list[DiagnosisGuidelineProfile],
        file_path: str | Path,
    ) -> None:
        self._save_jsonl([item.to_dict() for item in profiles], file_path)

    def save_case_records(
        self,
        records: list[DiagnosisCaseRecord],
        file_path: str | Path,
    ) -> None:
        self._save_jsonl([item.to_dict() for item in records], file_path)

    def save_validation_results(
        self,
        results: list[DiagnosisValidationResult],
        file_path: str | Path,
    ) -> None:
        self._save_jsonl([item.to_dict() for item in results], file_path)

    def build_case_record(self, claim: ParsedClaim) -> DiagnosisCaseRecord:
        note_text = " ".join(note.note_text or "" for note in claim.clinical_notes)
        result_text = " ".join(
            " ".join(
                filter(
                    None,
                    [
                        result.indicator_name,
                        result.description,
                        result.conclusion,
                        result.value,
                    ],
                )
            )
            for result in claim.clinical_results
        )
        diagnosis_token_source = " ".join(
            [claim.header.primary_diagnosis_code, *claim.header.secondary_diagnosis_codes]
        )
        diagnosis_tokens = self._extract_keywords(diagnosis_token_source)
        clinical_keywords = self._extract_keywords(note_text)
        result_keywords = self._extract_keywords(result_text)

        timeline_refs: list[DiagnosisTimelineRef] = []
        for note in claim.clinical_notes:
            timeline_refs.append(
                DiagnosisTimelineRef(
                    ref_id=note.note_id,
                    ref_type="xml5_note",
                    event_time=note.note_time,
                    text=(note.note_text or "")[:240],
                )
            )
        for result in claim.clinical_results:
            timeline_refs.append(
                DiagnosisTimelineRef(
                    ref_id=result.result_id,
                    ref_type="clinical_result",
                    event_time=result.result_time,
                    code=result.service_code,
                    text=((result.indicator_name or "") + " " + (result.conclusion or "")).strip()[:240],
                )
            )
        for line in claim.lines:
            timeline_refs.append(
                DiagnosisTimelineRef(
                    ref_id=line.line_id,
                    ref_type=f"{line.line_type}_line",
                    event_time=line.execution_time or line.ordering_time,
                    code=line.item_code,
                    text=(line.item_name or "")[:240],
                )
            )

        return DiagnosisCaseRecord(
            claim_id=claim.header.claim_id,
            facility_id=claim.header.facility_id,
            patient_id=claim.header.patient_id,
            visit_type=claim.header.visit_type,
            primary_diagnosis_code=claim.header.primary_diagnosis_code,
            secondary_diagnosis_codes=list(claim.header.secondary_diagnosis_codes),
            diagnosis_text_tokens=diagnosis_tokens,
            clinical_keywords=clinical_keywords,
            service_codes=sorted(
                {line.item_code for line in claim.lines if line.line_type == "service" and line.item_code}
            ),
            drug_codes=sorted(
                {line.item_code for line in claim.lines if line.line_type == "drug" and line.item_code}
            ),
            supply_codes=sorted(
                {line.item_code for line in claim.lines if line.line_type == "supply" and line.item_code}
            ),
            result_codes=sorted(
                {result.service_code for result in claim.clinical_results if result.service_code}
            ),
            result_keywords=result_keywords,
            note_refs=[note.note_id for note in claim.clinical_notes if note.note_id],
            timeline_refs=timeline_refs,
        )

    def build_empty_validation_result(
        self,
        claim_id: str,
        diagnosis_code: str,
        profile_id: str | None,
    ) -> DiagnosisValidationResult:
        return DiagnosisValidationResult(
            claim_id=claim_id,
            diagnosis_code=diagnosis_code,
            profile_id=profile_id,
            validation_status="missing_evidence",
            recommended_action="request_more",
            summary="Chua doi chieu profile va evidence day du.",
        )

    def find_profile_for_case(
        self,
        case_record: DiagnosisCaseRecord,
        profiles: list[DiagnosisGuidelineProfile],
    ) -> DiagnosisGuidelineProfile | None:
        diagnosis_codes = {
            case_record.primary_diagnosis_code,
            *case_record.secondary_diagnosis_codes,
        }
        for profile in profiles:
            if diagnosis_codes.intersection(set(profile.diagnosis_codes)):
                return profile
        return None

    def validate_case_record(
        self,
        case_record: DiagnosisCaseRecord,
        profiles: list[DiagnosisGuidelineProfile],
    ) -> DiagnosisValidationResult:
        profile = self.find_profile_for_case(case_record, profiles)
        if profile is None:
            return DiagnosisValidationResult(
                claim_id=case_record.claim_id,
                diagnosis_code=case_record.primary_diagnosis_code,
                profile_id=None,
                validation_status="missing_profile",
                missing_evidence=["diagnosis_guideline_profile"],
                recommended_action="review",
                summary="Chua co profile doi chieu cho ma benh nay.",
            )

        evidence_pool = set(case_record.clinical_keywords) | set(case_record.result_keywords)
        evidence_pool.update(case_record.diagnosis_text_tokens)
        evidence_text = self._case_record_search_text(case_record)
        code_pool = set(case_record.service_codes) | set(case_record.drug_codes) | set(case_record.result_codes)

        matched_symptoms = [
            symptom
            for symptom in profile.required_symptoms
            if self._phrase_matches_tokens(symptom, evidence_pool)
            or self._phrase_matches_text(symptom, evidence_text)
        ]
        matched_tests = [
            test
            for test in profile.required_tests
            if self._phrase_matches_tokens(test, evidence_pool)
            or self._phrase_matches_text(test, evidence_text)
            or test in code_pool
        ]
        supporting_matches = [
            finding
            for finding in profile.supporting_findings
            if self._phrase_matches_tokens(finding, evidence_pool)
            or self._phrase_matches_text(finding, evidence_text)
        ]
        conflicting_evidence = [
            finding
            for finding in profile.exclusion_findings
            if self._phrase_matches_text(finding, evidence_text)
        ]

        recommended_code_matches: list[str] = []
        for code in [*profile.recommended_services, *profile.recommended_drugs]:
            if code in code_pool:
                recommended_code_matches.append(code)

        missing_evidence: list[str] = []
        if profile.required_symptoms and not matched_symptoms:
            missing_evidence.append("required_symptoms")
        if profile.required_tests and not matched_tests:
            missing_evidence.append("required_tests")
        if (profile.supporting_findings or profile.recommended_services or profile.recommended_drugs) and not (
            supporting_matches or recommended_code_matches
        ):
            missing_evidence.append("supporting_findings_or_recommended_codes")

        if conflicting_evidence:
            status = "suspected_mismatch"
            action = "review"
        elif not missing_evidence and (matched_symptoms or matched_tests or supporting_matches or recommended_code_matches):
            status = "strong_match"
            action = "accept"
        elif matched_symptoms or matched_tests or supporting_matches or recommended_code_matches:
            status = "partial_match"
            action = "review"
        else:
            status = "missing_evidence"
            action = "request_more"

        summary_parts = [
            f"Profile {profile.profile_id}",
            f"matched_symptoms={len(matched_symptoms)}",
            f"matched_tests={len(matched_tests)}",
            f"supporting_matches={len(supporting_matches)}",
            f"recommended_code_matches={len(recommended_code_matches)}",
        ]
        if conflicting_evidence:
            summary_parts.append(f"conflicts={len(conflicting_evidence)}")
        if missing_evidence:
            summary_parts.append(f"missing={','.join(missing_evidence)}")

        return DiagnosisValidationResult(
            claim_id=case_record.claim_id,
            diagnosis_code=case_record.primary_diagnosis_code,
            profile_id=profile.profile_id,
            validation_status=status,
            matched_symptoms=matched_symptoms,
            matched_tests=matched_tests + recommended_code_matches,
            missing_evidence=missing_evidence,
            conflicting_evidence=conflicting_evidence,
            recommended_action=action,
            summary=" | ".join(summary_parts),
        )

    def validate_case_records(
        self,
        case_records: list[DiagnosisCaseRecord],
        profiles: list[DiagnosisGuidelineProfile],
    ) -> list[DiagnosisValidationResult]:
        return [self.validate_case_record(case_record, profiles) for case_record in case_records]

    def _normalize_text(self, raw_value: str | None) -> str:
        normalized = unicodedata.normalize("NFD", (raw_value or "").strip().lower())
        normalized = normalized.replace("đ", "d")
        normalized = "".join(
            character for character in normalized if unicodedata.category(character) != "Mn"
        )
        normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
        return " ".join(part for part in normalized.split() if part)

    def _extract_keywords(self, raw_text: str | None, min_len: int = 3) -> list[str]:
        normalized = self._normalize_text(raw_text)
        tokens = [token for token in normalized.split() if len(token) >= min_len]
        seen: set[str] = set()
        ordered: list[str] = []
        for token in tokens:
            if token in seen:
                continue
            seen.add(token)
            ordered.append(token)
        return ordered

    def _phrase_matches_tokens(self, phrase: str, evidence_pool: set[str]) -> bool:
        normalized = self._normalize_text(phrase)
        if not normalized:
            return False
        parts = normalized.split()
        return all(part in evidence_pool for part in parts)

    def _phrase_matches_text(self, phrase: str, normalized_text: str) -> bool:
        normalized_phrase = self._normalize_text(phrase)
        if not normalized_phrase:
            return False
        return normalized_phrase in normalized_text

    def _case_record_search_text(self, case_record: DiagnosisCaseRecord) -> str:
        text_parts = [
            " ".join(case_record.clinical_keywords),
            " ".join(case_record.result_keywords),
            " ".join(case_record.diagnosis_text_tokens),
        ]
        text_parts.extend(ref.text or "" for ref in case_record.timeline_refs)
        return self._normalize_text(" ".join(text_parts))

    def _load_jsonl(self, file_path: str | Path) -> list[dict[str, Any]]:
        path = Path(file_path)
        if not path.exists():
            return []
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _save_jsonl(self, rows: list[dict[str, Any]], file_path: str | Path) -> None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""),
            encoding="utf-8",
        )
