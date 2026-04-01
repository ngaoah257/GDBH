from __future__ import annotations

import json
from pathlib import Path

from audit_reporting import AuditReportingService


def test_audit_reporting_should_append_jsonl_event(tmp_path: Path) -> None:
    service = AuditReportingService(tmp_path)

    event = service.log_event(
        module_name="rule-engine",
        entity_type="claim",
        entity_id="HS001",
        action="evaluate",
        action_result="success",
        version_ref="engine@0.1.0",
        details={"hit_count": 0},
    )

    files = list(tmp_path.glob("audit-*.jsonl"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text(encoding="utf-8").strip())
    assert payload["event_id"] == event.event_id
    assert payload["details"]["hit_count"] == 0
