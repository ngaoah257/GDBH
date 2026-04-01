from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from claim_models import AuditEvent


class AuditReportingService:
    """Luu event log append-only de replay va doi chieu."""

    def __init__(self, audit_dir: str | Path):
        self._audit_dir = Path(audit_dir)
        self._audit_dir.mkdir(parents=True, exist_ok=True)

    def log_event(
        self,
        module_name: str,
        entity_type: str,
        entity_id: str,
        action: str,
        action_result: str,
        version_ref: str,
        details: dict | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            event_id=str(uuid4()),
            module_name=module_name,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            action_result=action_result,
            version_ref=version_ref,
            created_at=datetime.now(timezone.utc).isoformat(),
            details=details or {},
        )
        self._append_event(event)
        return event

    def _append_event(self, event: AuditEvent) -> None:
        event_date = event.created_at[:10]
        target_file = self._audit_dir / f"audit-{event_date}.jsonl"
        with target_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event), ensure_ascii=False, default=str))
            handle.write("\n")
