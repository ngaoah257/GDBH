from __future__ import annotations

import json
import re
import unicodedata
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET


WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


@dataclass(slots=True)
class GuidelineRawDocument:
    doc_id: str
    title: str
    source_path: str
    issuer: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    specialty: str | None = None
    version: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class GuidelineCandidate:
    candidate_id: str
    doc_id: str
    source_path: str
    title: str
    section_path: list[str] = field(default_factory=list)
    paragraph_index: int = 0
    statement_type_hint: str = "unknown"
    source_text: str = ""
    source_section: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class GuidelineCondition:
    diagnosis_codes: list[str] = field(default_factory=list)
    clinical_context_tags: list[str] = field(default_factory=list)
    demographics: list[str] = field(default_factory=list)
    timing_constraints: list[str] = field(default_factory=list)
    lab_constraints: list[str] = field(default_factory=list)
    procedure_constraints: list[str] = field(default_factory=list)


@dataclass(slots=True)
class GuidelineRecommendedAction:
    action_type: str = "warn"
    target_codes: list[str] = field(default_factory=list)
    target_groups: list[str] = field(default_factory=list)
    text: str = ""


@dataclass(slots=True)
class GuidelineContraindication:
    diagnosis_codes: list[str] = field(default_factory=list)
    clinical_context_tags: list[str] = field(default_factory=list)
    lab_constraints: list[str] = field(default_factory=list)
    text: str | None = None


@dataclass(slots=True)
class GuidelineEvidenceRequirement:
    evidence_type: str
    codes: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    min_count: int = 1
    time_window: str | None = None


@dataclass(slots=True)
class GuidelineStatement:
    statement_id: str
    doc_id: str
    statement_type: str
    condition: GuidelineCondition = field(default_factory=GuidelineCondition)
    recommended_action: GuidelineRecommendedAction = field(default_factory=GuidelineRecommendedAction)
    contraindication: GuidelineContraindication = field(default_factory=GuidelineContraindication)
    required_evidence: list[GuidelineEvidenceRequirement] = field(default_factory=list)
    applies_to_codes: list[str] = field(default_factory=list)
    priority: int = 50
    source_quote: str = ""
    source_section: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class GuidelineRuleDraft:
    draft_rule_id: str
    statement_id: str
    rule_family: str
    severity: str
    suggested_action: str
    trigger: dict[str, object]
    required_evidence: list[dict[str, object]]
    decision_logic_text: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class GuidelineManifest:
    manifest_id: str
    generated_at: str
    source_path: str
    output_path: str
    record_count: int
    artifact_type: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class GuidelineInternalCodeMapping:
    placeholder_code: str
    mapped_code: str
    item_type: str
    label: str
    note: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class GuidelineRuleBuilderService:
    def build_candidates_from_directory(self, input_dir: str | Path) -> tuple[list[GuidelineRawDocument], list[GuidelineCandidate]]:
        input_dir = Path(input_dir)
        raw_documents: list[GuidelineRawDocument] = []
        candidates: list[GuidelineCandidate] = []
        for file_path in sorted(input_dir.iterdir()):
            if file_path.suffix.lower() not in {".doc", ".docx"} or not file_path.is_file():
                continue
            raw_document, doc_candidates = self.build_candidates_from_word(file_path)
            raw_documents.append(raw_document)
            candidates.extend(doc_candidates)
        return raw_documents, candidates

    def build_candidates_from_word(self, file_path: str | Path) -> tuple[GuidelineRawDocument, list[GuidelineCandidate]]:
        file_path = Path(file_path)
        if file_path.suffix.lower() == ".docx":
            return self.build_candidates_from_docx(file_path)
        if file_path.suffix.lower() == ".doc":
            converted_path = self._convert_doc_to_docx(file_path)
            return self.build_candidates_from_docx(converted_path, source_path=file_path)
        raise ValueError(f"Unsupported guideline file type: {file_path.suffix}")

    def build_candidates_from_docx(
        self,
        file_path: str | Path,
        source_path: str | Path | None = None,
    ) -> tuple[GuidelineRawDocument, list[GuidelineCandidate]]:
        file_path = Path(file_path)
        source_path = Path(source_path) if source_path else file_path
        paragraphs = self._extract_docx_paragraphs(file_path)
        title = self._infer_title(source_path, paragraphs)
        doc_id = source_path.stem
        raw_document = GuidelineRawDocument(
            doc_id=doc_id,
            title=title,
            source_path=str(source_path),
        )
        section_stack: list[str] = []
        candidates: list[GuidelineCandidate] = []
        for index, paragraph in enumerate(paragraphs, start=1):
            text = self._normalize_text(paragraph["text"])
            if not text:
                continue
            style_name = paragraph["style"]
            if self._is_heading(style_name, text):
                section_stack = self._update_section_stack(section_stack, text)
                continue
            if len(text) < 20:
                continue
            candidates.append(
                GuidelineCandidate(
                    candidate_id=f"{doc_id}:candidate:{len(candidates)+1}",
                    doc_id=doc_id,
                    source_path=str(source_path),
                    title=title,
                    section_path=list(section_stack),
                    paragraph_index=index,
                    statement_type_hint=self._infer_statement_type(text),
                    source_text=text,
                    source_section=" > ".join(section_stack) if section_stack else title,
                )
            )
        return raw_document, candidates

    def build_rule_drafts_from_statements(
        self,
        statements: list[GuidelineStatement],
    ) -> list[GuidelineRuleDraft]:
        drafts: list[GuidelineRuleDraft] = []
        for index, statement in enumerate(statements, start=1):
            severity, suggested_action = self._infer_rule_controls(statement)
            trigger = {
                "statement_type": statement.statement_type,
                "condition": asdict(statement.condition),
                "contraindication": asdict(statement.contraindication),
                "applies_to_codes": statement.applies_to_codes,
            }
            drafts.append(
                GuidelineRuleDraft(
                    draft_rule_id=f"GL.DRAFT.{index:03d}",
                    statement_id=statement.statement_id,
                    rule_family="GUIDELINE",
                    severity=severity,
                    suggested_action=suggested_action,
                    trigger=json.loads(json.dumps(trigger, ensure_ascii=False)),
                    required_evidence=[asdict(item) for item in statement.required_evidence],
                    decision_logic_text=self._build_decision_logic_text(statement),
                )
            )
        return drafts

    def load_statements(self, input_path: str | Path) -> list[GuidelineStatement]:
        statements: list[GuidelineStatement] = []
        for row in self._load_jsonl(input_path):
            condition = GuidelineCondition(**row.get("condition", {}))
            recommended_action = GuidelineRecommendedAction(**row.get("recommended_action", {}))
            contraindication = GuidelineContraindication(**row.get("contraindication", {}))
            required_evidence = [
                GuidelineEvidenceRequirement(**item)
                for item in row.get("required_evidence", [])
            ]
            statements.append(
                GuidelineStatement(
                    statement_id=row["statement_id"],
                    doc_id=row["doc_id"],
                    statement_type=row["statement_type"],
                    condition=condition,
                    recommended_action=recommended_action,
                    contraindication=contraindication,
                    required_evidence=required_evidence,
                    applies_to_codes=list(row.get("applies_to_codes", [])),
                    priority=int(row.get("priority", 50)),
                    source_quote=row.get("source_quote", ""),
                    source_section=row.get("source_section", ""),
                )
            )
        return statements

    def export_candidates(
        self,
        input_dir: str | Path,
        output_root: str | Path,
    ) -> tuple[Path, Path, Path]:
        output_root = Path(output_root)
        raw_dir = output_root / "raw"
        parsed_dir = output_root / "parsed"
        manifests_dir = output_root / "manifests"
        raw_dir.mkdir(parents=True, exist_ok=True)
        parsed_dir.mkdir(parents=True, exist_ok=True)
        manifests_dir.mkdir(parents=True, exist_ok=True)

        raw_documents, candidates = self.build_candidates_from_directory(input_dir)
        raw_output = raw_dir / "guideline_raw_documents.jsonl"
        parsed_output = parsed_dir / "guideline_candidates.jsonl"
        manifest_output = manifests_dir / "guideline_candidates.manifest.json"

        self._write_jsonl(raw_output, raw_documents)
        self._write_jsonl(parsed_output, candidates)
        manifest = GuidelineManifest(
            manifest_id="guideline-candidates@0.1.0",
            generated_at=self._now_iso(),
            source_path=str(Path(input_dir)),
            output_path=str(parsed_output),
            record_count=len(candidates),
            artifact_type="guideline_candidate",
        )
        manifest_output.write_text(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return raw_output, parsed_output, manifest_output

    def export_rule_drafts(
        self,
        statements_path: str | Path,
        output_root: str | Path,
    ) -> tuple[Path, Path]:
        output_root = Path(output_root)
        drafts_dir = output_root / "drafts"
        manifests_dir = output_root / "manifests"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        manifests_dir.mkdir(parents=True, exist_ok=True)

        statements = self.load_statements(statements_path)
        drafts = self.build_rule_drafts_from_statements(statements)
        drafts_output = drafts_dir / "guideline_rule_drafts.jsonl"
        manifest_output = manifests_dir / "guideline_rule_drafts.manifest.json"
        self._write_jsonl(drafts_output, drafts)
        manifest = GuidelineManifest(
            manifest_id="guideline-rule-drafts@0.1.0",
            generated_at=self._now_iso(),
            source_path=str(Path(statements_path)),
            output_path=str(drafts_output),
            record_count=len(drafts),
            artifact_type="guideline_rule_draft",
        )
        manifest_output.write_text(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return drafts_output, manifest_output

    def load_internal_code_mappings(
        self,
        mapping_path: str | Path,
    ) -> list[GuidelineInternalCodeMapping]:
        payload = json.loads(Path(mapping_path).read_text(encoding="utf-8"))
        rows = payload.get("mappings", payload)
        mappings: list[GuidelineInternalCodeMapping] = []
        for row in rows:
            mappings.append(
                GuidelineInternalCodeMapping(
                    placeholder_code=row["placeholder_code"],
                    mapped_code=row["mapped_code"],
                    item_type=row.get("item_type", "service"),
                    label=row.get("label", row["mapped_code"]),
                    note=row.get("note", ""),
                )
            )
        return mappings

    def apply_internal_code_mappings(
        self,
        statements: list[GuidelineStatement],
        mappings: list[GuidelineInternalCodeMapping],
    ) -> list[GuidelineStatement]:
        mapping_by_placeholder = {
            row.placeholder_code: row.mapped_code
            for row in mappings
        }
        updated: list[GuidelineStatement] = []
        for statement in statements:
            statement.applies_to_codes = self._map_codes(statement.applies_to_codes, mapping_by_placeholder)
            statement.recommended_action.target_codes = self._map_codes(
                statement.recommended_action.target_codes,
                mapping_by_placeholder,
            )
            for evidence in statement.required_evidence:
                evidence.codes = self._map_codes(evidence.codes, mapping_by_placeholder)
            updated.append(statement)
        return updated

    def export_mapped_statements(
        self,
        statements_path: str | Path,
        mapping_path: str | Path,
        output_path: str | Path,
    ) -> tuple[Path, Path]:
        statements = self.load_statements(statements_path)
        mappings = self.load_internal_code_mappings(mapping_path)
        mapped_statements = self.apply_internal_code_mappings(statements, mappings)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        manifests_dir = output_path.parent.parent / "manifests"
        manifests_dir.mkdir(parents=True, exist_ok=True)
        manifest_output = manifests_dir / "guideline_internal_code_mapping.manifest.json"

        self._write_jsonl(output_path, mapped_statements)
        manifest = GuidelineManifest(
            manifest_id="guideline-internal-code-mapping@0.1.0",
            generated_at=self._now_iso(),
            source_path=str(Path(statements_path)),
            output_path=str(output_path),
            record_count=len(mapped_statements),
            artifact_type="guideline_internal_code_mapping",
        )
        manifest_output.write_text(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return output_path, manifest_output

    def load_candidates(self, input_path: str | Path) -> list[GuidelineCandidate]:
        candidates: list[GuidelineCandidate] = []
        for row in self._load_jsonl(input_path):
            candidates.append(
                GuidelineCandidate(
                    candidate_id=row["candidate_id"],
                    doc_id=row["doc_id"],
                    source_path=row["source_path"],
                    title=row.get("title", ""),
                    section_path=list(row.get("section_path", [])),
                    paragraph_index=int(row.get("paragraph_index", 0)),
                    statement_type_hint=row.get("statement_type_hint", "unknown"),
                    source_text=row.get("source_text", ""),
                    source_section=row.get("source_section"),
                )
            )
        return candidates

    def filter_business_candidates(self, candidates: list[GuidelineCandidate]) -> list[GuidelineCandidate]:
        return [candidate for candidate in candidates if self._is_business_candidate(candidate)]

    def export_business_candidates(
        self,
        candidates_path: str | Path,
        output_root: str | Path,
    ) -> tuple[Path, Path]:
        output_root = Path(output_root)
        parsed_dir = output_root / "parsed"
        manifests_dir = output_root / "manifests"
        parsed_dir.mkdir(parents=True, exist_ok=True)
        manifests_dir.mkdir(parents=True, exist_ok=True)

        candidates = self.load_candidates(candidates_path)
        business_candidates = self.filter_business_candidates(candidates)
        filtered_output = parsed_dir / "guideline_business_candidates.jsonl"
        manifest_output = manifests_dir / "guideline_business_candidates.manifest.json"
        self._write_jsonl(filtered_output, business_candidates)
        manifest = GuidelineManifest(
            manifest_id="guideline-business-candidates@0.1.0",
            generated_at=self._now_iso(),
            source_path=str(Path(candidates_path)),
            output_path=str(filtered_output),
            record_count=len(business_candidates),
            artifact_type="guideline_business_candidate",
        )
        manifest_output.write_text(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return filtered_output, manifest_output

    def _convert_doc_to_docx(self, file_path: Path) -> Path:
        converted_root = file_path.parent / ".converted-docx"
        converted_root.mkdir(parents=True, exist_ok=True)
        output_path = converted_root / f"{file_path.stem}.docx"
        if output_path.exists() and output_path.stat().st_mtime >= file_path.stat().st_mtime:
            return output_path

        try:
            import win32com.client  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "Cannot convert .doc guideline files because pywin32 is not available. "
                "Please convert them to .docx first or install pywin32."
            ) from exc

        word = None
        document = None
        try:
            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            word.DisplayAlerts = 0
            document = word.Documents.Open(str(file_path.resolve()))
            document.SaveAs(str(output_path.resolve()), FileFormat=16)
        except Exception as exc:  # pragma: no cover - depends on local Word install
            raise RuntimeError(
                f"Failed to convert '{file_path.name}' from .doc to .docx via Microsoft Word."
            ) from exc
        finally:
            if document is not None:
                document.Close(False)
            if word is not None:
                word.Quit()
        return output_path

    def _extract_docx_paragraphs(self, file_path: Path) -> list[dict[str, str]]:
        paragraphs: list[dict[str, str]] = []
        with zipfile.ZipFile(file_path) as archive:
            document_root = ET.fromstring(archive.read("word/document.xml"))
            styles = self._read_styles(archive)
            for paragraph in document_root.findall(".//w:body/w:p", WORD_NS):
                texts = paragraph.findall(".//w:t", WORD_NS)
                text = "".join(node.text or "" for node in texts).strip()
                style_id = ""
                style_el = paragraph.find(".//w:pPr/w:pStyle", WORD_NS)
                if style_el is not None:
                    style_id = style_el.attrib.get(f"{{{WORD_NS['w']}}}val", "")
                paragraphs.append(
                    {
                        "text": text,
                        "style": styles.get(style_id, style_id),
                    }
                )
        return paragraphs

    def _read_styles(self, archive: zipfile.ZipFile) -> dict[str, str]:
        if "word/styles.xml" not in archive.namelist():
            return {}
        styles_root = ET.fromstring(archive.read("word/styles.xml"))
        style_map: dict[str, str] = {}
        for style in styles_root.findall(".//w:style", WORD_NS):
            style_id = style.attrib.get(f"{{{WORD_NS['w']}}}styleId", "")
            style_name = ""
            name_el = style.find(".//w:name", WORD_NS)
            if name_el is not None:
                style_name = name_el.attrib.get(f"{{{WORD_NS['w']}}}val", "")
            if style_id:
                style_map[style_id] = style_name or style_id
        return style_map

    def _infer_title(self, file_path: Path, paragraphs: list[dict[str, str]]) -> str:
        for paragraph in paragraphs:
            text = self._normalize_text(paragraph["text"])
            if text:
                return text[:160]
        return file_path.stem

    def _is_heading(self, style_name: str, text: str) -> bool:
        normalized_style = style_name.lower()
        return (
            "heading" in normalized_style
            or normalized_style.startswith("title")
            or (len(text) <= 120 and text.isupper())
        )

    def _update_section_stack(self, stack: list[str], heading_text: str) -> list[str]:
        if re.match(r"^\d+(\.\d+)*", heading_text):
            level = heading_text.count(".") + 1
            return stack[: max(level - 1, 0)] + [heading_text]
        if not stack:
            return [heading_text]
        return stack[:-1] + [heading_text]

    def _infer_statement_type(self, text: str) -> str:
        lowered = text.lower()
        if any(term in lowered for term in ("chống chỉ định", "không dùng", "không được")):
            return "contraindication"
        if any(term in lowered for term in ("chỉ định", "nên", "khuyến cáo", "đề nghị")):
            return "indication"
        if any(term in lowered for term in ("cần", "phải", "yêu cầu", "theo dõi")):
            return "requirement"
        if any(term in lowered for term in ("phác đồ", "liều", "điều trị")):
            return "regimen"
        return "unknown"

    def _infer_rule_controls(self, statement: GuidelineStatement) -> tuple[str, str]:
        if statement.contraindication.text or statement.statement_type == "contraindication":
            return "reject", "reject"
        if statement.required_evidence:
            return "pending", "request_more"
        action_type = statement.recommended_action.action_type
        if action_type in {"forbid", "avoid"}:
            return "warning", "warn"
        return "warning", "warn"

    def _build_decision_logic_text(self, statement: GuidelineStatement) -> str:
        parts = [
            f"Statement type: {statement.statement_type}",
            f"Applies to: {', '.join(statement.applies_to_codes) if statement.applies_to_codes else '-'}",
            f"Recommended action: {statement.recommended_action.text or statement.recommended_action.action_type}",
            f"Source section: {statement.source_section or '-'}",
        ]
        return " | ".join(parts)

    def _is_business_candidate(self, candidate: GuidelineCandidate) -> bool:
        text = self._normalize_text(candidate.source_text)
        section = self._normalize_text(candidate.source_section or "")
        folded_text = self._fold_text(text)
        folded_section = self._fold_text(section)
        folded_combined = f"{folded_section} {folded_text}".strip()

        if not text or len(text) < 12:
            return False
        if self._looks_like_administrative_section(folded_section):
            return False
        if self._looks_like_administrative_text(folded_text):
            return False
        if self._looks_like_personnel_list(text):
            return False
        if self._looks_like_topic_heading_only(folded_text):
            return False
        if candidate.statement_type_hint != "unknown":
            return True
        if self._looks_like_medical_heading(folded_text):
            return True
        if self._contains_business_keywords(folded_combined):
            return True
        return False

    def _looks_like_administrative_section(self, folded_section: str) -> bool:
        markers = (
            "bo truong bo y te",
            "quyet dinh",
            "chu bien",
            "tham gia bien soan",
            "thanh vien bien soan",
            "ban thu ky",
            "ban tham dinh",
            "loi gioi thieu",
            "bang danh muc cac chu viet tat",
        )
        return any(marker in folded_section for marker in markers)

    def _looks_like_administrative_text(self, folded_text: str) -> bool:
        prefixes = (
            "can cu ",
            "theo de nghi",
            "dieu 1.",
            "dieu 2.",
            "dieu 3.",
            "dieu 4.",
        )
        if any(folded_text.startswith(prefix) for prefix in prefixes):
            return True
        if re.match(r"^\d+(\.\d+)+\.\s+.+\s+\d+$", folded_text):
            return True
        terms = (
            "quyet dinh nay",
            "chiu trach nhiem thi hanh",
            "ban hanh kem theo quyet dinh",
            "chuc nang, nhiem vu, quyen han",
            "so y te",
        )
        return any(term in folded_text for term in terms)

    def _looks_like_personnel_list(self, text: str) -> bool:
        title_hits = len(re.findall(r"\b(GS|PGS|TS|ThS|BSCKII|BSCKI)\.?\b", text, flags=re.IGNORECASE))
        return title_hits >= 2

    def _looks_like_medical_heading(self, folded_text: str) -> bool:
        markers = (
            "chan doan",
            "dieu tri",
            "phac do",
            "ung thu",
            "cap cuu",
            "di can",
        )
        return any(marker in folded_text for marker in markers)

    def _looks_like_topic_heading_only(self, folded_text: str) -> bool:
        if not re.match(r"^bai\s+\d+[.:]?\s+", folded_text):
            return False
        if any(keyword in folded_text for keyword in ("chi dinh", "chong chi dinh", "phac do", "lieu", "can ", "phai ")):
            return False
        word_count = len(re.findall(r"\w+", folded_text))
        return word_count <= 12

    def _contains_business_keywords(self, folded_text: str) -> bool:
        keywords = (
            "chi dinh",
            "chong chi dinh",
            "chan doan",
            "dieu tri",
            "phac do",
            "lieu",
            "hoa chat",
            "xa tri",
            "phau thuat",
            "thuoc",
            "xet nghiem",
            "theo doi",
            "trieu chung",
            "ung thu",
            "benh nhan",
            "di can",
            "cap cuu",
        )
        return any(keyword in folded_text for keyword in keywords)

    def _normalize_text(self, raw_text: str) -> str:
        normalized = re.sub(r"\s+", " ", raw_text or "")
        return normalized.strip()

    def _fold_text(self, raw_text: str) -> str:
        normalized = unicodedata.normalize("NFKD", raw_text or "")
        without_marks = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        return without_marks.lower().replace("đ", "d").replace("Đ", "d")

    def _map_codes(
        self,
        codes: list[str],
        mapping_by_placeholder: dict[str, str],
    ) -> list[str]:
        mapped_codes: list[str] = []
        for code in codes:
            mapped = mapping_by_placeholder.get(code, code)
            if mapped not in mapped_codes:
                mapped_codes.append(mapped)
        return mapped_codes

    def _load_jsonl(self, input_path: str | Path) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        path = Path(input_path)
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rows.append(json.loads(line))
        return rows

    def _write_jsonl(self, output_path: Path, records: list[object]) -> None:
        with output_path.open("w", encoding="utf-8") as handle:
            for record in records:
                payload = record.to_dict() if hasattr(record, "to_dict") else asdict(record)
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
