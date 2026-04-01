from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from claim_models import (
    KBChunkMetadata,
    KBManifest,
    KBQueryFilters,
    KBStructuredFields,
    KnowledgeChunk,
    ParsedDocument,
    QueryRecord,
    XML5EvidenceFlags,
    XML5NoteRecord,
    XML5RawRef,
)


class XML5KnowledgeBaseBuilder:
    KB_VERSION = "xml5-kb-0.1.0"
    SOURCE_TYPE = "xml5_note"
    CHUNK_TYPE = "clinical_note_pattern"
    ARTIFACT_FAMILY = "xml5_note_record"

    def load_note_records(self, input_path: str | Path) -> list[XML5NoteRecord]:
        path = Path(input_path)
        records: list[XML5NoteRecord] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            evidence_flags_payload = payload.get("evidence_flags", {})
            raw_ref_payload = payload.get("raw_ref", {})
            payload["evidence_flags"] = XML5EvidenceFlags(**evidence_flags_payload)
            payload["raw_ref"] = XML5RawRef(**raw_ref_payload)
            records.append(XML5NoteRecord(**payload))
        return records

    def build_parsed_documents(
        self,
        note_records: list[XML5NoteRecord],
        generated_at: str,
    ) -> list[ParsedDocument]:
        return [self._to_parsed_document(record, generated_at) for record in note_records]

    def build_chunks(self, note_records: list[XML5NoteRecord]) -> list[KnowledgeChunk]:
        return [self._to_knowledge_chunk(record) for record in note_records]

    def build_queries(self, note_records: list[XML5NoteRecord]) -> list[QueryRecord]:
        return [self._to_query_record(record) for record in note_records]

    def build_manifest(
        self,
        source_path: str | Path,
        parsed_output_path: str | Path,
        chunks_output_path: str | Path,
        queries_output_path: str | Path,
        note_records: list[XML5NoteRecord],
        generated_at: str,
    ) -> KBManifest:
        return KBManifest(
            manifest_id=f"{self.ARTIFACT_FAMILY}:{self.KB_VERSION}",
            kb_version=self.KB_VERSION,
            artifact_family=self.ARTIFACT_FAMILY,
            source_type=self.SOURCE_TYPE,
            source_path=str(Path(source_path)),
            parsed_output_path=str(Path(parsed_output_path)),
            chunks_output_path=str(Path(chunks_output_path)),
            queries_output_path=str(Path(queries_output_path)),
            generated_at=generated_at,
            parser_version=self._resolve_parser_version(note_records),
            input_record_count=len(note_records),
            parsed_document_count=len(note_records),
            chunk_count=len(note_records),
            query_count=len(note_records),
            notes_without_tags=sum(1 for record in note_records if not record.context_tags),
            notes_without_links=sum(
                1
                for record in note_records
                if not record.linked_line_ids and not record.linked_result_ids
            ),
        )

    def export(
        self,
        input_path: str | Path,
        output_root: str | Path,
    ) -> KBManifest:
        input_path = Path(input_path)
        output_root = Path(output_root)
        parsed_dir = output_root / "parsed"
        chunks_dir = output_root / "chunks"
        queries_dir = output_root / "queries"
        manifests_dir = output_root / "manifests"
        parsed_dir.mkdir(parents=True, exist_ok=True)
        chunks_dir.mkdir(parents=True, exist_ok=True)
        queries_dir.mkdir(parents=True, exist_ok=True)
        manifests_dir.mkdir(parents=True, exist_ok=True)

        generated_at = self._now_iso()
        records = self.load_note_records(input_path)
        parsed_documents = self.build_parsed_documents(records, generated_at)
        chunks = self.build_chunks(records)
        queries = self.build_queries(records)

        parsed_output_path = parsed_dir / "xml5_note_records.parsed.jsonl"
        chunks_output_path = chunks_dir / "xml5_note_records.chunks.jsonl"
        queries_output_path = queries_dir / "xml5_note_records.queries.jsonl"
        manifest_output_path = manifests_dir / "xml5_note_records.manifest.json"

        self._write_jsonl(parsed_output_path, parsed_documents)
        self._write_jsonl(chunks_output_path, chunks)
        self._write_jsonl(queries_output_path, queries)
        manifest = self.build_manifest(
            source_path=input_path,
            parsed_output_path=parsed_output_path,
            chunks_output_path=chunks_output_path,
            queries_output_path=queries_output_path,
            note_records=records,
            generated_at=generated_at,
        )
        manifest_output_path.write_text(
            json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return manifest

    def _to_parsed_document(self, record: XML5NoteRecord, generated_at: str) -> ParsedDocument:
        parsed_document_id = self._parsed_document_id(record)
        specialty = self._infer_specialty(record)
        return ParsedDocument(
            parsed_document_id=parsed_document_id,
            raw_document_id=f"xml5:{record.source_file_name}:{record.note_id}",
            kb_version=self.KB_VERSION,
            title=f"{record.primary_diagnosis_code or 'UNKNOWN'} {record.note_type} {record.note_id}",
            source_type=self.SOURCE_TYPE,
            text_content=record.clinical_text,
            structured_fields=KBStructuredFields(
                document_number=record.note_id,
                document_type=record.note_type,
                legal_basis=[],
                specialties=[specialty] if specialty else [],
                facility_scope=[record.facility_id] if record.facility_id else [],
                item_types=self._infer_item_types(record),
                codes=self._dedupe(record.linked_item_codes + self._diagnosis_codes(record)),
                keywords=self._dedupe(record.context_tags + [record.note_type]),
            ),
            effective_from=record.recorded_date,
            effective_to=record.recorded_date,
            parsed_at=generated_at,
            parser_version=record.parser_version,
        )

    def _to_knowledge_chunk(self, record: XML5NoteRecord) -> KnowledgeChunk:
        parsed_document_id = self._parsed_document_id(record)
        specialty = self._infer_specialty(record)
        keywords = self._dedupe(record.context_tags + [record.note_type])
        return KnowledgeChunk(
            chunk_id=f"{parsed_document_id}:chunk:0",
            kb_version=self.KB_VERSION,
            parsed_document_id=parsed_document_id,
            chunk_index=0,
            chunk_type=self.CHUNK_TYPE,
            title=f"{record.note_id} {record.note_type}",
            text_chunk=record.clinical_text,
            summary=self._build_summary(record),
            metadata=KBChunkMetadata(
                source_type=self.SOURCE_TYPE,
                legal_basis=[],
                effective_from=record.recorded_date,
                effective_to=record.recorded_date,
                specialties=[specialty] if specialty else [],
                facility_scope=[record.facility_id] if record.facility_id else [],
                item_types=self._infer_item_types(record),
                codes=self._dedupe(record.linked_item_codes + self._diagnosis_codes(record)),
                keywords=keywords,
                evidence_required=self._build_evidence_required(record),
                review_action_hint=self._build_review_action_hint(record),
                priority=self._build_priority(record),
            ),
        )

    def _to_query_record(self, record: XML5NoteRecord) -> QueryRecord:
        specialty = self._infer_specialty(record)
        return QueryRecord(
            query_id=f"query:{record.claim_id}:{record.note_id}",
            claim_id=record.claim_id,
            line_id=record.linked_line_ids[0] if len(record.linked_line_ids) == 1 else None,
            note_id=record.note_id,
            query_type=self._infer_query_type(record),
            effective_date=record.recorded_date or "",
            specialties=[specialty] if specialty else [],
            item_types=self._infer_item_types(record),
            codes=self._dedupe(record.linked_item_codes + self._diagnosis_codes(record)),
            instruction_text=self._build_instruction_text(record),
            query_text=self._build_query_text(record),
            filters=KBQueryFilters(
                source_types=["xml5_note", "legal", "guideline", "catalog", "historical_decision"],
                facility_scope=[record.facility_id] if record.facility_id else [],
                effective_only=True,
            ),
        )

    def _parsed_document_id(self, record: XML5NoteRecord) -> str:
        return f"xml5:{record.claim_id}:{record.note_id}"

    def _diagnosis_codes(self, record: XML5NoteRecord) -> list[str]:
        codes = [record.primary_diagnosis_code] if record.primary_diagnosis_code else []
        codes.extend(record.secondary_diagnosis_codes)
        return [code for code in codes if code]

    def _infer_item_types(self, record: XML5NoteRecord) -> list[str]:
        item_types = {"note"}
        if any(code.startswith("XML4-") for code in record.linked_result_ids):
            item_types.add("clinical_result")
        if record.linked_item_codes:
            item_types.update(("service", "drug", "supply"))
        return sorted(item_types)

    def _infer_specialty(self, record: XML5NoteRecord) -> str | None:
        diagnosis_code = (record.primary_diagnosis_code or "").upper()
        if diagnosis_code.startswith("C50"):
            return "ung_buou_vu"
        if diagnosis_code.startswith("C34"):
            return "ung_buou_ho_hap"
        if diagnosis_code.startswith("C13"):
            return "ung_buou_tai_mui_hong"
        if diagnosis_code.startswith("C16"):
            return "ung_buou_tieu_hoa"
        return None

    def _build_summary(self, record: XML5NoteRecord) -> str:
        preview = record.clinical_text.strip()
        if len(preview) > 180:
            preview = preview[:177].rstrip() + "..."
        return preview

    def _build_query_text(self, record: XML5NoteRecord) -> str:
        parts = [
            f"chan doan: {record.primary_diagnosis_code}" if record.primary_diagnosis_code else "",
            f"note_type: {record.note_type}" if record.note_type else "",
            f"context: {', '.join(record.context_tags)}" if record.context_tags else "",
            f"codes: {', '.join(record.linked_item_codes)}" if record.linked_item_codes else "",
            record.clinical_text.strip(),
        ]
        return " | ".join(part for part in parts if part)

    def _build_instruction_text(self, record: XML5NoteRecord) -> str:
        if record.linked_line_ids or record.linked_result_ids:
            return "Tim can cu nghiep vu va boi canh lam sang lien quan den note XML5 va cac dong chi phi hoac ket qua da lien ket."
        return "Tim cac chunk co boi canh lam sang gan voi note XML5 de ho tro retrieval va reviewer."

    def _infer_query_type(self, record: XML5NoteRecord) -> str:
        if record.linked_line_ids or record.linked_result_ids:
            return "clinical_context_lookup"
        return "xml5_note_similarity"

    def _build_evidence_required(self, record: XML5NoteRecord) -> list[str]:
        evidence = ["xml5_note"]
        if record.linked_line_ids:
            evidence.append("claim_line")
        if record.linked_result_ids:
            evidence.append("clinical_result")
        return evidence

    def _build_review_action_hint(self, record: XML5NoteRecord) -> list[str]:
        hints: list[str] = []
        if not record.context_tags:
            hints.append("request_more")
        if record.linked_line_ids:
            hints.append("warn")
        if not hints:
            hints.append("accept")
        return self._dedupe(hints)

    def _build_priority(self, record: XML5NoteRecord) -> int:
        priority = 50
        if record.context_tags:
            priority += 10
        if record.linked_line_ids:
            priority += 10
        if record.linked_result_ids:
            priority += 5
        return priority

    def _resolve_parser_version(self, note_records: list[XML5NoteRecord]) -> str:
        for record in note_records:
            if record.parser_version:
                return record.parser_version
        return ""

    def _dedupe(self, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            if not value or value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result

    def _write_jsonl(self, output_path: Path, records: list[object]) -> None:
        with output_path.open("w", encoding="utf-8") as handle:
            for record in records:
                payload = record.to_dict() if hasattr(record, "to_dict") else asdict(record)
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
