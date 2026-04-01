from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXTRA_PATHS = [
    ROOT / "shared" / "types",
    ROOT / "shared",
    ROOT / "modules" / "parser-normalizer" / "src",
    ROOT / "modules" / "eligibility-service" / "src",
    ROOT / "modules" / "master-data-service" / "src",
    ROOT / "modules" / "deterministic-rule-engine" / "src",
    ROOT / "modules" / "reviewer-workspace" / "src",
    ROOT / "modules" / "rule-registry" / "src",
    ROOT / "modules" / "case-triage" / "src",
    ROOT / "modules" / "audit-reporting" / "src",
]

for extra_path in EXTRA_PATHS:
    extra = str(extra_path)
    if extra not in sys.path:
        sys.path.insert(0, extra)
