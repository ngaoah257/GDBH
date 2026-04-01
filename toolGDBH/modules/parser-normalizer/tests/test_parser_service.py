from __future__ import annotations

from pathlib import Path

import pytest

from errors import ParseError
from parser_normalizer import ParserNormalizerService


FIXTURE = (
    Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "sample_giamdinhhs.xml"
)


def test_parse_file_should_build_claim_header_and_lines() -> None:
    service = ParserNormalizerService()

    result = service.parse_file(FIXTURE)

    assert result.header.claim_id == "HS001"
    assert result.header.facility_id == "79001"
    assert len(result.lines) == 2
    assert len(result.documents) == 1
    assert result.documents[0].document_type == "XML1"
    assert result.documents[0].claim_id == "HS001"
    assert result.lines[0].item_code == "DV001"
    assert result.lines[1].amount == 200000


def test_parse_text_should_keep_all_filehoso_as_document_refs() -> None:
    service = ParserNormalizerService()
    xml_text = """
    <GIAMDINHHS>
      <DANHSACHHOSO>
        <FILEHOSO>
          <LOAIHOSO>XML1</LOAIHOSO>
          <NOIDUNGFILE>PFhNTDE+PFRIT05HVElOSE9TTz48TUFfSE9TTz5IUzAwMTwvTUFfSE9TTz48TUFfQ1NLQ0I+NzkwMDE8L01BX0NTS0NCPjxNQV9OR1VPSUJFTkg+UE4wMDE8L01BX05HVU9JQkVOSD48TUFfVEhFPlRIRTAwMTwvTUFfVEhFPjxMT0FJX0tDQj5pbnBhdGllbnQ8L0xPQUlfS0NCPjxOR0FZX1ZBTz4yMDI2LTAzLTI4VDA4OjAwOjAwPC9OR0FZX1ZBTz48TkdBWV9SQT4yMDI2LTAzLTI5VDEwOjAwOjAwPC9OR0FZX1JBPjxNQV9CRU5IPkEwOTwvTUFfQkVOSD48TUFfVFVZRU4+MDE8L01BX1RVWUVOPjxUT05HX1RJRU4+MTAwMDAwPC9UT05HX1RJRU4+PFRJRU5fQkhZVD44MDAwMDwvVElFTl9CSFlUPjxUSUVOX05HVU9JQkVOSD4yMDAwMDwvVElFTl9OR1VPSUJFTkg+PC9USE9OR1RJTkhPU08+PERTQUNIX0NISV9USUVUPjxDSElfVElFVD48TUFfRE9ORz5MMDAxPC9NQV9ET05HPjxMT0FJX0RPTkc+c2VydmljZTwvTE9BSV9ET05HPjxNQV9ESUNIX1ZVPkRWMDAxPC9NQV9ESUNIX1ZVPjxURU5fRElDSF9WVT5LaGFtIGJlbmg8L1RFTl9ESUNIX1ZVPjxTT19MVU9ORz4xPC9TT19MVU9ORz48RE9OX0dJQT4xMDAwMDA8L0RPTl9HSUE+PFRIQU5IX1RJRU4+MTAwMDAwPC9USEFOSF9USUVOPjxNQV9LSE9BPktIMDE8L01BX0tIT0E+PE1BX0JTPjM4MjAyMjI2MjM8L01BX0JTPjwvQ0hJX1RJRVQ+PC9EU0FDSF9DSElfVElFVD48L1hNTDE+</NOIDUNGFILE>
        </FILEHOSO>
        <FILEHOSO>
          <LOAIHOSO>XML2</LOAIHOSO>
          <NOIDUNGFILE>PFhNTDI+PFRFWFQ+REFUQTwvVEVYVD48L1hNTDI+</NOIDUNGFILE>
        </FILEHOSO>
      </DANHSACHHOSO>
    </GIAMDINHHS>
    """

    result = service.parse_text(xml_text)

    assert [doc.document_type for doc in result.documents] == ["XML1", "XML2"]
    assert result.documents[1].claim_id == "HS001"


def test_parse_text_should_raise_when_root_invalid() -> None:
    service = ParserNormalizerService()

    with pytest.raises(ParseError) as exc:
        service.parse_text("<NOT_GIAMDINHHS />")

    assert exc.value.error_code == "PARSER.ROOT.INVALID"


def test_parse_text_should_normalize_tong_hop_effective_date() -> None:
    service = ParserNormalizerService()
    xml_text = """
    <GIAMDINHHS>
      <DANHSACHHOSO>
        <FILEHOSO>
          <LOAIHOSO>XML1</LOAIHOSO>
          <NOIDUNGFILE>PFRPTkdfSE9QPgogIDxNQV9MSz5IT1NUSDAwMTwvTUFfTEs+CiAgPE1BX0NTS0NCPjc5MDAxPC9NQV9DU0tDQj4KICA8TUFfQk4+UE4wMDE8L01BX0JOPgogIDxNQV9USEVfQkhZVD5USEUwMDE8L01BX1RIRV9CSFlUPgogIDxNQV9MT0FJX0tDQj4wMzwvTUFfTE9BSV9LQ0I+CiAgPE5HQVlfVkFPPjIwMjYwMzI4MDgwMDwvTkdBWV9WQU8+CiAgPE5HQVlfUkE+MjAyNjAzMjkxMDAwPC9OR0FZX1JBPgogIDxNQV9CRU5IX0NISU5IPkEwOTwvTUFfQkVOSF9DSElOSD4KICA8TUFfRE9JVFVPTkdfS0NCPjAxPC9NQV9ET0lUVU9OR19LQ0I+CiAgPFRfVE9OR0NISV9CVj4xMDAwMDA8L1RfVE9OR0NISV9CVj4KICA8VF9CSFRUPjgwMDAwPC9UX0JIVFQ+CiAgPFRfQk5DQ1Q+MjAwMDA8L1RfQk5DQ1Q+CiAgPE1BX0JFTkhfS1Q+QjAwO0MwMDwvTUFfQkVOSF9LVD4KPC9UT05HX0hPUD4=</NOIDUNGFILE>
        </FILEHOSO>
      </DANHSACHHOSO>
    </GIAMDINHHS>
    """

    result = service.parse_text(xml_text)

    assert result.header.claim_id == "HOSTH001"
    assert result.header.claim_effective_date == "2026-03-29"


def test_build_xml5_note_records_from_file_should_link_xml5_with_claim_context() -> None:
    service = ParserNormalizerService()

    records = service.build_xml5_note_records_from_file(FIXTURE)

    assert len(records) == 0


def test_build_xml5_note_records_from_text_fixture_should_create_record(tmp_path: Path) -> None:
    service = ParserNormalizerService()
    xml_file = tmp_path / "giamdinh.xml"
    xml_file.write_text(
        """
        <GIAMDINHHS>
          <DANHSACHHOSO>
            <FILEHOSO>
              <LOAIHOSO>XML1</LOAIHOSO>
              <NOIDUNGFILE>PFRPTkdfSE9QPgogIDxNQV9MSz5IUzAwMTwvTUFfTEs+CiAgPE1BX0NTS0NCPjc5MDAxPC9NQV9DU0tDQj4KICA8TUFfQk4+UE4wMDE8L01BX0JOPgogIDxNQV9USEVfQkhZVD5USEUwMDE8L01BX1RIRV9CSFlUPgogIDxNQV9MT0FJX0tDQj4wMzwvTUFfTE9BSV9LQ0I+CiAgPE5HQVlfVkFPPjIwMjYwMzI4MDgwMDwvTkdBWV9WQU8+CiAgPE5HQVlfUkE+MjAyNjAzMjkxMDAwPC9OR0FZX1JBPgogIDxNQV9CRU5IX0NISU5IPkEwOTwvTUFfQkVOSF9DSElOSD4KICA8TUFfRE9JVFVPTkdfS0NCPjAxPC9NQV9ET0lUVU9OR19LQ0I+CiAgPFRfVE9OR0NISV9CVj4xMDAwMDA8L1RfVE9OR0NISV9CVj4KICA8VF9CSFRUPjgwMDAwPC9UX0JIVFQ+CiAgPFRfQk5DQ1Q+MjAwMDA8L1RfQk5DQ1Q+CiAgPE1BX0JFTkhfS1Q+QjAwO0MwMDwvTUFfQkVOSF9LVD4KPC9UT05HX0hPUD4=</NOIDUNGFILE>
            </FILEHOSO>
            <FILEHOSO>
              <LOAIHOSO>XML2</LOAIHOSO>
              <NOIDUNGFILE>PENISVRJRVVfQ0hJVElFVF9USFVPQz4KICA8RFNBQ0hfQ0hJX1RJRVRfVEhVT0M+CiAgICA8Q0hJX1RJRVRfVEhVT0M+CiAgICAgIDxTVFQ+MTwvU1RUPgogICAgICA8TUFfVEhVT0M+VEgwMDE8L01BX1RIVU9DPgogICAgICA8VEVOX1RIVU9DPkZpc3VsdHkgMiBnPC9URU5fVEhVT0M+CiAgICAgIDxTT19MVU9ORz4xPC9TT19MVU9ORz4KICAgICAgPERPTl9HSUE+MTAwMDAwPC9ET05fR0lBPgogICAgICA8VEhBTkhfVElFTl9CVj4xMDAwMDA8L1RIQU5IX1RJRU5fQlY+CiAgICAgIDxNQV9LSE9BPkswMTwvTUFfS0hPQT4KICAgICAgPE1BX0JBQ19TST5CUzAwMTwvTUFfQkFDX1NJPgogICAgICA8TkdBWV9ZTD4yMDI2LTAzLTI4VDA5OjAwOjAwPC9OR0FZX1lMPgogICAgPC9DSElfVElFVF9USFVPQz4KICA8L0RTQUNIX0NISV9USUVUX1RIVU9DPgo8L0NISVRJRVVfQ0hJVElFVF9USFVPQz4=</NOIDUNGFILE>
            </FILEHOSO>
            <FILEHOSO>
              <LOAIHOSO>XML5</LOAIHOSO>
              <NOIDUNGFILE>PENISVRJRVVfQ0hJVElFVF9ESUVOQklFTkxBTVNBTkc+CiAgPERTQUNIX0NISV9USUVUX0RJRU5fQklFTl9CRU5IPgogICAgPENISV9USUVUX0RJRU5fQklFTl9CRU5IPgogICAgICA8U1RUPjE8L1NUVD4KICAgICAgPERJRU5fQklFTl9MUz5DaOG6qW4gxJFvw6FuOiBBMDkuIENow6sgxJHhu4tuaCBGaXN1bHR5IDIgZywgZ2hpIG5o4bqtbiBuaGnhu4VtIHRyxrDhu5tuZy4gQ2jhu4kgxJHhu4tuaCBYLXF1YW5nLjwvRElFTl9CSUVOX0xTPgogICAgICA8VEhPSV9ESUVNX0RCTFM+MjAyNi0wMy0yOFQwODozMDowMDwvVEhPSV9ESUVNX0RCTFM+CiAgICAgIDxOR1VPSV9USFVDX0hJRU4+QlMwMDE8L05HVU9JX1RIVUNfSElFTj4KICAgIDwvQ0hJX1RJRVRfRElFTl9CSUVOX0JFTkg+CiAgPC9EU0FDSF9DSElfVElFVF9ESUVOX0JJRU5fQkVOSD4KPC9DSElUSUVVX0NISVRJRVRfRElFTkJJRU5MQU1TQU5HPg==</NOIDUNGFILE>
            </FILEHOSO>
          </DANHSACHHOSO>
        </GIAMDINHHS>
        """,
        encoding="utf-8",
    )

    records = service.build_xml5_note_records_from_file(xml_file)

    assert len(records) == 1
    assert records[0].claim_id == "HS001"
    assert records[0].source_file_name == "giamdinh.xml"
    assert records[0].recorded_date == "2026-03-28"
    assert records[0].linked_item_codes == ["TH001"]
    assert records[0].linked_line_ids == ["XML2-1"]
    assert records[0].evidence_flags.has_diagnosis_context is True


def test_build_xml5_note_records_should_extract_relevant_context_tags(tmp_path: Path) -> None:
    service = ParserNormalizerService()
    xml_file = tmp_path / "giamdinh_tags.xml"
    xml_file.write_text(
        """
        <GIAMDINHHS>
          <DANHSACHHOSO>
            <FILEHOSO>
              <LOAIHOSO>XML1</LOAIHOSO>
              <NOIDUNGFILE>PFRPTkdfSE9QPgogIDxNQV9MSz5IUzAwMjwvTUFfTEs+CiAgPE1BX0NTS0NCPjc5MDAxPC9NQV9DU0tDQj4KICA8TUFfQk4+UE4wMDI8L01BX0JOPgogIDxNQV9USEVfQkhZVD5USEUwMDI8L01BX1RIRV9CSFlUPgogIDxNQV9MT0FJX0tDQj4wMzwvTUFfTE9BSV9LQ0I+CiAgPE5HQVlfVkFPPjIwMjYwMzI4MDgwMDwvTkdBWV9WQU8+CiAgPE5HQVlfUkE+MjAyNjAzMjkxMDAwPC9OR0FZX1JBPgogIDxNQV9CRU5IX0NISU5IPkMwMDwvTUFfQkVOSF9DSElOSD4KICA8TUFfRE9JVFVPTkdfS0NCPjAxPC9NQV9ET0lUVU9OR19LQ0I+CiAgPFRfVE9OR0NISV9CVj4xMDAwMDA8L1RfVE9OR0NISV9CVj4KICA8VF9CSFRUPjgwMDAwPC9UX0JIVFQ+CiAgPFRfQk5DQ1Q+MjAwMDA8L1RfQk5DQ1Q+CiAgPE1BX0JFTkhfS1Q+RDAwO0UwMDwvTUFfQkVOSF9LVD4KPC9UT05HX0hPUD4=</NOIDUNGFILE>
            </FILEHOSO>
            <FILEHOSO>
              <LOAIHOSO>XML5</LOAIHOSO>
              <NOIDUNGFILE>PENISVRJRVVfQ0hJVElFVF9ESUVOQklFTkxBTVNBTkc+CiAgPERTQUNIX0NISV9USUVUX0RJRU5fQklFTl9CRU5IPgogICAgPENISV9USUVUX0RJRU5fQklFTl9CRU5IPgogICAgICA8U1RUPjE8L1NUVD4KICAgICAgPERJRU5fQklFTl9MUz5C4buHbmggbmjDom4gbcOqdCwgw6RuIGvDqW0sIGJ14buTbiBuw7RuLCBuw7RuIDEgbOG6p24vIG5nw6B5LiBIb8OhIGNo4bqldCBOYXZlbGJpbi48L0RJRU5fQklFTl9MUz4KICAgICAgPFRIT0lfRElFTV9EQkxTPjIwMjYtMDMtMjhUMDg6MzA6MDA8L1RIT0lfRElFTV9EQkxTPgogICAgICA8TkdVT0lfVEhVQ19ISUVOPkJTMDAxPC9OR1VPSV9USFVDX0hJRU4+CiAgICA8L0NISV9USUVUX0RJRU5fQklFTl9CRU5IPgogIDwvRFNBQ0hfQ0hJX1RJRVRfRElFTl9CSUVOX0JFTkg+CjwvQ0hJVElFVV9DSElUSUVUX0RJRU5CSUVOTEFNU0FORz4=</NOIDUNGFILE>
            </FILEHOSO>
          </DANHSACHHOSO>
        </GIAMDINHHS>
        """,
        encoding="utf-8",
    )

    records = service.build_xml5_note_records_from_file(xml_file)

    assert len(records) == 1
    assert set(records[0].context_tags) == {"buon non", "an kem", "met moi", "hoa chat"}


def test_extract_context_tags_should_capture_postop_digestive_and_sonde_patterns() -> None:
    service = ParserNormalizerService()
    tags = service._extract_context_tags(
        "Bệnh nhân đau nhiều vết mổ, đau rát vùng thượng vị, ợ hơi, ợ chua. Chân mở thông dạ dày khô."
    )

    assert {"hau phau", "tieu hoa", "sonde"} <= set(tags)
