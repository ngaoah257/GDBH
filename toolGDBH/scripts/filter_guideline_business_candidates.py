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
    if len(sys.argv) < 3:
        print("Usage: python scripts\\filter_guideline_business_candidates.py <candidates_jsonl> <output_root>")
        return 1

    candidates_path = Path(sys.argv[1]).resolve()
    output_root = Path(sys.argv[2]).resolve()
    if not candidates_path.exists():
        print("Input candidate file not found.")
        return 1

    filtered_output, manifest_output = GuidelineRuleBuilderService().export_business_candidates(
        candidates_path,
        output_root,
    )
    print(
        json.dumps(
            {
                "filtered_output": str(filtered_output),
                "manifest_output": str(manifest_output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
