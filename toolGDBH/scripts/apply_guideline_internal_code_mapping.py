from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules" / "guideline-rule-builder" / "src"))

from guideline_rule_builder import GuidelineRuleBuilderService


def main() -> int:
    if len(sys.argv) < 4:
        print(
            "Usage: python scripts\\apply_guideline_internal_code_mapping.py "
            "<statements_jsonl> <mapping_json> <output_jsonl>"
        )
        return 1

    statements_path = Path(sys.argv[1]).resolve()
    mapping_path = Path(sys.argv[2]).resolve()
    output_path = Path(sys.argv[3]).resolve()
    if not statements_path.exists():
        print("Input statements file not found.")
        return 1
    if not mapping_path.exists():
        print("Internal mapping file not found.")
        return 1

    output_path, manifest_output = GuidelineRuleBuilderService().export_mapped_statements(
        statements_path,
        mapping_path,
        output_path,
    )
    print(
        json.dumps(
            {
                "output_path": str(output_path),
                "manifest_output": str(manifest_output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
