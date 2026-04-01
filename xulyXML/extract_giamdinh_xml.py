#!/usr/bin/env python3
"""
Trich xuat du lieu tu cac file XML giam dinh BHYT trong thu muc con XML
va xuat ra mot file Excel nhieu sheet theo tung LOAIHOSO.
"""

from __future__ import annotations

import argparse
import base64
from collections import defaultdict
from pathlib import Path
import subprocess
import sys
from typing import Any
import re
import xml.etree.ElementTree as ET


DEFAULT_INPUT_DIR = Path("XML")
DEFAULT_OUTPUT_FILE = Path("output") / "giamdinh_loaihoso.xlsx"
EXCEL_SHEET_NAME_LIMIT = 31
INVALID_SHEET_CHARS = r"[\\/*?:\[\]]"
REQUIRED_PACKAGES = {"openpyxl": "openpyxl"}


def ensure_package(module_name: str, package_name: str) -> Any:
    try:
        return __import__(module_name)
    except ImportError:
        print(f"Thieu thu vien '{package_name}', dang tu dong cai dat...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        return __import__(module_name)


Workbook = ensure_package("openpyxl", REQUIRED_PACKAGES["openpyxl"]).Workbook


def normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip()


def decode_base64_to_text(raw: str) -> str | None:
    raw = raw.strip()
    if not raw:
        return ""

    try:
        decoded = base64.b64decode(raw, validate=True)
        return decoded.decode("utf-8", errors="replace")
    except Exception:
        return None


def flatten_obj(obj: Any, prefix: str = "") -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            new_prefix = f"{prefix}.{key}" if prefix else key
            rows.extend(flatten_obj(value, new_prefix))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            new_prefix = f"{prefix}[{idx}]"
            rows.extend(flatten_obj(value, new_prefix))
    else:
        rows.append((prefix, "" if obj is None else str(obj)))

    return rows


def xml_element_to_obj(element: ET.Element) -> Any:
    children = list(element)
    text = normalize_text(element.text)

    if not children:
        return text

    grouped: dict[str, list[Any]] = {}
    for child in children:
        child_obj = xml_element_to_obj(child)
        grouped.setdefault(child.tag, []).append(child_obj)

    result: dict[str, Any] = {}
    for tag, items in grouped.items():
        result[tag] = items[0] if len(items) == 1 else items

    if text:
        result["_text"] = text

    return result


def try_parse_xml(xml_content: str) -> tuple[bool, Any]:
    try:
        root = ET.fromstring(xml_content)
        return True, {root.tag: xml_element_to_obj(root)}
    except ET.ParseError:
        return False, None


def build_sheet_name(loaihoso: str, used_names: set[str]) -> str:
    base_name = re.sub(INVALID_SHEET_CHARS, "_", loaihoso or "UNKNOWN").strip()
    if not base_name:
        base_name = "UNKNOWN"

    base_name = base_name[:EXCEL_SHEET_NAME_LIMIT]
    candidate = base_name
    counter = 1

    while candidate in used_names:
        suffix = f"_{counter}"
        candidate = f"{base_name[: EXCEL_SHEET_NAME_LIMIT - len(suffix)]}{suffix}"
        counter += 1

    used_names.add(candidate)
    return candidate


def parse_outer_xml(xml_path: Path) -> list[dict[str, str]]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    filehoso_nodes = root.findall(".//HOSO/FILEHOSO")
    rows: list[dict[str, str]] = []

    for idx, node in enumerate(filehoso_nodes, start=1):
        loaihoso = normalize_text(node.findtext("LOAIHOSO")) or "UNKNOWN"
        noidung = node.findtext("NOIDUNGFILE") or ""
        decoded_text = decode_base64_to_text(noidung)

        if decoded_text is None:
            rows.append(
                {
                    "source_file": xml_path.name,
                    "file_index": str(idx),
                    "loaihoso": loaihoso,
                    "key_path": "RAW_BASE64_OR_TEXT",
                    "value": noidung,
                    "decode_status": "not_base64",
                }
            )
            continue

        ok, parsed = try_parse_xml(decoded_text)
        if ok:
            for key, value in flatten_obj(parsed):
                rows.append(
                    {
                        "source_file": xml_path.name,
                        "file_index": str(idx),
                        "loaihoso": loaihoso,
                        "key_path": key,
                        "value": value,
                        "decode_status": "decoded_xml",
                    }
                )
        else:
            rows.append(
                {
                    "source_file": xml_path.name,
                    "file_index": str(idx),
                    "loaihoso": loaihoso,
                    "key_path": "RAW_TEXT",
                    "value": decoded_text,
                    "decode_status": "decoded_non_xml",
                }
            )

    return rows


def collect_rows(input_dir: Path) -> tuple[list[dict[str, str]], list[Path]]:
    xml_files = sorted(input_dir.glob("*.xml"))
    if not xml_files:
        raise FileNotFoundError(f"Khong tim thay file XML nao trong thu muc: {input_dir}")

    all_rows: list[dict[str, str]] = []
    for xml_file in xml_files:
        all_rows.extend(parse_outer_xml(xml_file))

    return all_rows, xml_files


def write_excel(rows: list[dict[str, str]], output_file: Path) -> dict[str, int]:
    output_file.parent.mkdir(parents=True, exist_ok=True)

    grouped_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped_rows[row["loaihoso"]].append(row)

    workbook = Workbook()
    default_sheet = workbook.active
    workbook.remove(default_sheet)

    headers = ["source_file", "file_index", "loaihoso", "key_path", "value", "decode_status"]
    used_names: set[str] = set()
    sheet_stats: dict[str, int] = {}

    for loaihoso in sorted(grouped_rows):
        sheet_name = build_sheet_name(loaihoso, used_names)
        worksheet = workbook.create_sheet(title=sheet_name)
        worksheet.append(headers)

        for row in grouped_rows[loaihoso]:
            worksheet.append([row[header] for header in headers])

        for column_cells in worksheet.columns:
            max_length = max(len(str(cell.value or "")) for cell in column_cells)
            worksheet.column_dimensions[column_cells[0].column_letter].width = min(max_length + 2, 80)

        sheet_stats[sheet_name] = len(grouped_rows[loaihoso])

    workbook.save(output_file)
    return sheet_stats


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Quet thu muc XML va xuat Excel nhieu sheet theo LOAIHOSO"
    )
    parser.add_argument(
        "-i",
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Thu muc chua cac file XML can xu ly (mac dinh: ./XML)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_FILE,
        help="File Excel dau ra (mac dinh: ./output/giamdinh_loaihoso.xlsx)",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    if not args.input_dir.exists():
        raise FileNotFoundError(f"Khong tim thay thu muc input: {args.input_dir}")

    rows, xml_files = collect_rows(args.input_dir)
    sheet_stats = write_excel(rows, args.output)

    print("Hoan tat xuat Excel.")
    print(f"- Thu muc XML: {args.input_dir.resolve()}")
    print(f"- So file XML da xu ly: {len(xml_files)}")
    print(f"- File Excel: {args.output.resolve()}")
    print(f"- So sheet da tao: {len(sheet_stats)}")
    for sheet_name, row_count in sheet_stats.items():
        print(f"  + {sheet_name}: {row_count} dong")


if __name__ == "__main__":
    main()
