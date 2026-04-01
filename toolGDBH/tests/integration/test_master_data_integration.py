from __future__ import annotations

import base64
import os
from pathlib import Path
from textwrap import dedent

import pytest

from deterministic_rule_engine import DeterministicRuleEngine
from master_data_service import MasterDataService
from parser_normalizer import ParserNormalizerService
from rule_registry import RuleRegistry


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CATALOG_DIR = Path(os.getenv("TOOLGDBH_CATALOG_DIR", PROJECT_ROOT / "Danhmuc"))
RULE_FILE = PROJECT_ROOT / "modules" / "rule-registry" / "config" / "rules.mwp.json"


def _require_catalog_dir() -> Path:
    if not CATALOG_DIR.exists():
        pytest.skip(f"Khong tim thay Danhmuc de test integration: {CATALOG_DIR}")
    return CATALOG_DIR


def _build_giamdinhhs(xml1_text: str) -> str:
    encoded = base64.b64encode(xml1_text.encode("utf-8")).decode("ascii")
    return dedent(
        f"""\
        <GIAMDINHHS>
          <DANHSACHHOSO>
            <FILEHOSO>
              <LOAIHOSO>XML1</LOAIHOSO>
              <NOIDUNGFILE>{encoded}</NOIDUNGFILE>
            </FILEHOSO>
          </DANHSACHHOSO>
        </GIAMDINHHS>
        """
    )


def test_pipeline_should_not_flag_practitioner_exists_when_practitioner_is_in_catalog() -> None:
    xml1 = dedent(
        """\
        <XML1>
          <THONGTINHOSO>
            <MA_HOSO>HSREAL001</MA_HOSO>
            <MA_CSKCB>79001</MA_CSKCB>
            <MA_NGUOIBENH>PNREAL001</MA_NGUOIBENH>
            <MA_THE>THE001</MA_THE>
            <LOAI_KCB>inpatient</LOAI_KCB>
            <NGAY_VAO>2026-03-28T08:00:00</NGAY_VAO>
            <NGAY_RA>2026-03-29T10:00:00</NGAY_RA>
            <MA_BENH>A09</MA_BENH>
            <MA_TUYEN>01</MA_TUYEN>
            <TONG_TIEN>200000</TONG_TIEN>
            <TIEN_BHYT>160000</TIEN_BHYT>
            <TIEN_NGUOIBENH>40000</TIEN_NGUOIBENH>
          </THONGTINHOSO>
          <DSACH_CHI_TIET>
            <CHI_TIET>
              <MA_DONG>L001</MA_DONG>
              <LOAI_DONG>service</LOAI_DONG>
              <MA_DICH_VU>02.1900</MA_DICH_VU>
              <TEN_DICH_VU>Hoi chan ca benh kho chuyen nganh Noi</TEN_DICH_VU>
              <SO_LUONG>1</SO_LUONG>
              <DON_GIA>200000</DON_GIA>
              <THANH_TIEN>200000</THANH_TIEN>
              <NGAY_YL>2026-03-28T08:00:00</NGAY_YL>
              <NGAY_TH>2026-03-28T08:30:00</NGAY_TH>
              <MA_KHOA>K02</MA_KHOA>
              <MA_BS>3820222623</MA_BS>
            </CHI_TIET>
          </DSACH_CHI_TIET>
        </XML1>
        """
    )

    claim = ParserNormalizerService().parse_text(_build_giamdinhhs(xml1))
    master_snapshot = MasterDataService(_require_catalog_dir()).load_snapshot("2026-03-30", facility_id="79001")
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)

    result = engine.evaluate(claim, "2026-03-30", master_snapshot=master_snapshot)

    assert all(hit.rule_id != "MASTER.PRACTITIONER_EXISTS.001" for hit in result.hits)
    assert all(hit.rule_id != "MASTER.PRACTITIONER_DEPARTMENT.001" for hit in result.hits)


def test_pipeline_should_not_flag_service_catalog_rules_for_known_effective_service() -> None:
    xml1 = dedent(
        """\
        <XML1>
          <THONGTINHOSO>
            <MA_HOSO>HSREAL002</MA_HOSO>
            <MA_CSKCB>79001</MA_CSKCB>
            <MA_NGUOIBENH>PNREAL002</MA_NGUOIBENH>
            <MA_THE>THE001</MA_THE>
            <LOAI_KCB>inpatient</LOAI_KCB>
            <NGAY_VAO>2026-03-28T08:00:00</NGAY_VAO>
            <NGAY_RA>2026-03-29T10:00:00</NGAY_RA>
            <MA_BENH>A09</MA_BENH>
            <MA_TUYEN>01</MA_TUYEN>
            <TONG_TIEN>200000</TONG_TIEN>
            <TIEN_BHYT>160000</TIEN_BHYT>
            <TIEN_NGUOIBENH>40000</TIEN_NGUOIBENH>
          </THONGTINHOSO>
          <DSACH_CHI_TIET>
            <CHI_TIET>
              <MA_DONG>L001</MA_DONG>
              <LOAI_DONG>service</LOAI_DONG>
              <MA_DICH_VU>02.1900</MA_DICH_VU>
              <TEN_DICH_VU>Hoi chan ca benh kho chuyen nganh Noi</TEN_DICH_VU>
              <SO_LUONG>1</SO_LUONG>
              <DON_GIA>200000</DON_GIA>
              <THANH_TIEN>200000</THANH_TIEN>
              <NGAY_YL>2026-03-28T08:00:00</NGAY_YL>
              <NGAY_TH>2026-03-28T08:30:00</NGAY_TH>
            </CHI_TIET>
          </DSACH_CHI_TIET>
        </XML1>
        """
    )

    claim = ParserNormalizerService().parse_text(_build_giamdinhhs(xml1))
    master_snapshot = MasterDataService(_require_catalog_dir()).load_snapshot("2026-03-30", facility_id="79001")
    registry = RuleRegistry.from_json_file(RULE_FILE)
    engine = DeterministicRuleEngine(registry)

    result = engine.evaluate(claim, "2026-03-30", master_snapshot=master_snapshot)

    assert all(hit.rule_id != "MASTER.ITEM_CODE.001" for hit in result.hits)
    assert all(hit.rule_id != "MASTER.ITEM_EFFECTIVE.001" for hit in result.hits)
