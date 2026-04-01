# Knowledge Base Schema

## Mục đích

Tài liệu này chốt schema cho kho tri thức dùng trong bài toán:

- truy hồi căn cứ pháp lý, nghiệp vụ, lâm sàng
- so sánh với dữ liệu chuẩn hóa từ `XML5`
- hỗ trợ `reviewer-workspace`, `deterministic-rule-engine`, và lớp retrieval dùng embedding model như `Harrier`

Kho tri thức không phải nơi ra quyết định cuối cùng. Nó là lớp:

- lưu nguồn tri thức có version
- chia nhỏ tài liệu thành chunk có metadata
- hỗ trợ truy hồi đúng theo `ngày hiệu lực`, `chuyên khoa`, `item_type`, `code`

## Nguyên tắc thiết kế

- mọi tài liệu phải có nguồn và ngày hiệu lực
- mọi chunk phải truy vết được về tài liệu gốc
- mọi bản cập nhật phải có `kb_version`
- mọi tri thức phải có metadata đủ mạnh để filter trước khi vector search
- không index raw text không kiểm soát

## Cấu trúc logic của kho tri thức

Kho tri thức gồm 4 lớp:

1. `raw_document`
2. `parsed_document`
3. `knowledge_chunk`
4. `embedding_record`

## 1. Raw Document

Là bản gốc chưa chuẩn hóa.

### Schema

```json
{
  "raw_document_id": "string",
  "kb_version": "string",
  "source_type": "legal|guideline|catalog|historical_decision|hospital_policy|evidence_template",
  "source_name": "string",
  "source_uri": "string",
  "file_path": "string",
  "mime_type": "string",
  "checksum_sha256": "string",
  "collected_at": "datetime",
  "effective_from": "date|null",
  "effective_to": "date|null",
  "issuer": "string|null",
  "title": "string",
  "language": "vi|en|other",
  "status": "active|inactive|superseded"
}
```

### Giải thích

- `source_type`: loại tài liệu
- `source_uri`: URL hoặc nguồn nội bộ
- `effective_from/effective_to`: ngày hiệu lực của tri thức
- `status`: dùng để đánh dấu văn bản còn hiệu lực hay đã thay thế

## 2. Parsed Document

Là bản chuẩn hóa từ tài liệu gốc, đã trích text và metadata nghiệp vụ.

### Schema

```json
{
  "parsed_document_id": "string",
  "raw_document_id": "string",
  "kb_version": "string",
  "title": "string",
  "source_type": "legal|guideline|catalog|historical_decision|hospital_policy|evidence_template",
  "text_content": "string",
  "structured_fields": {
    "document_number": "string|null",
    "document_type": "string|null",
    "legal_basis": ["string"],
    "specialties": ["string"],
    "facility_scope": ["string"],
    "item_types": ["service", "drug", "supply", "clinical_result", "note"],
    "codes": ["string"],
    "keywords": ["string"]
  },
  "effective_from": "date|null",
  "effective_to": "date|null",
  "parsed_at": "datetime",
  "parser_version": "string"
}
```

### Ghi chú

- `structured_fields.codes` là các mã dịch vụ/thuốc/VTYT hoặc mã nghiệp vụ
- `specialties` dùng để lọc theo chuyên khoa trước khi retrieval
- `facility_scope` dùng cho tri thức nội bộ bệnh viện hoặc phạm vi chuyên môn

## 3. Knowledge Chunk

Đây là thực thể chính được đưa vào retriever.

### Schema

```json
{
  "chunk_id": "string",
  "kb_version": "string",
  "parsed_document_id": "string",
  "chunk_index": 0,
  "chunk_type": "legal_clause|guideline_rule|catalog_entry|decision_reason|evidence_checklist|clinical_note_pattern",
  "title": "string",
  "text_chunk": "string",
  "summary": "string|null",
  "metadata": {
    "source_type": "legal|guideline|catalog|historical_decision|hospital_policy|evidence_template",
    "legal_basis": ["string"],
    "effective_from": "date|null",
    "effective_to": "date|null",
    "specialties": ["string"],
    "facility_scope": ["string"],
    "item_types": ["service", "drug", "supply", "clinical_result", "note"],
    "codes": ["string"],
    "keywords": ["string"],
    "evidence_required": ["string"],
    "review_action_hint": ["warn", "request_more", "reduce", "reject", "accept"],
    "priority": 0
  }
}
```

### Ý nghĩa các trường quan trọng

- `chunk_type`: giúp retriever và reviewer hiểu bản chất chunk
- `evidence_required`: ví dụ cần `XML5`, kết quả CLS, y lệnh, chỉ định, phiếu thực hiện
- `review_action_hint`: gợi ý xử lý nếu chunk này được retrieve đúng bối cảnh
- `priority`: dùng để rerank rule/legal chunk lên trên chunk ít quan trọng hơn

## 4. Embedding Record

Là bản ghi embedding của từng chunk.

### Schema

```json
{
  "embedding_id": "string",
  "chunk_id": "string",
  "kb_version": "string",
  "embedding_model": "string",
  "embedding_dimension": 0,
  "embedding_dtype": "float32|float16|bf16",
  "embedding_vector_ref": "string",
  "embedded_at": "datetime"
}
```

### Ghi chú

- `embedding_vector_ref` có thể là:
  - vector lưu trong DB
  - key tới file `.npy`
  - key trong vector store

## 5. Query Record cho XML5

Đây là schema query chuẩn hóa để truy hồi tri thức cho `XML5`.

### Schema

```json
{
  "query_id": "string",
  "claim_id": "string",
  "line_id": "string|null",
  "note_id": "string|null",
  "query_type": "xml5_note_similarity|rule_evidence_lookup|payment_scope_lookup|clinical_context_lookup",
  "effective_date": "date",
  "specialties": ["string"],
  "item_types": ["service", "drug", "supply", "clinical_result", "note"],
  "codes": ["string"],
  "instruction_text": "string",
  "query_text": "string",
  "filters": {
    "source_types": ["legal", "guideline", "catalog", "historical_decision"],
    "facility_scope": ["string"],
    "effective_only": true
  }
}
```

## 6. Retrieval Result

### Schema

```json
{
  "query_id": "string",
  "retriever_version": "string",
  "embedding_model": "string",
  "results": [
    {
      "chunk_id": "string",
      "score": 0.0,
      "rank": 1,
      "matched_codes": ["string"],
      "matched_keywords": ["string"],
      "metadata": {}
    }
  ],
  "retrieved_at": "datetime"
}
```

## 7. Quy tắc chunking

### Với văn bản pháp lý

Nên chunk theo:

- điều
- khoản
- điểm

Không nên chunk mù theo số ký tự nếu làm mất ngữ cảnh pháp lý.

### Với guideline/chỉ định

Nên chunk theo:

- điều kiện chỉ định
- chống chỉ định
- điều kiện thanh toán
- yêu cầu bằng chứng

### Với danh mục

Nên chunk theo từng bản ghi:

- 1 mã dịch vụ
- 1 mã thuốc
- 1 mã VTYT

### Với quyết định giám định lịch sử

Nên chunk theo:

- 1 lý do chấp nhận / xuất toán
- 1 lập luận nghiệp vụ hoàn chỉnh

## 8. Metadata tối thiểu để filter trước vector search

Trước khi truy hồi embedding, nên filter bằng metadata:

- `effective_date`
- `source_type`
- `specialties`
- `item_types`
- `codes`
- `facility_scope`

Điều này giúp:

- giảm nhiễu
- tăng precision
- tránh retrieve văn bản hết hiệu lực

## 9. Ví dụ knowledge chunk

```json
{
  "chunk_id": "kb_legal_0001_03",
  "kb_version": "kb-2026.03.31",
  "parsed_document_id": "doc_legal_0001",
  "chunk_index": 3,
  "chunk_type": "legal_clause",
  "title": "Khoản thanh toán ngoài phạm vi",
  "text_chunk": "Không thanh toán riêng các khoản đã kết cấu trong giá dịch vụ...",
  "summary": "Quy định không thanh toán riêng khoản đã kết cấu trong giá.",
  "metadata": {
    "source_type": "legal",
    "legal_basis": ["TT39/2024/TT-BYT"],
    "effective_from": "2025-01-01",
    "effective_to": null,
    "specialties": [],
    "facility_scope": [],
    "item_types": ["service", "drug", "supply"],
    "codes": [],
    "keywords": ["đã kết cấu", "không thanh toán riêng"],
    "evidence_required": ["bảng kê chi phí", "giá dịch vụ"],
    "review_action_hint": ["reduce"],
    "priority": 100
  }
}
```

## 10. Tổ chức thư mục đề xuất

```text
knowledge-base/
  raw/
    legal/
    guideline/
    catalog/
    historical-decision/
  parsed/
  chunks/
  embeddings/
  manifests/
```

## 11. Tiêu chí hoàn thành

Schema được coi là đủ dùng khi:

- ingest được ít nhất 4 loại tài liệu
- chunk truy hồi được theo `effective_date`
- query từ XML5 tìm ra được top-k chunk có liên quan
- reviewer nhìn được chunk, nguồn, căn cứ pháp lý, ngày hiệu lực

