from __future__ import annotations

from claim_models import EngineResult, TriageResult


class CaseTriageService:
    """Phan luong ho so dua tren severity cua rule hit."""

    def triage(self, engine_result: EngineResult) -> TriageResult:
        if not engine_result.hits:
            return TriageResult(
                claim_id=engine_result.claim_id,
                triage_level="xanh",
                summary="Khong phat hien rule hit deterministic.",
            )

        severities = {hit.severity for hit in engine_result.hits}
        reason_codes = [hit.rule_id for hit in engine_result.hits]

        if "reject" in severities:
            level = "do"
            summary = "Co can cu manh de giam tru, xuat toan hoac tu choi."
        elif "pending" in severities:
            level = "cam"
            summary = "Can bo sung chung cu hoac giam dinh chu dong."
        elif "warning" in severities:
            level = "vang"
            summary = "Co canh bao can reviewer xac minh them."
        else:
            level = "xanh"
            summary = "Chi co thong tin tham khao, khong anh huong quyet dinh."

        return TriageResult(
            claim_id=engine_result.claim_id,
            triage_level=level,
            reason_codes=reason_codes,
            summary=summary,
        )
