from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from claim_models import KBQueryFilters, QueryRecord, RetrievalHit, RetrievalResult


class EvidenceRetrievalService:
    RETRIEVER_VERSION = "lexical-retriever-0.1.0"
    EMBEDDING_MODEL = "lexical-baseline"

    def load_jsonl(self, input_path: str | Path) -> list[dict]:
        path = Path(input_path)
        rows: list[dict] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rows.append(json.loads(line))
        return rows

    def load_queries(self, input_path: str | Path) -> list[QueryRecord]:
        queries: list[QueryRecord] = []
        for row in self.load_jsonl(input_path):
            row["filters"] = KBQueryFilters(**row.get("filters", {}))
            queries.append(QueryRecord(**row))
        return queries

    def retrieve_for_query(
        self,
        query: QueryRecord,
        chunks: list[dict],
        top_k: int = 5,
    ) -> RetrievalResult:
        candidates = [chunk for chunk in chunks if self._passes_filters(query, chunk)]
        scored_hits: list[tuple[float, RetrievalHit]] = []
        for chunk in candidates:
            hit = self._score_chunk(query, chunk)
            if hit.score <= 0:
                continue
            scored_hits.append((hit.score, hit))
        scored_hits.sort(key=lambda item: (-item[0], item[1].chunk_id))
        ranked_hits: list[RetrievalHit] = []
        for rank, (_, hit) in enumerate(scored_hits[:top_k], start=1):
            hit.rank = rank
            ranked_hits.append(hit)
        return RetrievalResult(
            query_id=query.query_id,
            retriever_version=self.RETRIEVER_VERSION,
            embedding_model=self.EMBEDDING_MODEL,
            results=ranked_hits,
            retrieved_at=self._now_iso(),
        )

    def retrieve_from_files(
        self,
        query_path: str | Path,
        chunks_path: str | Path,
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        queries = self.load_queries(query_path)
        chunks = self.load_jsonl(chunks_path)
        return [self.retrieve_for_query(query, chunks, top_k=top_k) for query in queries]

    def export_results(
        self,
        query_path: str | Path,
        chunks_path: str | Path,
        output_path: str | Path,
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        results = self.retrieve_from_files(query_path, chunks_path, top_k=top_k)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            for result in results:
                handle.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")
        return results

    def _passes_filters(self, query: QueryRecord, chunk: dict) -> bool:
        metadata = chunk.get("metadata", {})
        source_type = metadata.get("source_type")
        if query.filters.source_types and source_type not in query.filters.source_types:
            return False
        if query.filters.facility_scope:
            chunk_scope = metadata.get("facility_scope", [])
            if chunk_scope and not set(query.filters.facility_scope).intersection(chunk_scope):
                return False
        if query.specialties:
            chunk_specialties = metadata.get("specialties", [])
            if chunk_specialties and not set(query.specialties).intersection(chunk_specialties):
                return False
        if query.item_types:
            chunk_item_types = metadata.get("item_types", [])
            if chunk_item_types and not set(query.item_types).intersection(chunk_item_types):
                return False
        if query.filters.effective_only and query.effective_date:
            effective_from = metadata.get("effective_from")
            effective_to = metadata.get("effective_to")
            if effective_from and query.effective_date < effective_from:
                return False
            if effective_to and query.effective_date > effective_to:
                return False
        return True

    def _score_chunk(self, query: QueryRecord, chunk: dict) -> RetrievalHit:
        metadata = chunk.get("metadata", {})
        chunk_codes = metadata.get("codes", [])
        chunk_keywords = metadata.get("keywords", [])
        matched_codes = [code for code in query.codes if code in chunk_codes]
        matched_keywords = [
            keyword
            for keyword in self._extract_query_keywords(query)
            if keyword in chunk_keywords
        ]
        query_terms = self._tokenize(query.query_text)
        chunk_terms = self._tokenize(chunk.get("text_chunk", ""))
        matched_terms = query_terms.intersection(chunk_terms)

        score = 0.0
        score += len(matched_codes) * 10.0
        score += len(matched_keywords) * 4.0
        score += min(len(matched_terms), 12) * 0.5
        score += float(metadata.get("priority", 0)) / 100.0

        return RetrievalHit(
            chunk_id=chunk.get("chunk_id", ""),
            score=round(score, 3),
            rank=0,
            matched_codes=matched_codes,
            matched_keywords=matched_keywords,
            metadata=metadata,
        )

    def _extract_query_keywords(self, query: QueryRecord) -> list[str]:
        normalized = self._normalize_text(query.query_text)
        parts = []
        if "context:" in normalized:
            after_context = normalized.split("context:", 1)[1].split("|", 1)[0]
            parts.extend(part.strip() for part in after_context.split(",") if part.strip())
        if "note_type:" in normalized:
            after_type = normalized.split("note_type:", 1)[1].split("|", 1)[0].strip()
            if after_type:
                parts.append(after_type)
        return list(dict.fromkeys(parts))

    def _tokenize(self, raw_text: str) -> set[str]:
        normalized = self._normalize_text(raw_text)
        return {token for token in normalized.split() if len(token) >= 3}

    def _normalize_text(self, raw_text: str) -> str:
        normalized = unicodedata.normalize("NFD", raw_text.lower())
        normalized = normalized.replace("\u0111", "d")
        normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
        normalized = re.sub(r"[^a-z0-9\s:_|,.-]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
