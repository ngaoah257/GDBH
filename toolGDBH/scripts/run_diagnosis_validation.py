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
sys.path.insert(0, str(ROOT / "modules" / "diagnosis-validator" / "src"))

from diagnosis_validator import DiagnosisValidatorService


def resolve_path_from_env(env_name: str, fallback_candidates: list[Path]) -> Path | None:
    raw_value = os.getenv(env_name, "").strip()
    if raw_value:
        return Path(raw_value)
    for candidate in fallback_candidates:
        if candidate.exists():
            return candidate
    return None


def main() -> int:
    default_case_records_file = (
        ROOT / "runtime" / "diagnosis-validation" / "case-records" / "diagnosis_case_records.jsonl"
    )
    default_profiles_file = (
        ROOT / "tests" / "fixtures" / "diagnosis" / "sample_diagnosis_profiles.jsonl"
    )
    default_output_file = (
        ROOT / "runtime" / "diagnosis-validation" / "results" / "diagnosis_validation_results.jsonl"
    )

    case_records_file = (
        Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default_case_records_file.resolve()
    )
    profiles_file = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else default_profiles_file.resolve()
    output_file = Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else default_output_file.resolve()

    if not case_records_file.exists():
        print("Case records file not found.")
        return 1
    if not profiles_file.exists():
        print("Profiles file not found.")
        return 1

    service = DiagnosisValidatorService()
    case_records = service.load_case_records(case_records_file)
    profiles = service.load_profiles(profiles_file)
    results = service.validate_case_records(case_records, profiles)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    service.save_validation_results(results, output_file)

    status_counts: dict[str, int] = {}
    for result in results:
        status_counts[result.validation_status] = status_counts.get(result.validation_status, 0) + 1

    print(
        json.dumps(
            {
                "case_records_file": str(case_records_file),
                "profiles_file": str(profiles_file),
                "output_file": str(output_file),
                "record_count": len(case_records),
                "profile_count": len(profiles),
                "result_count": len(results),
                "status_counts": status_counts,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
