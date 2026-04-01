from __future__ import annotations

import json
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "shared" / "types"))
sys.path.insert(0, str(ROOT / "shared"))
sys.path.insert(0, str(ROOT / "modules" / "parser-normalizer" / "src"))

from parser_normalizer import ParserNormalizerService


def resolve_path_from_env(env_name: str, fallback_candidates: list[Path]) -> Path | None:
    raw_value = os.getenv(env_name, "").strip()
    if raw_value:
        return Path(raw_value)
    for candidate in fallback_candidates:
        if candidate.exists():
            return candidate
    return None


def main() -> int:
    default_input_dir = resolve_path_from_env(
        "TOOLGDBH_XML_DIR",
        [ROOT.parent / "xulyXML" / "XML", ROOT / "xulyXML" / "XML"],
    )
    default_output_file = ROOT / "runtime" / "xml5_note_records.jsonl"

    input_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default_input_dir
    output_file = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else default_output_file.resolve()

    if input_dir is None or not input_dir.exists():
        print("Input XML directory not found.")
        return 1

    output_file.parent.mkdir(parents=True, exist_ok=True)

    parser = ParserNormalizerService()
    records = parser.build_xml5_note_records_from_directory(input_dir)

    with output_file.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record.to_dict(), ensure_ascii=False, default=str) + "\n")

    print(
        json.dumps(
            {
                "input_dir": str(input_dir),
                "output_file": str(output_file),
                "record_count": len(records),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
