from __future__ import annotations

import base64
import hashlib
import re
import unicodedata
import xml.etree.ElementTree as ET
from decimal import Decimal
from pathlib import Path

from claim_models import (
    ClaimDocumentRef,
    ClaimHeader,
    ClaimLine,
    ClinicalNote,
    ClinicalResult,
    ParsedClaim,
    XML5EvidenceFlags,
    XML5NoteRecord,
    XML5RawRef,
)
from errors import ParseError


class ParserNormalizerService:
    """Doc goi GIAMDINHHS va chuan hoa XML1 thanh claim model toi thieu."""

    XML5_SCHEMA_VERSION = "1.0"
    XML5_PARSER_VERSION = "parser-xml5-0.1.0"
    _XML5_CONTEXT_KEYWORDS: dict[str, tuple[str, ...]] = {
        "khang sinh": ("khang sinh", "amoxicilin", "cef", "fisulty", "ceftriaxon"),
        "dau bung": ("dau bung", "dau vung bung", "dau o bung"),
        "buon non": ("buon non", "non 1 lan", "non nhieu lan"),
        "an kem": ("an kem",),
        "met moi": ("met", "met moi"),
        "suy kiet": ("suy kiet", "gay suy kiet"),
        "dau nguc vu": ("dau nhuc vu", "dau vu", "tuc nguc"),
        "dau nguc": ("dau nguc", "tuc nguc", "nguc trai", "nguc phai"),
        "hau phau": ("hau phau", "sau mo", "sau phau thuat", "vet mo"),
        "tieu hoa": ("thuong vi", "o hoi", "o chua", "day hoi", "trao nguoc"),
        "sonde": ("sonde", "mo thong da day", "chan mo thong da day"),
        "hoa chat": ("hoa chat", "paclitaxel", "docetaxel", "navelbin"),
        "sot": ("sot", "sot cao"),
        "x-quang": ("x-quang", "x quang"),
        "sieu am": ("sieu am",),
        "huyet hoc": ("huyet hoc", "bach cau", "hong cau"),
        "sinh hoa": ("sinh hoa", "ure", "creatinin", "dien giai"),
        "noi soi": ("noi soi",),
        "dai thao duong": ("dai thao duong", "tieu duong"),
    }
    _NOTE_TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
        "consult_note": ("hoi chan",),
        "procedure_note": ("phau thuat", "thu thuat"),
        "order_note": ("y lenh", "chi dinh"),
        "summary_note": ("tom tat", "ra vien", "vao vien"),
        "progress_note": ("dien bien", "kham toan than", "chan doan"),
    }

    def parse_file(self, file_path: str | Path) -> ParsedClaim:
        xml_text = Path(file_path).read_text(encoding="utf-8")
        return self.parse_text(xml_text)

    def build_xml5_note_records_from_file(self, file_path: str | Path) -> list[XML5NoteRecord]:
        file_path = Path(file_path)
        xml_text = file_path.read_text(encoding="utf-8")
        root = ET.fromstring(xml_text)
        return self._build_xml5_note_records(root, file_path.name)

    def build_xml5_note_records_from_directory(
        self,
        directory_path: str | Path,
    ) -> list[XML5NoteRecord]:
        directory_path = Path(directory_path)
        records: list[XML5NoteRecord] = []
        for file_path in sorted(directory_path.glob("*.xml")):
            records.extend(self.build_xml5_note_records_from_file(file_path))
        return records

    def parse_text(self, xml_text: str) -> ParsedClaim:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise ParseError("PARSER.XML.INVALID", f"XML khong hop le: {exc}") from exc

        if root.tag != "GIAMDINHHS":
            raise ParseError("PARSER.ROOT.INVALID", f"Root khong dung: {root.tag}")

        document_refs = self._extract_document_refs(root)
        xml1_content = self._extract_embedded_xml(root, "XML1")
        xml1_root = ET.fromstring(xml1_content)
        parsed_claim = self._parse_xml1(xml1_root)
        xml2_content = self._extract_optional_embedded_xml(root, "XML2")
        if xml2_content:
            parsed_claim.lines.extend(self._parse_xml2(ET.fromstring(xml2_content), parsed_claim))
        xml3_content = self._extract_optional_embedded_xml(root, "XML3")
        if xml3_content:
            parsed_claim.lines.extend(self._parse_xml3(ET.fromstring(xml3_content), parsed_claim))
        xml4_content = self._extract_optional_embedded_xml(root, "XML4")
        if xml4_content:
            parsed_claim.clinical_results.extend(
                self._parse_xml4(ET.fromstring(xml4_content), parsed_claim)
            )
        xml5_content = self._extract_optional_embedded_xml(root, "XML5")
        if xml5_content:
            parsed_claim.clinical_notes.extend(
                self._parse_xml5(ET.fromstring(xml5_content), parsed_claim)
            )
        for document in document_refs:
            document.claim_id = parsed_claim.header.claim_id
        parsed_claim.documents = document_refs
        return parsed_claim

    def _build_xml5_note_records(
        self,
        root: ET.Element,
        source_file_name: str,
    ) -> list[XML5NoteRecord]:
        parsed_claim = self.parse_text(ET.tostring(root, encoding="unicode"))
        records: list[XML5NoteRecord] = []
        for note in parsed_claim.clinical_notes:
            records.append(self._to_xml5_note_record(parsed_claim, note, source_file_name))
        return records

    def _extract_embedded_xml(self, root: ET.Element, expected_file_type: str) -> str:
        for filehoso in root.findall(".//FILEHOSO"):
            loai = (filehoso.findtext("LOAIHOSO") or "").strip().upper()
            noidung = (filehoso.findtext("NOIDUNGFILE") or "").strip()
            if loai == expected_file_type and noidung:
                try:
                    return base64.b64decode(noidung).decode("utf-8")
                except Exception as exc:  # noqa: BLE001
                    raise ParseError(
                        "PARSER.DECODE.FAIL",
                        f"Khong giai ma duoc {expected_file_type}: {exc}",
                    ) from exc

        raise ParseError("PARSER.FILE.MISSING", f"Khong tim thay {expected_file_type}")

    def _extract_optional_embedded_xml(self, root: ET.Element, expected_file_type: str) -> str | None:
        try:
            return self._extract_embedded_xml(root, expected_file_type)
        except ParseError as exc:
            if exc.error_code == "PARSER.FILE.MISSING":
                return None
            raise

    def _extract_document_refs(self, root: ET.Element) -> list[ClaimDocumentRef]:
        documents: list[ClaimDocumentRef] = []
        for index, filehoso in enumerate(root.findall(".//FILEHOSO"), start=1):
            document_type = (filehoso.findtext("LOAIHOSO") or "").strip().upper()
            encoded_content = (filehoso.findtext("NOIDUNGFILE") or "").strip()
            if not document_type or not encoded_content:
                continue
            try:
                decoded_bytes = base64.b64decode(encoded_content)
                content_hash = hashlib.sha256(decoded_bytes).hexdigest()
            except Exception:  # noqa: BLE001
                content_hash = hashlib.sha256(encoded_content.encode("utf-8")).hexdigest()
            documents.append(
                ClaimDocumentRef(
                    document_id=f"DOC.{index:03d}",
                    claim_id="",
                    document_type=document_type,
                    file_name=f"{document_type}.xml",
                    storage_uri=f"embedded://{document_type}",
                    content_hash=content_hash,
                    created_at="",
                )
            )
        return documents

    def _parse_xml1(self, xml1_root: ET.Element) -> ParsedClaim:
        if xml1_root.tag == "TONG_HOP":
            return self._parse_xml1_tong_hop(xml1_root)

        claim_id = self._required_text(xml1_root, "THONGTINHOSO/MA_HOSO")
        total_amount = self._to_decimal(self._required_text(xml1_root, "THONGTINHOSO/TONG_TIEN"))
        insurance_amount = self._to_decimal(
            self._required_text(xml1_root, "THONGTINHOSO/TIEN_BHYT")
        )
        patient_pay_amount = self._to_decimal(
            self._required_text(xml1_root, "THONGTINHOSO/TIEN_NGUOIBENH")
        )

        header = ClaimHeader(
            claim_id=claim_id,
            facility_id=self._required_text(xml1_root, "THONGTINHOSO/MA_CSKCB"),
            patient_id=self._required_text(xml1_root, "THONGTINHOSO/MA_NGUOIBENH"),
            insurance_card_no=self._required_text(xml1_root, "THONGTINHOSO/MA_THE"),
            visit_type=self._required_text(xml1_root, "THONGTINHOSO/LOAI_KCB"),
            admission_time=self._required_text(xml1_root, "THONGTINHOSO/NGAY_VAO"),
            discharge_time=self._required_text(xml1_root, "THONGTINHOSO/NGAY_RA"),
            primary_diagnosis_code=self._required_text(xml1_root, "THONGTINHOSO/MA_BENH"),
            route_code=self._required_text(xml1_root, "THONGTINHOSO/MA_TUYEN"),
            total_amount=total_amount,
            insurance_amount=insurance_amount,
            patient_pay_amount=patient_pay_amount,
            claim_effective_date=self._normalize_claim_effective_date(
                self._required_text(xml1_root, "THONGTINHOSO/NGAY_RA")
            ),
        )

        lines: list[ClaimLine] = []
        for line_el in xml1_root.findall(".//DSACH_CHI_TIET/CHI_TIET"):
            line = ClaimLine(
                line_id=self._required_text_from(line_el, "MA_DONG"),
                claim_id=claim_id,
                line_type=self._required_text_from(line_el, "LOAI_DONG"),
                item_code=self._required_text_from(line_el, "MA_DICH_VU"),
                item_name=self._required_text_from(line_el, "TEN_DICH_VU"),
                quantity=self._to_decimal(self._required_text_from(line_el, "SO_LUONG")),
                unit_price=self._to_decimal(self._required_text_from(line_el, "DON_GIA")),
                amount=self._to_decimal(self._required_text_from(line_el, "THANH_TIEN")),
                execution_time=line_el.findtext("NGAY_YL"),
                ordering_time=line_el.findtext("NGAY_TH"),
                department_code=line_el.findtext("MA_KHOA"),
                practitioner_id=line_el.findtext("MA_BS"),
                equipment_ref=line_el.findtext("MA_MAY"),
                source_xml="XML1",
                source_node_path="DSACH_CHI_TIET/CHI_TIET",
            )
            lines.append(line)

        return ParsedClaim(header=header, lines=lines)

    def _parse_xml1_tong_hop(self, xml1_root: ET.Element) -> ParsedClaim:
        claim_id = self._required_text(xml1_root, "MA_LK")
        total_amount = self._to_decimal(self._required_text(xml1_root, "T_TONGCHI_BV"))
        insurance_amount = self._to_decimal(self._required_text(xml1_root, "T_BHTT"))
        patient_pay_amount = self._to_decimal(self._required_text(xml1_root, "T_BNCCT"))

        header = ClaimHeader(
            claim_id=claim_id,
            facility_id=self._required_text(xml1_root, "MA_CSKCB"),
            patient_id=self._required_text(xml1_root, "MA_BN"),
            insurance_card_no=self._required_text(xml1_root, "MA_THE_BHYT"),
            visit_type=self._required_text(xml1_root, "MA_LOAI_KCB"),
            admission_time=self._required_text(xml1_root, "NGAY_VAO"),
            discharge_time=self._required_text(xml1_root, "NGAY_RA"),
            primary_diagnosis_code=self._required_text(xml1_root, "MA_BENH_CHINH"),
            route_code=self._required_text(xml1_root, "MA_DOITUONG_KCB"),
            total_amount=total_amount,
            insurance_amount=insurance_amount,
            patient_pay_amount=patient_pay_amount,
            claim_effective_date=self._normalize_claim_effective_date(
                self._required_text(xml1_root, "NGAY_RA")
            ),
            secondary_diagnosis_codes=self._split_semicolon_values(
                self._required_text(xml1_root, "MA_BENH_KT")
            ),
        )

        return ParsedClaim(header=header, lines=[])

    def _parse_xml2(self, xml2_root: ET.Element, parsed_claim: ParsedClaim) -> list[ClaimLine]:
        lines: list[ClaimLine] = []
        for line_el in xml2_root.findall(".//DSACH_CHI_TIET_THUOC/CHI_TIET_THUOC"):
            line = ClaimLine(
                line_id=f"XML2-{self._required_text_from(line_el, 'STT')}",
                claim_id=parsed_claim.header.claim_id,
                line_type="drug",
                item_code=self._required_text_from(line_el, "MA_THUOC"),
                item_name=self._required_text_from(line_el, "TEN_THUOC"),
                quantity=self._to_decimal(self._required_text_from(line_el, "SO_LUONG")),
                unit_price=self._to_decimal(self._required_text_from(line_el, "DON_GIA")),
                amount=self._to_decimal(self._required_text_from(line_el, "THANH_TIEN_BV")),
                execution_time=line_el.findtext("NGAY_YL"),
                ordering_time=line_el.findtext("NGAY_TH_YL"),
                department_code=line_el.findtext("MA_KHOA"),
                practitioner_id=line_el.findtext("MA_BAC_SI"),
                equipment_ref=line_el.findtext("MA_MAY"),
                source_xml="XML2",
                source_node_path="DSACH_CHI_TIET_THUOC/CHI_TIET_THUOC",
            )
            lines.append(line)
        return lines

    def _parse_xml3(self, xml3_root: ET.Element, parsed_claim: ParsedClaim) -> list[ClaimLine]:
        lines: list[ClaimLine] = []
        for line_el in xml3_root.findall(".//DSACH_CHI_TIET_DVKT/CHI_TIET_DVKT"):
            ma_dich_vu = (line_el.findtext("MA_DICH_VU") or "").strip()
            ma_vat_tu = (line_el.findtext("MA_VAT_TU") or "").strip()
            item_code = ma_dich_vu or ma_vat_tu
            if not item_code:
                raise ParseError("PARSER.LINE.FIELD.REQUIRED", "Thieu truong dong chi phi: MA_DICH_VU/MA_VAT_TU")
            line_type = "supply" if ma_vat_tu else "service"
            practitioner_id = (
                line_el.findtext("NGUOI_THUC_HIEN")
                or line_el.findtext("MA_BAC_SI")
            )
            item_name = (
                (line_el.findtext("TEN_DICH_VU") or "").strip()
                or (line_el.findtext("TEN_VAT_TU") or "").strip()
            )
            if not item_name:
                raise ParseError("PARSER.LINE.FIELD.REQUIRED", "Thieu truong dong chi phi: TEN_DICH_VU/TEN_VAT_TU")
            line = ClaimLine(
                line_id=f"XML3-{self._required_text_from(line_el, 'STT')}",
                claim_id=parsed_claim.header.claim_id,
                line_type=line_type,
                item_code=item_code,
                item_name=item_name,
                quantity=self._to_decimal(self._required_text_from(line_el, "SO_LUONG")),
                unit_price=self._to_decimal(self._required_text_from(line_el, "DON_GIA_BV")),
                amount=self._to_decimal(self._required_text_from(line_el, "THANH_TIEN_BV")),
                execution_time=line_el.findtext("NGAY_YL"),
                ordering_time=line_el.findtext("NGAY_TH_YL"),
                department_code=line_el.findtext("MA_KHOA"),
                practitioner_id=practitioner_id,
                equipment_ref=line_el.findtext("MA_MAY"),
                source_xml="XML3",
                source_node_path="DSACH_CHI_TIET_DVKT/CHI_TIET_DVKT",
            )
            lines.append(line)
        return lines

    def _parse_xml4(
        self,
        xml4_root: ET.Element,
        parsed_claim: ParsedClaim,
    ) -> list[ClinicalResult]:
        results: list[ClinicalResult] = []
        for line_el in xml4_root.findall(".//DSACH_CHI_TIET_CLS/CHI_TIET_CLS"):
            results.append(
                ClinicalResult(
                    result_id=f"XML4-{self._required_text_from(line_el, 'STT')}",
                    claim_id=parsed_claim.header.claim_id,
                    service_code=self._required_text_from(line_el, "MA_DICH_VU"),
                    indicator_code=self._optional_text_from(line_el, "MA_CHI_SO"),
                    indicator_name=self._optional_text_from(line_el, "TEN_CHI_SO"),
                    value=self._optional_text_from(line_el, "GIA_TRI"),
                    unit=self._optional_text_from(line_el, "DON_VI_DO"),
                    description=self._optional_text_from(line_el, "MO_TA"),
                    conclusion=self._optional_text_from(line_el, "KET_LUAN"),
                    result_time=self._optional_text_from(line_el, "NGAY_KQ"),
                    practitioner_id=self._optional_text_from(line_el, "MA_BS_DOC_KQ"),
                    source_xml="XML4",
                    source_node_path="DSACH_CHI_TIET_CLS/CHI_TIET_CLS",
                )
            )
        return results

    def _parse_xml5(
        self,
        xml5_root: ET.Element,
        parsed_claim: ParsedClaim,
    ) -> list[ClinicalNote]:
        notes: list[ClinicalNote] = []
        for line_el in xml5_root.findall(".//DSACH_CHI_TIET_DIEN_BIEN_BENH/CHI_TIET_DIEN_BIEN_BENH"):
            notes.append(
                ClinicalNote(
                    note_id=f"XML5-{self._required_text_from(line_el, 'STT')}",
                    claim_id=parsed_claim.header.claim_id,
                    note_text=self._required_text_from(line_el, "DIEN_BIEN_LS"),
                    disease_stage=self._optional_text_from(line_el, "GIAI_DOAN_BENH"),
                    consultation=self._optional_text_from(line_el, "HOI_CHAN"),
                    surgery=self._optional_text_from(line_el, "PHAU_THUAT"),
                    note_time=self._optional_text_from(line_el, "THOI_DIEM_DBLS"),
                    practitioner_id=self._optional_text_from(line_el, "NGUOI_THUC_HIEN"),
                    source_xml="XML5",
                    source_node_path="DSACH_CHI_TIET_DIEN_BIEN_BENH/CHI_TIET_DIEN_BIEN_BENH",
                )
            )
        return notes

    def _to_xml5_note_record(
        self,
        parsed_claim: ParsedClaim,
        note: ClinicalNote,
        source_file_name: str,
    ) -> XML5NoteRecord:
        normalized_text = self._normalize_clinical_text(note.note_text)
        linked_lines = self._link_note_to_lines(parsed_claim, note, normalized_text)
        linked_results = self._link_note_to_results(parsed_claim, note)
        recorded_date = self._normalize_optional_date(note.note_time)
        return XML5NoteRecord(
            schema_version=self.XML5_SCHEMA_VERSION,
            claim_id=parsed_claim.header.claim_id,
            note_id=note.note_id,
            source_file_type="XML5",
            source_file_name=source_file_name,
            facility_id=parsed_claim.header.facility_id,
            patient_id=parsed_claim.header.patient_id,
            encounter_id=parsed_claim.header.claim_id,
            department_code=self._select_note_department_code(linked_lines),
            department_name=None,
            practitioner_id=note.practitioner_id,
            practitioner_name=None,
            recorded_at=note.note_time,
            recorded_date=recorded_date,
            admission_time=parsed_claim.header.admission_time,
            discharge_time=parsed_claim.header.discharge_time,
            primary_diagnosis_code=parsed_claim.header.primary_diagnosis_code or None,
            primary_diagnosis_text=None,
            secondary_diagnosis_codes=list(parsed_claim.header.secondary_diagnosis_codes),
            secondary_diagnosis_texts=[],
            clinical_text=note.note_text,
            clinical_text_normalized=normalized_text,
            note_type=self._infer_note_type(normalized_text),
            context_tags=self._extract_context_tags(normalized_text),
            linked_line_ids=[line.line_id for line in linked_lines],
            linked_item_codes=self._dedupe_preserve_order([line.item_code for line in linked_lines if line.item_code]),
            linked_result_ids=[result.result_id for result in linked_results],
            evidence_flags=self._build_evidence_flags(normalized_text),
            parser_version=self.XML5_PARSER_VERSION,
            raw_ref=XML5RawRef(
                file_hoso_id="XML5",
                xml_node_path=note.source_node_path,
            ),
        )

    def _required_text(self, root: ET.Element, path: str) -> str:
        value = root.findtext(path)
        if value is None or not value.strip():
            raise ParseError("PARSER.FIELD.REQUIRED", f"Thieu truong bat buoc: {path}")
        return value.strip()

    def _required_text_from(self, root: ET.Element, path: str) -> str:
        value = root.findtext(path)
        if value is None or not value.strip():
            raise ParseError("PARSER.LINE.FIELD.REQUIRED", f"Thieu truong dong chi phi: {path}")
        return value.strip()

    def _optional_text_from(self, root: ET.Element, path: str) -> str | None:
        value = root.findtext(path)
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def _to_decimal(self, raw_value: str) -> Decimal:
        normalized = raw_value.strip().replace(",", "")
        return Decimal(normalized)

    def _split_semicolon_values(self, raw_value: str) -> list[str]:
        return [item.strip() for item in raw_value.split(";") if item.strip()]

    def _normalize_clinical_text(self, raw_value: str) -> str:
        normalized = unicodedata.normalize("NFC", raw_value or "")
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def _normalize_match_text(self, raw_value: str | None) -> str:
        normalized = unicodedata.normalize("NFD", (raw_value or "").strip().lower())
        normalized = normalized.replace("\u0111", "d")
        normalized = "".join(character for character in normalized if unicodedata.category(character) != "Mn")
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def _normalize_optional_date(self, raw_value: str | None) -> str | None:
        if not raw_value:
            return None
        try:
            return self._normalize_claim_effective_date(raw_value)
        except ParseError:
            return None

    def _extract_context_tags(self, normalized_text: str) -> list[str]:
        normalized_match_text = self._normalize_match_text(normalized_text)
        tags: list[str] = []
        for tag, keywords in self._XML5_CONTEXT_KEYWORDS.items():
            if any(
                keyword in normalized_match_text and not self._is_negated_keyword(normalized_match_text, keyword)
                for keyword in keywords
            ):
                tags.append(tag)
        return tags

    def _infer_note_type(self, normalized_text: str) -> str:
        normalized_match_text = self._normalize_match_text(normalized_text)
        for note_type, keywords in self._NOTE_TYPE_KEYWORDS.items():
            if any(keyword in normalized_match_text for keyword in keywords):
                return note_type
        return "unknown"

    def _build_evidence_flags(self, normalized_text: str) -> XML5EvidenceFlags:
        normalized_match_text = self._normalize_match_text(normalized_text)
        return XML5EvidenceFlags(
            has_diagnosis_context="chan doan" in normalized_match_text,
            has_treatment_context=any(
                keyword in normalized_match_text
                for keyword in ("dieu tri", "y lenh", "thuoc", "truyen")
            ),
            has_procedure_context=any(
                keyword in normalized_match_text for keyword in ("thu thuat", "phau thuat")
            ),
            has_lab_context=any(
                keyword in normalized_match_text for keyword in ("xet nghiem", "bach cau", "ure", "creatinin")
            ),
            has_imaging_context=any(
                keyword in normalized_match_text for keyword in ("x-quang", "x quang", "sieu am", "ct", "mri")
            ),
        )

    def _select_note_department_code(self, linked_lines: list[ClaimLine]) -> str | None:
        for line in linked_lines:
            if line.department_code:
                return line.department_code
        return None

    def _link_note_to_lines(
        self,
        parsed_claim: ParsedClaim,
        note: ClinicalNote,
        normalized_text: str,
    ) -> list[ClaimLine]:
        note_time_digits = self._digits_only(note.note_time)
        normalized_match_text = self._normalize_match_text(normalized_text)
        is_administrative_note = self._is_administrative_note(normalized_match_text)
        note_has_drug_signal = any(
            keyword in normalized_match_text
            for keyword in ("thuoc", "khang sinh", "hoa chat", "truyen", "uong")
        )
        note_has_service_signal = any(
            keyword in normalized_match_text
            for keyword in ("xet nghiem", "sieu am", "x quang", "dien tim", "thu thuat")
        )
        note_has_supply_signal = any(
            keyword in normalized_match_text
            for keyword in ("vat tu", "sonde", "mo thong", "bang", "ong")
        )
        scored_lines: list[tuple[int, ClaimLine]] = []
        for line in parsed_claim.lines:
            score = 0
            direct_match = False
            if note.practitioner_id and line.practitioner_id == note.practitioner_id:
                score += 2
            line_time_digits = self._digits_only(line.execution_time or line.ordering_time)
            if note_time_digits and line_time_digits and note_time_digits[:8] == line_time_digits[:8]:
                score += 1
            if line.item_code and self._normalize_match_text(line.item_code) in normalized_match_text:
                score += 6
                direct_match = True
            if line.item_name and self._normalize_match_text(line.item_name) in normalized_match_text:
                score += 6
                direct_match = True
            if line.line_type == "drug" and note_has_drug_signal:
                score += 2
            if line.line_type == "service" and note_has_service_signal:
                score += 2
            if line.line_type == "supply" and note_has_supply_signal:
                score += 2
            if is_administrative_note and score < 5:
                continue
            if not is_administrative_note and not direct_match and score < 4:
                continue
            if not is_administrative_note and not direct_match and score < 5 and not (
                (line.line_type == "drug" and note_has_drug_signal)
                or (line.line_type == "service" and note_has_service_signal)
                or (line.line_type == "supply" and note_has_supply_signal)
            ):
                continue
            if score >= 4:
                scored_lines.append((score, line))
        scored_lines.sort(
            key=lambda item: (
                -item[0],
                abs(self._time_distance_minutes(note.note_time, item[1].execution_time or item[1].ordering_time)),
            )
        )
        max_links = 3 if is_administrative_note else 5
        return [line for _, line in scored_lines[:max_links]]

    def _link_note_to_results(
        self,
        parsed_claim: ParsedClaim,
        note: ClinicalNote,
    ) -> list[ClinicalResult]:
        note_time_digits = self._digits_only(note.note_time)
        normalized_match_text = self._normalize_match_text(note.note_text)
        if self._is_administrative_note(normalized_match_text):
            return []
        note_has_result_signal = any(
            keyword in normalized_match_text for keyword in ("xet nghiem", "ket qua", "cls", "chi so")
        )
        scored_results: list[tuple[int, ClinicalResult]] = []
        for result in parsed_claim.clinical_results:
            score = 0
            direct_match = False
            if result.practitioner_id and note.practitioner_id and result.practitioner_id == note.practitioner_id:
                score += 2
            result_time_digits = self._digits_only(result.result_time)
            if note_time_digits and result_time_digits and note_time_digits[:8] == result_time_digits[:8]:
                score += 1
            if result.service_code and self._normalize_match_text(result.service_code) in normalized_match_text:
                score += 5
                direct_match = True
            if result.indicator_name and self._normalize_match_text(result.indicator_name) in normalized_match_text:
                score += 5
                direct_match = True
            if note_has_result_signal:
                score += 2
            if not direct_match and score < 5:
                continue
            if score >= 5:
                scored_results.append((score, result))
        scored_results.sort(
            key=lambda item: (
                -item[0],
                abs(self._time_distance_minutes(note.note_time, item[1].result_time)),
            )
        )
        return [result for _, result in scored_results[:3]]

    def _digits_only(self, raw_value: str | None) -> str:
        return "".join(ch for ch in (raw_value or "") if ch.isdigit())

    def _dedupe_preserve_order(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result

    def _is_negated_keyword(self, normalized_text: str, keyword: str) -> bool:
        return any(
            f"{prefix} {keyword}" in normalized_text
            for prefix in ("khong", "chua", "ko")
        )

    def _is_administrative_note(self, normalized_match_text: str) -> bool:
        administrative_keywords = (
            "ra vien",
            "tai kham",
            "benh on dinh",
            "on dinh -> ra vien",
            "bo sung vat tu",
        )
        if any(keyword in normalized_match_text for keyword in administrative_keywords):
            return True
        clinical_signal_keywords = (
            "dau",
            "sot",
            "xet nghiem",
            "thuoc",
            "hoa chat",
            "phau thuat",
            "thu thuat",
            "non",
            "an kem",
        )
        return (
            "chan doan" in normalized_match_text
            and not any(keyword in normalized_match_text for keyword in clinical_signal_keywords)
        )

    def _time_distance_minutes(self, left: str | None, right: str | None) -> int:
        left_digits = self._digits_only(left)
        right_digits = self._digits_only(right)
        if len(left_digits) < 12 or len(right_digits) < 12:
            return 10**9
        try:
            left_value = int(left_digits[:12])
            right_value = int(right_digits[:12])
        except ValueError:
            return 10**9
        return abs(left_value - right_value)

    def _normalize_claim_effective_date(self, raw_value: str) -> str:
        normalized = raw_value.strip()
        if len(normalized) >= 10 and normalized[4] == "-" and normalized[7] == "-":
            return normalized[:10]
        digits_only = "".join(ch for ch in normalized if ch.isdigit())
        if len(digits_only) >= 8:
            return f"{digits_only[:4]}-{digits_only[4:6]}-{digits_only[6:8]}"
        raise ParseError(
            "PARSER.DATE.INVALID",
            f"Khong the chuan hoa claim_effective_date tu gia tri: {raw_value}",
        )
