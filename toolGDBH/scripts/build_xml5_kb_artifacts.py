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

from parser_normalizer import XML5KnowledgeBaseBuilder


def resolve_path_from_env(env_name: str, fallback_candidates: list[Path]) -> Path | None:
    raw_value = os.getenv(env_name, "").strip()
    if raw_value:
        return Path(raw_value)
    for candidate in fallback_candidates:
        if candidate.exists():
            return candidate
    return None


def main() -> int:
    default_input_file = resolve_path_from_env(
        "TOOLGDBH_XML5_JSONL",
        [ROOT / "runtime" / "xml5_note_records.jsonl"],
    )
    default_output_root = ROOT / "runtime" / "knowledge-base"

    input_file = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default_input_file
    output_root = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else default_output_root.resolve()

    if input_file is None or not input_file.exists():
        print("Input XML5 jsonl not found.")
        return 1

    builder = XML5KnowledgeBaseBuilder()
    manifest = builder.export(input_file, output_root)
    print(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
