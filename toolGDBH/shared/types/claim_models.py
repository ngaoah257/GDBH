from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(slots=True)
class ClaimHeader:
    claim_id: str
    facility_id: str
    patient_id: str
    insurance_card_no: str
    visit_type: str
    admission_time: str
    discharge_time: str
    primary_diagnosis_code: str
    route_code: str
    total_amount: Decimal
    insurance_amount: Decimal
    patient_pay_amount: Decimal
    claim_effective_date: str
    secondary_diagnosis_codes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ClaimLine:
    line_id: str
    claim_id: str
    line_type: str
    item_code: str
    item_name: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    execution_time: str | None = None
    ordering_time: str | None = None
    department_code: str | None = None
    practitioner_id: str | None = None
    equipment_ref: str | None = None
    source_xml: str | None = None
    source_node_path: str | None = None


@dataclass(slots=True)
class ClaimDocumentRef:
    document_id: str
    claim_id: str
    document_type: str
    file_name: str
    storage_uri: str
    content_hash: str
    created_at: str


@dataclass(slots=True)
class ClinicalResult:
    result_id: str
    claim_id: str
    service_code: str
    indicator_code: str | None = None
    indicator_name: str | None = None
    value: str | None = None
    unit: str | None = None
    description: str | None = None
    conclusion: str | None = None
    result_time: str | None = None
    practitioner_id: str | None = None
    source_xml: str | None = None
    source_node_path: str | None = None


@dataclass(slots=True)
class ClinicalNote:
    note_id: str
    claim_id: str
    note_text: str
    disease_stage: str | None = None
    consultation: str | None = None
    surgery: str | None = None
    note_time: str | None = None
    practitioner_id: str | None = None
    source_xml: str | None = None
    source_node_path: str | None = None


@dataclass(slots=True)
class XML5EvidenceFlags:
    has_diagnosis_context: bool = False
    has_treatment_context: bool = False
    has_procedure_context: bool = False
    has_lab_context: bool = False
    has_imaging_context: bool = False


@dataclass(slots=True)
class XML5RawRef:
    file_hoso_id: str | None = None
    xml_node_path: str | None = None


@dataclass(slots=True)
class XML5NoteRecord:
    schema_version: str
    claim_id: str
    note_id: str
    source_file_type: str
    source_file_name: str
    facility_id: str
    patient_id: str | None
    encounter_id: str | None
    department_code: str | None
    department_name: str | None
    practitioner_id: str | None
    practitioner_name: str | None
    recorded_at: str | None
    recorded_date: str | None
    admission_time: str | None
    discharge_time: str | None
    primary_diagnosis_code: str | None
    primary_diagnosis_text: str | None
    secondary_diagnosis_codes: list[str] = field(default_factory=list)
    secondary_diagnosis_texts: list[str] = field(default_factory=list)
    clinical_text: str = ""
    clinical_text_normalized: str = ""
    note_type: str = "unknown"
    context_tags: list[str] = field(default_factory=list)
    linked_line_ids: list[str] = field(default_factory=list)
    linked_item_codes: list[str] = field(default_factory=list)
    linked_result_ids: list[str] = field(default_factory=list)
    evidence_flags: XML5EvidenceFlags = field(default_factory=XML5EvidenceFlags)
    parser_version: str = ""
    raw_ref: XML5RawRef = field(default_factory=XML5RawRef)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return dict(payload)


@dataclass(slots=True)
class KBStructuredFields:
    document_number: str | None = None
    document_type: str | None = None
    legal_basis: list[str] = field(default_factory=list)
    specialties: list[str] = field(default_factory=list)
    facility_scope: list[str] = field(default_factory=list)
    item_types: list[str] = field(default_factory=list)
    codes: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ParsedDocument:
    parsed_document_id: str
    raw_document_id: str
    kb_version: str
    title: str
    source_type: str
    text_content: str
    structured_fields: KBStructuredFields = field(default_factory=KBStructuredFields)
    effective_from: str | None = None
    effective_to: str | None = None
    parsed_at: str = ""
    parser_version: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return dict(payload)


@dataclass(slots=True)
class KBChunkMetadata:
    source_type: str
    legal_basis: list[str] = field(default_factory=list)
    effective_from: str | None = None
    effective_to: str | None = None
    specialties: list[str] = field(default_factory=list)
    facility_scope: list[str] = field(default_factory=list)
    item_types: list[str] = field(default_factory=list)
    codes: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    evidence_required: list[str] = field(default_factory=list)
    review_action_hint: list[str] = field(default_factory=list)
    priority: int = 0


@dataclass(slots=True)
class KnowledgeChunk:
    chunk_id: str
    kb_version: str
    parsed_document_id: str
    chunk_index: int
    chunk_type: str
    title: str
    text_chunk: str
    summary: str | None
    metadata: KBChunkMetadata

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return dict(payload)


@dataclass(slots=True)
class KBManifest:
    manifest_id: str
    kb_version: str
    artifact_family: str
    source_type: str
    source_path: str
    parsed_output_path: str
    chunks_output_path: str
    generated_at: str
    parser_version: str
    input_record_count: int
    parsed_document_count: int
    chunk_count: int
    queries_output_path: str | None = None
    query_count: int = 0
    notes_without_tags: int = 0
    notes_without_links: int = 0

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return dict(payload)


@dataclass(slots=True)
class KBQueryFilters:
    source_types: list[str] = field(default_factory=list)
    facility_scope: list[str] = field(default_factory=list)
    effective_only: bool = True


@dataclass(slots=True)
class QueryRecord:
    query_id: str
    claim_id: str
    line_id: str | None
    note_id: str | None
    query_type: str
    effective_date: str
    specialties: list[str] = field(default_factory=list)
    item_types: list[str] = field(default_factory=list)
    codes: list[str] = field(default_factory=list)
    instruction_text: str = ""
    query_text: str = ""
    filters: KBQueryFilters = field(default_factory=KBQueryFilters)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return dict(payload)


@dataclass(slots=True)
class RetrievalHit:
    chunk_id: str
    score: float
    rank: int
    matched_codes: list[str] = field(default_factory=list)
    matched_keywords: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RetrievalResult:
    query_id: str
    retriever_version: str
    embedding_model: str
    results: list[RetrievalHit] = field(default_factory=list)
    retrieved_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return dict(payload)


@dataclass(slots=True)
class ParsedClaim:
    header: ClaimHeader
    lines: list[ClaimLine]
    documents: list[ClaimDocumentRef] = field(default_factory=list)
    clinical_results: list[ClinicalResult] = field(default_factory=list)
    clinical_notes: list[ClinicalNote] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return dict(payload)


@dataclass(slots=True)
class RuleHit:
    rule_hit_id: str
    claim_id: str
    rule_id: str
    severity: str
    legal_basis: str
    message: str
    suggested_action: str
    line_id: str | None = None
    estimated_amount_impact: Decimal = Decimal("0")
    required_evidence: list[str] = field(default_factory=list)


@dataclass(slots=True)
class EngineResult:
    claim_id: str
    hits: list[RuleHit] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return dict(payload)


@dataclass(slots=True)
class TriageResult:
    claim_id: str
    triage_level: str
    reason_codes: list[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return dict(payload)


@dataclass(slots=True)
class AuditEvent:
    event_id: str
    module_name: str
    entity_type: str
    entity_id: str
    action: str
    action_result: str
    version_ref: str
    created_at: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return dict(payload)


@dataclass(slots=True)
class EligibilityCheck:
    check_code: str
    status: str
    message: str


@dataclass(slots=True)
class EligibilityResult:
    claim_id: str
    card_valid: bool
    route_eligible: bool
    benefit_level: Decimal
    checks: list[EligibilityCheck] = field(default_factory=list)
    source_ref: str = "eligibility@0.1.0"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return dict(payload)


@dataclass(slots=True)
class StaffMember:
    practitioner_id: str
    practitioner_name: str
    department_code: str | None = None
    department_name: str | None = None
    title_code: str | None = None
    license_code: str | None = None
    practice_scope: str | None = None
    extra_service_codes: list[str] = field(default_factory=list)
    effective_from: str | None = None
    effective_to: str | None = None


@dataclass(slots=True)
class EquipmentItem:
    equipment_id: str
    equipment_name: str
    model_code: str | None = None
    manufacturer: str | None = None
    country_of_origin: str | None = None
    serial_or_asset_code: str | None = None
    license_code: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None


@dataclass(slots=True)
class ServiceItem:
    service_code: str
    approved_name: str
    price_name: str | None = None
    unit_price: Decimal = Decimal("0")
    decision_ref: str | None = None
    transfer_facilities: list[str] = field(default_factory=list)
    cls_facilities: list[str] = field(default_factory=list)
    effective_from: str | None = None
    effective_to: str | None = None


@dataclass(slots=True)
class DrugItem:
    drug_code: str
    drug_name: str
    active_ingredient: str | None = None
    dosage_form: str | None = None
    strength: str | None = None
    unit_name: str | None = None
    unit_price: Decimal = Decimal("0")
    insurance_group_code: str | None = None
    decision_ref: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None


@dataclass(slots=True)
class SupplyItem:
    supply_code: str
    supply_name: str
    unit_name: str | None = None
    unit_price: Decimal = Decimal("0")
    insurance_group_code: str | None = None
    decision_ref: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None


@dataclass(slots=True)
class MasterDataSnapshot:
    dataset_version: str
    effective_date: str
    facility_id: str | None = None
    staff_members: list[StaffMember] = field(default_factory=list)
    equipment_items: list[EquipmentItem] = field(default_factory=list)
    service_items: list[ServiceItem] = field(default_factory=list)
    all_service_items: list[ServiceItem] = field(default_factory=list)
    drug_items: list[DrugItem] = field(default_factory=list)
    all_drug_items: list[DrugItem] = field(default_factory=list)
    supply_items: list[SupplyItem] = field(default_factory=list)
    all_supply_items: list[SupplyItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return dict(payload)
