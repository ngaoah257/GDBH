from __future__ import annotations

import zipfile
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET

from claim_models import (
    DrugItem,
    EquipmentItem,
    MasterDataSnapshot,
    ServiceItem,
    StaffMember,
    SupplyItem,
)


class MasterDataService:
    """Doc snapshot danh muc co so tu cac file xlsx trong folder Danhmuc."""

    _NS = {
        "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
    }

    def __init__(self, catalog_dir: str | Path):
        self._catalog_dir = Path(catalog_dir)

    def load_snapshot(
        self,
        effective_date: str,
        facility_id: str | None = None,
    ) -> MasterDataSnapshot:
        staff_file = self._catalog_dir / "FileNhanVienYTe.xlsx"
        equipment_file = self._catalog_dir / "FileTrangThietBi.xlsx"
        service_file = self._catalog_dir / "FileDichVuBV.xlsx"
        drug_file = self._resolve_catalog_file(
            "FileDanhMucThuoc.xlsx",
            "FileThuoc.xlsx",
            "FileThuocBV.xlsx",
        )
        supply_file = self._resolve_catalog_file(
            "FileVatTuYTe.xlsx",
            "FileVTYT.xlsx",
            "FileDanhMucVTYT.xlsx",
            "FileVatTu.xlsx",
        )
        staff_members = self._load_staff_members(staff_file, effective_date)
        equipment_items = self._load_equipment_items(equipment_file, effective_date)
        service_items = self._load_service_items(service_file, effective_date)
        all_service_items = self._load_service_items(service_file, None)
        drug_items = self._load_drug_items(drug_file, effective_date)
        all_drug_items = self._load_drug_items(drug_file, None)
        supply_items = self._load_supply_items(supply_file, effective_date)
        all_supply_items = self._load_supply_items(supply_file, None)
        dataset_version = (
            "danhmuc:"
            f"{self._dataset_component(staff_file)}:"
            f"{self._dataset_component(equipment_file)}:"
            f"{self._dataset_component(service_file)}:"
            f"{self._dataset_component(drug_file)}:"
            f"{self._dataset_component(supply_file)}"
        )
        return MasterDataSnapshot(
            dataset_version=dataset_version,
            effective_date=effective_date,
            facility_id=facility_id,
            staff_members=staff_members,
            equipment_items=equipment_items,
            service_items=service_items,
            all_service_items=all_service_items,
            drug_items=drug_items,
            all_drug_items=all_drug_items,
            supply_items=supply_items,
            all_supply_items=all_supply_items,
        )

    def find_staff_by_practitioner_id(
        self,
        practitioner_id: str,
        effective_date: str,
    ) -> StaffMember | None:
        snapshot = self.load_snapshot(effective_date)
        for staff in snapshot.staff_members:
            if staff.practitioner_id == practitioner_id:
                return staff
        return None

    def _load_staff_members(self, file_path: Path, effective_date: str) -> list[StaffMember]:
        records = []
        for row in self._read_xlsx_rows(file_path):
            if not self._is_effective(row.get("TU_NGAY"), row.get("DEN_NGAY"), effective_date):
                continue
            practitioner_id = row.get("practitioner_id") or row.get("MA_BHXH") or row.get("ID")
            if not practitioner_id:
                continue
            records.append(
                StaffMember(
                    practitioner_id=practitioner_id,
                    practitioner_name=row.get("HO_TEN", ""),
                    department_code=row.get("MA_KHOA") or None,
                    department_name=row.get("TEN_KHOA") or None,
                    title_code=row.get("CHUCDANH_NN") or None,
                    license_code=row.get("MACCHN") or None,
                    practice_scope=row.get("PHAMVI_CM") or None,
                    extra_service_codes=self._split_semicolon_values(row.get("DVKT_KHAC", "")),
                    effective_from=self._normalize_excel_date(row.get("TU_NGAY")),
                    effective_to=self._normalize_excel_date(row.get("DEN_NGAY")),
                )
            )
        return records

    def _load_equipment_items(self, file_path: Path, effective_date: str) -> list[EquipmentItem]:
        records = []
        for row in self._read_xlsx_rows(file_path):
            if not self._is_effective(row.get("TU_NGAY"), row.get("DEN_NGAY"), effective_date):
                continue
            equipment_id = row.get("MA_MAY") or row.get("ID")
            if not equipment_id:
                continue
            records.append(
                EquipmentItem(
                    equipment_id=equipment_id,
                    equipment_name=row.get("TEN_TB", ""),
                    model_code=row.get("KY_HIEU") or None,
                    manufacturer=row.get("CONGTY_SX") or None,
                    country_of_origin=row.get("NUOC_SX") or None,
                    serial_or_asset_code=row.get("MA_MAY") or None,
                    license_code=row.get("SO_LUU_HANH") or None,
                    effective_from=self._normalize_excel_date(row.get("TU_NGAY")),
                    effective_to=self._normalize_excel_date(row.get("DEN_NGAY")),
                )
            )
        return records

    def _load_service_items(self, file_path: Path, effective_date: str | None) -> list[ServiceItem]:
        records = []
        for row in self._read_xlsx_rows(file_path):
            if effective_date is not None and not self._is_effective(
                row.get("TUNGAY"),
                row.get("DENNGAY"),
                effective_date,
            ):
                continue
            service_code = row.get("MA_TUONG_DUONG") or row.get("ID")
            if not service_code:
                continue
            records.append(
                ServiceItem(
                    service_code=service_code,
                    approved_name=row.get("TEN_DVKT_PHEDUYET", ""),
                    price_name=row.get("TEN_DVKT_GIA") or None,
                    unit_price=self._to_decimal(row.get("DON_GIA")),
                    decision_ref=row.get("QUYET_DINH") or None,
                    transfer_facilities=self._split_semicolon_values(row.get("CSKCB_CGKT", "")),
                    cls_facilities=self._split_semicolon_values(row.get("CSKCB_CLS", "")),
                    effective_from=self._normalize_excel_date(row.get("TUNGAY")),
                    effective_to=self._normalize_excel_date(row.get("DENNGAY")),
                )
            )
        return records

    def _load_drug_items(self, file_path: Path, effective_date: str | None) -> list[DrugItem]:
        records = []
        for row in self._read_xlsx_rows(file_path):
            if effective_date is not None and not self._is_effective(
                row.get("TUNGAY") or row.get("TU_NGAY"),
                row.get("DENNGAY") or row.get("DEN_NGAY"),
                effective_date,
            ):
                continue
            drug_code = (
                row.get("MA_THUOC")
                or row.get("MA_TUONG_DUONG")
                or row.get("MA_DUNG_CHUNG")
                or row.get("ID")
            )
            if not drug_code:
                continue
            records.append(
                DrugItem(
                    drug_code=drug_code,
                    drug_name=row.get("TEN_THUOC") or row.get("TEN_HOAT_CHAT", ""),
                    active_ingredient=row.get("TEN_HOAT_CHAT") or None,
                    dosage_form=row.get("DANG_BAO_CHE") or None,
                    strength=row.get("HAM_LUONG") or None,
                    unit_name=row.get("DON_VI_TINH") or row.get("TEN_DON_VI") or None,
                    unit_price=self._to_decimal(row.get("DON_GIA") or row.get("DON_GIA_BH")),
                    insurance_group_code=(
                        row.get("MA_NHOM_BHYT")
                        or row.get("LOAI_THUOC")
                        or row.get("NHOM_THUOC")
                        or None
                    ),
                    decision_ref=row.get("QUYET_DINH") or None,
                    effective_from=self._normalize_excel_date(row.get("TUNGAY") or row.get("TU_NGAY")),
                    effective_to=self._normalize_excel_date(row.get("DENNGAY") or row.get("DEN_NGAY")),
                )
            )
        return records

    def _load_supply_items(self, file_path: Path, effective_date: str | None) -> list[SupplyItem]:
        records = []
        for row in self._read_xlsx_rows(file_path):
            if effective_date is not None and not self._is_effective(
                row.get("TUNGAY") or row.get("TU_NGAY"),
                row.get("DENNGAY") or row.get("DEN_NGAY") or row.get("DEN_NGAY_HD"),
                effective_date,
            ):
                continue
            supply_code = (
                row.get("MA_VAT_TU")
                or row.get("MA_TUONG_DUONG")
                or row.get("MA_DUNG_CHUNG")
                or row.get("ID")
            )
            if not supply_code:
                continue
            records.append(
                SupplyItem(
                    supply_code=supply_code,
                    supply_name=row.get("TEN_VAT_TU") or row.get("TEN_VTYT", ""),
                    unit_name=row.get("DON_VI_TINH") or row.get("TEN_DON_VI") or None,
                    unit_price=self._to_decimal(row.get("DON_GIA") or row.get("DON_GIA_BH")),
                    insurance_group_code=(
                        row.get("MA_NHOM_BHYT")
                        or row.get("NHOM_VAT_TU")
                        or row.get("NHOM_VTYT")
                        or None
                    ),
                    decision_ref=row.get("QUYET_DINH") or None,
                    effective_from=self._normalize_excel_date(row.get("TUNGAY") or row.get("TU_NGAY")),
                    effective_to=self._normalize_excel_date(
                        row.get("DENNGAY") or row.get("DEN_NGAY") or row.get("DEN_NGAY_HD")
                    ),
                )
            )
        return records

    def _read_xlsx_rows(self, file_path: Path) -> list[dict[str, str]]:
        if not file_path.exists():
            return []
        with zipfile.ZipFile(file_path) as archive:
            shared_strings = self._read_shared_strings(archive)
            sheet_target = self._get_first_sheet_target(archive)
            sheet = ET.fromstring(archive.read(f"xl/{sheet_target}"))
            rows = sheet.findall(".//a:sheetData/a:row", self._NS)
            if not rows:
                return []
            header = self._row_values(rows[0], shared_strings)
            records: list[dict[str, str]] = []
            for row in rows[1:]:
                values = self._row_values(row, shared_strings)
                if not any(values):
                    continue
                padded_values = values + [""] * (len(header) - len(values))
                records.append(dict(zip(header, padded_values)))
            return records

    def _row_values(self, row: ET.Element, shared_strings: list[str]) -> list[str]:
        values_by_index: dict[int, str] = {}
        max_index = -1
        for cell in row.findall("a:c", self._NS):
            ref = cell.attrib.get("r", "")
            column_index = self._column_index_from_ref(ref)
            values_by_index[column_index] = self._cell_value(cell, shared_strings)
            if column_index > max_index:
                max_index = column_index
        if max_index < 0:
            return []
        return [values_by_index.get(index, "") for index in range(max_index + 1)]

    def _column_index_from_ref(self, ref: str) -> int:
        letters = "".join(character for character in ref if character.isalpha()).upper()
        if not letters:
            return 0
        index = 0
        for character in letters:
            index = index * 26 + (ord(character) - ord("A") + 1)
        return index - 1

    def _read_shared_strings(self, archive: zipfile.ZipFile) -> list[str]:
        if "xl/sharedStrings.xml" not in archive.namelist():
            return []
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        values = []
        for si in root.findall("a:si", self._NS):
            texts = [node.text or "" for node in si.findall(".//a:t", self._NS)]
            values.append("".join(texts))
        return values

    def _get_first_sheet_target(self, archive: zipfile.ZipFile) -> str:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_map = {
            rel.attrib["Id"]: rel.attrib["Target"].replace("\\", "/")
            for rel in rels.findall("pr:Relationship", self._NS)
        }
        first_sheet = next(iter(workbook.find("a:sheets", self._NS)))
        rel_id = first_sheet.attrib[
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        ]
        return rel_map[rel_id]

    def _cell_value(self, cell: ET.Element, shared_strings: list[str]) -> str:
        value_node = cell.find("a:v", self._NS)
        if value_node is None:
            return ""
        value = value_node.text or ""
        if cell.attrib.get("t") == "s" and value:
            return shared_strings[int(value)]
        return value

    def _is_effective(
        self,
        from_value: str | None,
        to_value: str | None,
        effective_date: str,
    ) -> bool:
        normalized_from = self._normalize_excel_date(from_value)
        normalized_to = self._normalize_excel_date(to_value)
        if normalized_from and effective_date < normalized_from:
            return False
        if normalized_to and effective_date > normalized_to:
            return False
        return True

    def _normalize_excel_date(self, value: str | None) -> str | None:
        if value is None:
            return None
        raw = value.strip()
        if not raw:
            return None
        if len(raw) == 8 and raw.isdigit():
            return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
        return raw

    def _split_semicolon_values(self, value: str) -> list[str]:
        return [item.strip() for item in value.split(";") if item.strip()]

    def _to_decimal(self, value: str | None) -> Decimal:
        if value is None:
            return Decimal("0")
        raw = value.strip().replace(",", "")
        if not raw:
            return Decimal("0")
        return Decimal(raw)

    def _resolve_catalog_file(self, *candidate_names: str) -> Path:
        for candidate_name in candidate_names:
            candidate = self._catalog_dir / candidate_name
            if candidate.exists():
                return candidate
        return self._catalog_dir / candidate_names[0]

    def _dataset_component(self, file_path: Path) -> str:
        if not file_path.exists():
            return f"missing:{file_path.name}"
        return f"{file_path.name}@{file_path.stat().st_mtime_ns}"
