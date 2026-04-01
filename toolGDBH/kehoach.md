# Kế Hoạch Triển Khai Tool Giám Định BHYT

## 1. Mục tiêu hiện tại

Xây dựng hệ thống giám định BHYT theo hướng thực dụng, gồm 3 trụ chính:

- `deterministic rule engine` làm máy kết luận chính
- `kho tri thức versioned` để tra cứu căn cứ pháp lý, nghiệp vụ, lâm sàng
- `LLM/embedding` chỉ hỗ trợ truy hồi, so sánh ngữ nghĩa, tóm tắt chứng cứ

Nguyên tắc giữ nguyên:

- tách rõ `máy đọc hồ sơ` và `máy kết luận`
- mọi rule và danh mục phải chạy theo `ngày hiệu lực`
- mỗi module xây riêng để dễ sửa, rollback, replay
- không để LLM là máy ra quyết định thanh toán cuối cùng

## 2. Trạng thái hiện tại

### 2.1 Đã có

- `parser-normalizer`
  - đã đọc được `XML1`, `XML2`, `XML3`, `XML4`, `XML5`
  - đã chuẩn hóa được `clinical_results` và `clinical_notes`
- `master-data-service`
  - đã nạp danh mục dịch vụ, nhân lực, trang thiết bị
  - đã mở rộng thêm thuốc và VTYT
- `eligibility-service`
  - đã có kiểm tra điều kiện thẻ và route cơ bản
- `rule-registry`
  - đã có version theo hiệu lực
- `deterministic-rule-engine`
  - đã có `ELIG.*`
  - đã có `MASTER.*`
  - đã có `STRUCT.HEADER_SUM.001`
  - đã có `LOGIC.TIME_WINDOW.001`
  - đã có `LOGIC.CLINICAL_CONTEXT.001`
  - đã có `LOGIC.DUPLICATE_LINE.001`
  - đã có `PAY.INCLUDED_IN_PRICE.001`
- `case-triage`
  - đã phân luồng `xanh/vàng/cam/đỏ`
- `audit-reporting`
  - đã có audit append-only
- `reviewer-workspace`
  - đã chuyển sang Dear PyGui
  - đã có chỉnh rule
  - đã có chỉnh `payment policy`
  - đã có chỉnh `clinical policy`
  - đã có preview XML, lọc hit theo nhóm, export JSON

### 2.2 Chưa hoàn tất

- chưa hoàn thiện nhóm `PAY.*`
- chưa có kho tri thức chính thức cho XML5
- chưa có pipeline retrieval dùng Harrier
- chưa có benchmark so sánh XML5 với tri thức
- chưa có bộ test hồi quy đầy đủ cho dữ liệu thực

## 3. Mục tiêu đích của giai đoạn tiếp theo

Giai đoạn tiếp theo không còn chỉ là MVP parse + rule cơ bản, mà là:

1. hoàn thiện `PAY.*`
2. xây `knowledge base` để dùng với XML5
3. dùng `Harrier` để retrieval đoạn tri thức liên quan
4. để rule engine + reviewer quyết định, LLM chỉ hỗ trợ

## 4. Kiến trúc đích

```text
GIAMDINHHS/XML
  -> parser-normalizer
  -> normalized claim + XML5 note records
  -> eligibility-service
  -> master-data-service
  -> rule-registry
  -> deterministic-rule-engine
  -> case-triage
  -> reviewer-workspace

Kho tri thức
  -> ingest
  -> chunk
  -> embed bằng Harrier
  -> vector index / retriever
  -> trả top-k evidence cho XML5 / line item

LLM layer
  -> tóm tắt chứng cứ
  -> so sánh ngữ nghĩa XML5 với evidence
  -> không tự ra quyết định thanh toán
```

## 5. Kế hoạch theo giai đoạn

### Giai đoạn A. Ổn định lõi rule engine

#### A1. Hoàn thiện `PAY.OUT_OF_SCOPE.001`

Mục tiêu:

- phát hiện dịch vụ, thuốc, VTYT ngoài phạm vi thanh toán
- trả ra `rule_id`, `legal_basis`, `affected_line`, `estimated_amount_impact`

Cần làm:

- thiết kế config ngoài code cho `out_of_scope`
- hỗ trợ match theo:
  - `code`
  - `keyword`
  - `group`
- hỗ trợ `effective_from`, `effective_to`
- hỗ trợ `suggested_action`

Đầu ra:

- evaluator `PAY.OUT_OF_SCOPE.001`
- file config mẫu
- test cho:
  - code ngoài phạm vi
  - keyword ngoài phạm vi
  - rule hết hiệu lực

#### A2. Thêm rule giới hạn mức thanh toán / tỷ lệ thanh toán

Mục tiêu:

- hỗ trợ mức trần và tỷ lệ thanh toán theo config

Các loại giới hạn cần hỗ trợ:

- `coverage_percent`
- `unit_price_max`
- `amount_max`
- `quantity_max`

Cần làm:

- thiết kế schema config thống nhất cho `PAY.*`
- cho phép match theo:
  - `code`
  - `group`
  - `keyword`
- tính `estimated_amount_impact` theo từng loại vi phạm

Đầu ra:

- evaluator payment limit
- config versioned
- test cho từng loại giới hạn

#### A3. Đưa toàn bộ ngưỡng và mapping ra config

Mục tiêu:

- không hardcode nghiệp vụ trong engine nếu tránh được

Phạm vi:

- `PAY.*`
- duplicate thresholds
- clinical heuristics
- mapping item group

Đầu ra:

- engine chỉ còn logic xử lý, không giữ bảng nghiệp vụ lớn trong code
- reviewer-workspace có thể sửa config dễ hơn

### Giai đoạn B. Xây kho tri thức cho XML5

#### B1. Chuẩn hóa dữ liệu XML5

Mục tiêu:

- không dùng raw XML5 trực tiếp cho retrieval

Cần chuẩn hóa XML5 thành record:

- `claim_id`
- `line_id`
- `note_id`
- `performed_at`
- `department_code`
- `practitioner_id`
- `diagnosis_context`
- `clinical_text`
- `linked_item_codes`
- `source_file`

Đầu ra:

- schema `xml5_note_record`
- normalizer riêng cho XML5

#### B2. Thiết kế kho tri thức

Kho tri thức cần có các nhóm:

- văn bản pháp lý
- quy tắc thanh toán
- danh mục thuốc/VTYT/DVKT
- guideline/chỉ định lâm sàng
- quyết định giám định lịch sử
- mẫu chứng cứ và checklist bổ sung hồ sơ

Metadata bắt buộc cho mỗi chunk:

- `doc_id`
- `source_type`
- `title`
- `legal_basis`
- `effective_from`
- `effective_to`
- `specialty`
- `item_type`
- `codes`
- `facility_scope`
- `text_chunk`
- `evidence_required`

Đầu ra:

- schema tài liệu
- quy tắc chunking
- thư mục ingest chuẩn

#### B3. Ingest và version hóa kho tri thức

Mục tiêu:

- mỗi lần cập nhật tri thức có thể replay và rollback

Cần làm:

- tách raw docs và parsed docs
- gắn `kb_version`
- lưu checksum
- lưu nguồn và ngày hiệu lực

Đầu ra:

- pipeline ingest
- manifest cho từng lần cập nhật kho tri thức

### Giai đoạn C. Dùng Harrier để retrieval cho XML5

#### C1. Vai trò của Harrier

`microsoft/harrier-oss-v1-27b` là embedding model, dùng cho:

- retrieval
- semantic similarity
- reranking

Không dùng trực tiếp để kết luận thanh toán.

#### C2. Chiến lược dùng Harrier

Luồng đề xuất:

1. chunk tài liệu tri thức
2. embed toàn bộ chunk
3. tạo query từ từng dòng hoặc từng note XML5
4. retrieve top-k đoạn liên quan
5. đưa kết quả cho rule engine / reviewer / LLM giải thích

Query phải có instruction, ví dụ:

```text
Instruct: Tìm quy định, chỉ định lâm sàng và căn cứ thanh toán liên quan đến dòng XML5 để phục vụ giám định BHYT.
Query: [thông tin XML5 đã chuẩn hóa]
```

#### C3. Lộ trình triển khai Harrier

Thứ tự khuyến nghị:

1. benchmark với model nhỏ hơn trước nếu cần
2. chuẩn hóa bộ query XML5
3. xây vector index
4. đo top-k recall
5. chỉ nâng model nếu chất lượng chưa đạt

Đầu ra:

- module ingest embeddings
- module retriever
- benchmark retrieval cho XML5

### Giai đoạn D. Reviewer workflow có tri thức

Mục tiêu:

- reviewer nhìn thấy không chỉ `rule hit`, mà còn thấy `evidence hit`

Cần làm:

- hiển thị đoạn tri thức top-k liên quan đến từng `rule_hit`
- hiển thị căn cứ pháp lý và ngày hiệu lực
- hiển thị note XML5 nào khớp / không khớp với tri thức
- reviewer có thể đánh dấu:
  - chấp nhận
  - yêu cầu bổ sung
  - giảm trừ
  - từ chối

## 6. Dữ liệu cần chuẩn bị

### 6.1 Bắt buộc cho `PAY.*`

Bạn cần chuẩn bị:

- danh sách khoản ngoài phạm vi
- danh sách mức trần / tỷ lệ thanh toán
- cách tính `estimated_amount_impact`
- căn cứ pháp lý và ngày hiệu lực

Mẫu cấu hình tối thiểu:

- `item_type`
- `match_type`
- `match_value`
- `limit_type`
- `limit_value`
- `legal_basis`
- `effective_from`
- `effective_to`
- `suggested_action`

### 6.2 Bắt buộc cho kho tri thức XML5

Bạn cần chuẩn bị:

- file XML5 đã ẩn danh
- tài liệu pháp lý
- danh mục nghiệp vụ
- guideline/chỉ định
- case giám định mẫu có kết luận đúng/sai

### 6.3 Dữ liệu benchmark

Tối thiểu nên có:

- 20-50 case XML5 mẫu
- với mỗi case:
  - note XML5
  - dòng chi phí liên quan
  - căn cứ đúng cần retrieve được
  - kết luận mong đợi

## 7. Danh sách việc cần làm ngay

### Ưu tiên 1

- tạo `ke schema` cho config `PAY.*`
- thêm `PAY.OUT_OF_SCOPE.001`
- thêm rule giới hạn mức thanh toán / tỷ lệ thanh toán

### Ưu tiên 2

- tạo schema chuẩn cho `xml5_note_record`
- tạo schema cho `knowledge_base_document`
- tạo pipeline ingest tài liệu

### Ưu tiên 3

- tạo module embedding/retrieval dùng Harrier
- tạo benchmark retrieval cho XML5

### Ưu tiên 4

- nối retriever vào reviewer-workspace
- hiển thị evidence side-by-side với rule hit

## 8. Thứ tự triển khai khuyến nghị

1. hoàn thiện `PAY.*`
2. chuẩn hóa XML5
3. xây schema kho tri thức
4. ingest tài liệu
5. nhúng Harrier và retrieval
6. benchmark
7. nối vào reviewer-workspace
8. chỉ sau đó mới thêm LLM giải thích

## 9. Những gì không nên làm lúc này

- không để LLM kết luận thay rule engine
- không nhúng Harrier trước khi có schema tri thức rõ ràng
- không index raw PDF/XML bừa bãi mà không có metadata hiệu lực
- không mở rộng GUI thêm nhiều trước khi lõi `PAY.*` và kho tri thức ổn

## 10. Tiêu chí hoàn thành giai đoạn kế tiếp

Được coi là xong giai đoạn kế tiếp khi:

- `PAY.OUT_OF_SCOPE.001` chạy được bằng config
- rule limit/tỷ lệ thanh toán chạy được bằng config
- XML5 được chuẩn hóa thành record rõ ràng
- kho tri thức có schema và ingest pipeline
- Harrier retrieve được top-k evidence cho XML5
- reviewer nhìn được rule hit + evidence hit trên cùng workflow

## 11. Ghi chú vận hành

- mọi file config phải lưu UTF-8
- mọi tài liệu tri thức phải có `effective_from/effective_to`
- mọi cập nhật rule hoặc KB phải có regression case
- UI có thể hiển thị tiếng Việt có dấu, nhưng key kỹ thuật nội bộ nên giữ ổn định bằng mã tiếng Anh

