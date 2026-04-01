# Claim Schema MVP

## Muc dich

Tai lieu nay chot schema du lieu toi thieu cho MVP. Tat ca module phai dung chung schema nay de tranh vo hop dong du lieu.

## Doi tuong chinh

### `claim_header`

Truong bat buoc:

- `claim_id`
- `batch_id`
- `facility_id`
- `patient_id`
- `insurance_card_no`
- `visit_type`
- `admission_time`
- `discharge_time`
- `primary_diagnosis_code`
- `route_code`
- `total_amount`
- `insurance_amount`
- `patient_pay_amount`
- `claim_effective_date`

Quy uoc:

- `visit_type`: `outpatient|inpatient`
- So tien dung kieu so thap phan co kiem soat scale.
- Moi moc thoi gian luu theo ISO datetime.

### `claim_line`

Truong bat buoc:

- `line_id`
- `claim_id`
- `line_type`
- `item_code`
- `item_name`
- `quantity`
- `unit_price`
- `amount`

Truong khuyen nghi:

- `ordering_time`
- `execution_time`
- `department_code`
- `practitioner_id`
- `source_xml`
- `source_node_path`

Quy uoc:

- `line_type`: `drug|supply|service|bed|lab|transport|other`
- `source_xml` de truy vet dong phat sinh tu XML nao.

### `claim_document_ref`

Muc dich:

- Lien ket claim voi tai lieu goc va chung cu.

Truong:

- `document_id`
- `claim_id`
- `document_type`
- `file_name`
- `storage_uri`
- `content_hash`
- `created_at`

### `eligibility_result`

Truong:

- `claim_id`
- `card_status`
- `benefit_level`
- `coverage_scope`
- `route_validation_status`
- `history_check_status`
- `messages`

### `master_snapshot_ref`

Truong:

- `snapshot_id`
- `dataset_version`
- `applied_from`
- `applied_to`
- `generated_at`

### `rule_hit`

Truong bat buoc:

- `rule_hit_id`
- `execution_id`
- `claim_id`
- `rule_id`
- `severity`
- `legal_basis`
- `message`
- `suggested_action`

Truong tuy chon:

- `line_id`
- `estimated_amount_impact`
- `required_evidence`
- `debug_payload`

### `triage_result`

Truong:

- `claim_id`
- `execution_id`
- `triage_level`
- `reason_codes`
- `summary`

Quy uoc:

- `triage_level`: `xanh|vang|cam|do`

## Rang buoc du lieu

- `claim_header.total_amount` phai bang tong `claim_line.amount` sau khi loai cac dong bi danh dau huy.
- `claim_line.claim_id` phai ton tai trong `claim_header`.
- `rule_hit.line_id` neu co phai thuoc cung `claim_id`.
- `claim_effective_date` la truong dung de chon `rule_set_version` va `dataset_version`.

## Nguyen tac mo rong

- Khong doi ten truong da phat hanh neu chua co migration plan.
- Truong moi them vao phai co mo ta va gia tri mac dinh.
- Moi thay doi schema phai tang `schema_version`.
