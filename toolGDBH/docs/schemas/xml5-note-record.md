# XML5 Note Record Schema

## Mục đích

Tài liệu này chuẩn hóa dữ liệu `XML5` thành record dùng chung để:

- so sánh với rule nghiệp vụ
- truy hồi tri thức
- nối với `clinical_results`, `claim_line`, `diagnosis`
- hiển thị cho `reviewer-workspace`

Mục tiêu là không xử lý `XML5` ở dạng raw text rời rạc.

## Vai trò của XML5 trong hệ thống

`XML5` được xem là nguồn diễn biến lâm sàng, tường thuật hoặc chứng cứ ngữ cảnh.

Trong engine và retrieval, `XML5` chủ yếu dùng để:

- tìm bối cảnh chẩn đoán gần thời điểm phát sinh chi phí
- kiểm tra có diễn biến/y lệnh/chứng cứ hỗ trợ hay không
- tạo query truy hồi tri thức phù hợp với từng dòng chi phí

## Record chuẩn hóa

### Schema

```json
{
  "schema_version": "1.0",
  "claim_id": "string",
  "note_id": "string",
  "source_file_type": "XML5",
  "source_file_name": "string",
  "facility_id": "string",
  "patient_id": "string|null",
  "encounter_id": "string|null",
  "department_code": "string|null",
  "department_name": "string|null",
  "practitioner_id": "string|null",
  "practitioner_name": "string|null",
  "recorded_at": "datetime|null",
  "recorded_date": "date|null",
  "admission_time": "datetime|null",
  "discharge_time": "datetime|null",
  "primary_diagnosis_code": "string|null",
  "primary_diagnosis_text": "string|null",
  "secondary_diagnosis_codes": ["string"],
  "secondary_diagnosis_texts": ["string"],
  "clinical_text": "string",
  "clinical_text_normalized": "string",
  "note_type": "progress_note|order_note|consult_note|procedure_note|summary_note|unknown",
  "context_tags": ["string"],
  "linked_line_ids": ["string"],
  "linked_item_codes": ["string"],
  "linked_result_ids": ["string"],
  "evidence_flags": {
    "has_diagnosis_context": true,
    "has_treatment_context": true,
    "has_procedure_context": false,
    "has_lab_context": false,
    "has_imaging_context": false
  },
  "parser_version": "string",
  "raw_ref": {
    "file_hoso_id": "string|null",
    "xml_node_path": "string|null"
  }
}
```

## Giải thích các trường quan trọng

### Nhóm định danh

- `claim_id`: khóa hồ sơ
- `note_id`: khóa note XML5 duy nhất trong claim
- `source_file_name`: tên file nguồn

### Nhóm thời gian

- `recorded_at`: thời điểm note được ghi
- `recorded_date`: ngày suy ra nếu thiếu giờ
- `admission_time`, `discharge_time`: dùng để kiểm tra note nằm trong đợt điều trị

### Nhóm lâm sàng

- `primary_diagnosis_code/text`
- `secondary_diagnosis_codes/texts`
- `clinical_text`
- `clinical_text_normalized`
- `note_type`
- `context_tags`

### Nhóm liên kết

- `linked_line_ids`: các dòng chi phí liên quan gần thời điểm hoặc match theo code/ngữ cảnh
- `linked_item_codes`: mã dịch vụ/thuốc/VTYT được phát hiện có liên quan
- `linked_result_ids`: kết quả CLS hoặc chứng cứ khác liên quan

### Nhóm cờ chứng cứ

Các cờ này giúp rule engine không phải parse text lại nhiều lần:

- `has_diagnosis_context`
- `has_treatment_context`
- `has_procedure_context`
- `has_lab_context`
- `has_imaging_context`

## Chuẩn hóa text

`clinical_text_normalized` nên được tạo bằng pipeline:

1. loại khoảng trắng dư
2. chuẩn hóa Unicode
3. chuẩn hóa viết tắt phổ biến nếu có từ điển
4. giữ nguyên ý nghĩa y khoa, không thay thế quá tay

Không nên:

- xóa toàn bộ dấu tiếng Việt
- ép lowercase nếu làm mất thông tin mã hoặc tên thuốc

## Gợi ý phân loại `note_type`

Có thể suy ra `note_type` bằng rule hoặc heuristic:

- `progress_note`: diễn biến điều trị
- `order_note`: y lệnh, chỉ định
- `consult_note`: hội chẩn/chuyên khoa
- `procedure_note`: thủ thuật/phẫu thuật
- `summary_note`: tóm tắt vào viện/ra viện
- `unknown`: chưa xác định

## Gợi ý tạo `context_tags`

Ví dụ:

- `kháng sinh`
- `đau bụng`
- `sốt`
- `x-quang`
- `siêu âm`
- `huyết học`
- `sinh hóa`
- `nội soi`
- `hậu phẫu`
- `đái tháo đường`

Các tag này dùng để:

- map nhanh với `claim_line`
- lọc retrieval query
- hỗ trợ reviewer hiểu bối cảnh

## Liên kết XML5 với dòng chi phí

### Nguyên tắc liên kết

Ưu tiên kết hợp nhiều tín hiệu:

1. gần thời điểm phát sinh
2. cùng khoa điều trị
3. cùng người chỉ định/thực hiện nếu có
4. match theo code hoặc keyword
5. match theo chẩn đoán hoặc bối cảnh điều trị

### Kết quả liên kết

Một note có thể liên quan:

- 0 dòng chi phí
- 1 dòng chi phí
- nhiều dòng chi phí

Không ép `1 note = 1 line`.

## Dữ liệu dùng cho retrieval

Từ `xml5_note_record`, có thể tạo query retrieval như sau:

### Query input tối thiểu

```json
{
  "claim_id": "string",
  "note_id": "string",
  "effective_date": "date",
  "specialties": ["string"],
  "codes": ["string"],
  "query_text": "string"
}
```

### Query text đề xuất

Gom từ:

- chẩn đoán
- diễn biến
- chỉ định
- mã dòng chi phí liên quan
- khoa điều trị
- thời điểm

## Ví dụ record

```json
{
  "schema_version": "1.0",
  "claim_id": "HS001",
  "note_id": "XML5-0001",
  "source_file_type": "XML5",
  "source_file_name": "xml5_0001.xml",
  "facility_id": "BV123",
  "patient_id": "BN001",
  "encounter_id": "DT001",
  "department_code": "K03",
  "department_name": "Nội tổng hợp",
  "practitioner_id": "NV001",
  "practitioner_name": "Nguyễn Văn A",
  "recorded_at": "2026-03-31T08:15:00",
  "recorded_date": "2026-03-31",
  "admission_time": "2026-03-30T10:00:00",
  "discharge_time": null,
  "primary_diagnosis_code": "J18",
  "primary_diagnosis_text": "Viêm phổi",
  "secondary_diagnosis_codes": [],
  "secondary_diagnosis_texts": [],
  "clinical_text": "Bệnh nhân sốt, ho, khó thở. Chỉ định kháng sinh và X-quang ngực.",
  "clinical_text_normalized": "Bệnh nhân sốt, ho, khó thở. Chỉ định kháng sinh và X-quang ngực.",
  "note_type": "progress_note",
  "context_tags": ["sốt", "ho", "khó thở", "kháng sinh", "x-quang"],
  "linked_line_ids": ["LINE001", "LINE002"],
  "linked_item_codes": ["TH001", "DV001"],
  "linked_result_ids": [],
  "evidence_flags": {
    "has_diagnosis_context": true,
    "has_treatment_context": true,
    "has_procedure_context": false,
    "has_lab_context": false,
    "has_imaging_context": true
  },
  "parser_version": "parser-0.4.0",
  "raw_ref": {
    "file_hoso_id": "FH001",
    "xml_node_path": "/GIAMDINHHS/FILEHOSO[5]"
  }
}
```

## Tiêu chí hoàn thành

Schema XML5 được coi là đủ dùng khi:

- rule engine có thể dùng để kiểm `clinical context`
- retriever có thể dùng để tạo query tri thức
- reviewer có thể xem được note, thời điểm, liên kết dòng chi phí
- cùng một note có thể replay và so sánh giữa các version parser

