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
        print("Usage: python scripts\\build_guideline_rule_drafts.py <normalized_statements_jsonl> <output_root>")
        return 1

    statements_path = Path(sys.argv[1]).resolve()
    output_root = Path(sys.argv[2]).resolve()
    if not statements_path.exists():
        print("Normalized statements jsonl not found.")
        return 1

    drafts_output, manifest_output = GuidelineRuleBuilderService().export_rule_drafts(
        statements_path,
        output_root,
    )
    print(
        json.dumps(
            {
                "drafts_output": str(drafts_output),
                "manifest_output": str(manifest_output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
