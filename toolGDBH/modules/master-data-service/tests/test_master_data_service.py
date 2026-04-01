from __future__ import annotations

import os
from pathlib import Path

import pytest

from master_data_service import MasterDataService


CATALOG_DIR = Path(
    os.getenv("TOOLGDBH_CATALOG_DIR", Path(__file__).resolve().parents[4] / "Danhmuc")
)


def _require_catalog_dir() -> Path:
    if not CATALOG_DIR.exists():
        pytest.skip(f"Khong tim thay Danhmuc de test: {CATALOG_DIR}")
    return CATALOG_DIR


def test_master_data_service_should_load_staff_equipment_and_service_snapshot() -> None:
    service = MasterDataService(_require_catalog_dir())

    snapshot = service.load_snapshot("2026-03-30", facility_id="79001")

    assert snapshot.facility_id == "79001"
    assert snapshot.staff_members
    assert snapshot.equipment_items
    assert snapshot.service_items
    assert snapshot.all_service_items
    assert len(snapshot.all_service_items) >= len(snapshot.service_items)


def test_master_data_service_should_find_staff_by_practitioner_id() -> None:
    service = MasterDataService(_require_catalog_dir())

    staff = service.find_staff_by_practitioner_id("3820222623", "2026-03-30")

    assert staff is not None
    assert staff.department_code == "K02"


def test_master_data_service_should_load_drug_and_supply_items_from_catalog_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for file_name in [
        "FileNhanVienYTe.xlsx",
        "FileTrangThietBi.xlsx",
        "FileDichVuBV.xlsx",
        "FileThuoc.xlsx",
        "FileVatTuYTe.xlsx",
    ]:
        (tmp_path / file_name).write_bytes(b"stub")

    service = MasterDataService(tmp_path)

    def fake_read_xlsx_rows(file_path: Path) -> list[dict[str, str]]:
        if file_path.name == "FileThuoc.xlsx":
            return [
                {
                    "MA_THUOC": "TH001",
                    "TEN_THUOC": "Paracetamol 500mg",
                    "TEN_HOAT_CHAT": "Paracetamol",
                    "DANG_BAO_CHE": "Vien",
                    "HAM_LUONG": "500mg",
                    "DON_VI_TINH": "Vien",
                    "DON_GIA": "1200",
                    "MA_NHOM_BHYT": "N1",
                    "QUYET_DINH": "QD-THUOC",
                    "TUNGAY": "20250101",
                    "DENNGAY": "20261231",
                }
            ]
        if file_path.name == "FileVatTuYTe.xlsx":
            return [
                {
                    "MA_VAT_TU": "VT001",
                    "TEN_VAT_TU": "Kim tiem",
                    "DON_VI_TINH": "Cai",
                    "DON_GIA": "3500",
                    "MA_NHOM_BHYT": "VT1",
                    "QUYET_DINH": "QD-VTYT",
                    "TUNGAY": "20250101",
                    "DENNGAY": "20261231",
                }
            ]
        return []

    monkeypatch.setattr(service, "_read_xlsx_rows", fake_read_xlsx_rows)

    snapshot = service.load_snapshot("2026-03-30", facility_id="79001")

    assert len(snapshot.drug_items) == 1
    assert snapshot.drug_items[0].drug_code == "TH001"
    assert snapshot.drug_items[0].active_ingredient == "Paracetamol"
    assert len(snapshot.supply_items) == 1
    assert snapshot.supply_items[0].supply_code == "VT001"
    assert snapshot.supply_items[0].unit_price == 3500


def test_master_data_service_should_prefer_filedanhmucthuoc_and_map_group_and_price_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for file_name in [
        "FileNhanVienYTe.xlsx",
        "FileTrangThietBi.xlsx",
        "FileDichVuBV.xlsx",
        "FileDanhMucThuoc.xlsx",
        "FileVatTuYTe.xlsx",
    ]:
        (tmp_path / file_name).write_bytes(b"stub")

    service = MasterDataService(tmp_path)

    def fake_read_xlsx_rows(file_path: Path) -> list[dict[str, str]]:
        if file_path.name == "FileDanhMucThuoc.xlsx":
            return [
                {
                    "MA_THUOC": "40.27",
                    "TEN_THUOC": "CRESIMEX 5mg",
                    "TEN_HOAT_CHAT": "Aescin",
                    "DANG_BAO_CHE": "Vien",
                    "HAM_LUONG": "5mg",
                    "DON_VI_TINH": "Vien",
                    "DON_GIA": "",
                    "DON_GIA_BH": "68000",
                    "LOAI_THUOC": "1",
                    "TU_NGAY": "20250506",
                    "DEN_NGAY": "20260505",
                }
            ]
        return []

    monkeypatch.setattr(service, "_read_xlsx_rows", fake_read_xlsx_rows)

    snapshot = service.load_snapshot("2026-03-30", facility_id="79001")

    assert len(snapshot.drug_items) == 1
    assert snapshot.drug_items[0].drug_code == "40.27"
    assert snapshot.drug_items[0].insurance_group_code == "1"
    assert snapshot.drug_items[0].unit_price == 68000
    assert snapshot.drug_items[0].effective_from == "2025-05-06"
    assert snapshot.drug_items[0].effective_to == "2026-05-05"


def test_master_data_service_should_map_supply_group_price_and_effective_date_fallbacks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for file_name in [
        "FileNhanVienYTe.xlsx",
        "FileTrangThietBi.xlsx",
        "FileDichVuBV.xlsx",
        "FileDanhMucThuoc.xlsx",
        "FileVatTuYTe.xlsx",
    ]:
        (tmp_path / file_name).write_bytes(b"stub")

    service = MasterDataService(tmp_path)

    def fake_read_xlsx_rows(file_path: Path) -> list[dict[str, str]]:
        if file_path.name == "FileVatTuYTe.xlsx":
            return [
                {
                    "MA_VAT_TU": "N03.01.010",
                    "TEN_VAT_TU": "Bom thuc an",
                    "DON_VI_TINH": "Cai",
                    "DON_GIA": "",
                    "DON_GIA_BH": "2700",
                    "NHOM_VAT_TU": "N03",
                    "TU_NGAY": "20260120",
                    "DEN_NGAY_HD": "20261231",
                }
            ]
        return []

    monkeypatch.setattr(service, "_read_xlsx_rows", fake_read_xlsx_rows)

    snapshot = service.load_snapshot("2026-03-30", facility_id="79001")

    assert len(snapshot.supply_items) == 1
    assert snapshot.supply_items[0].supply_code == "N03.01.010"
    assert snapshot.supply_items[0].insurance_group_code == "N03"
    assert snapshot.supply_items[0].unit_price == 2700
    assert snapshot.supply_items[0].effective_from == "2026-01-20"
    assert snapshot.supply_items[0].effective_to == "2026-12-31"


def test_master_data_service_should_map_service_code_price_and_effective_dates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for file_name in [
        "FileNhanVienYTe.xlsx",
        "FileTrangThietBi.xlsx",
        "FileDichVuBV.xlsx",
        "FileDanhMucThuoc.xlsx",
        "FileVatTuYTe.xlsx",
    ]:
        (tmp_path / file_name).write_bytes(b"stub")

    service = MasterDataService(tmp_path)

    def fake_read_xlsx_rows(file_path: Path) -> list[dict[str, str]]:
        if file_path.name == "FileDichVuBV.xlsx":
            return [
                {
                    "MA_TUONG_DUONG": "02.1900",
                    "TEN_DVKT_PHEDUYET": "Hoi chan chuyen nganh Noi",
                    "TEN_DVKT_GIA": "Hoi chan chuyen nganh Noi",
                    "DON_GIA": "200000",
                    "QUYET_DINH": "QD-DV",
                    "TUNGAY": "20170901",
                    "DENNGAY": "",
                    "CSKCB_CGKT": "79001;79002",
                    "CSKCB_CLS": "79003",
                }
            ]
        return []

    monkeypatch.setattr(service, "_read_xlsx_rows", fake_read_xlsx_rows)

    snapshot = service.load_snapshot("2026-03-30", facility_id="79001")

    assert len(snapshot.service_items) == 1
    assert snapshot.service_items[0].service_code == "02.1900"
    assert snapshot.service_items[0].approved_name == "Hoi chan chuyen nganh Noi"
    assert snapshot.service_items[0].price_name == "Hoi chan chuyen nganh Noi"
    assert snapshot.service_items[0].unit_price == 200000
    assert snapshot.service_items[0].effective_from == "2017-09-01"
    assert snapshot.service_items[0].effective_to is None
    assert snapshot.service_items[0].transfer_facilities == ["79001", "79002"]
    assert snapshot.service_items[0].cls_facilities == ["79003"]
