# Module Interface Specification

## Muc dich

Chot giao tiep giua cac module de co the phat trien rieng, thay the rieng, va khoi phuc rieng.

## Nguyen tac interface

- Uu tien giao tiep bang message payload JSON ro rang.
- Moi payload phai co `schema_version`.
- Moi module phai idempotent neu nhan lai cung `job_id`.
- Loi duoc tra theo `error_code`, `error_message`, `retryable`.

## Interface 1: Intake -> Parser

### Request

```json
{
  "job_id": "string",
  "schema_version": "1.0",
  "claim_batch_id": "string",
  "raw_file_location": "string",
  "received_at": "datetime"
}
```

### Response

```json
{
  "job_id": "string",
  "parse_status": "success|failed",
  "parsed_snapshot_id": "string",
  "error_list": []
}
```

## Interface 2: Parser -> Master Data

### Request

```json
{
  "job_id": "string",
  "claim_id": "string",
  "claim_effective_date": "date",
  "facility_id": "string"
}
```

### Response

```json
{
  "job_id": "string",
  "snapshot_id": "string",
  "dataset_version": "string"
}
```

## Interface 3: Parser -> Eligibility

### Request

```json
{
  "job_id": "string",
  "claim_id": "string",
  "insurance_card_no": "string",
  "admission_time": "datetime",
  "discharge_time": "datetime",
  "route_code": "string"
}
```

### Response

```json
{
  "job_id": "string",
  "eligibility_status": "success|failed",
  "eligibility_result_id": "string",
  "messages": []
}
```

## Interface 4: Rule Engine Input

```json
{
  "job_id": "string",
  "execution_id": "string",
  "claim_id": "string",
  "parsed_snapshot_id": "string",
  "master_snapshot_id": "string",
  "eligibility_result_id": "string",
  "rule_set_version": "string"
}
```

## Interface 5: Rule Engine Output

```json
{
  "job_id": "string",
  "execution_id": "string",
  "claim_id": "string",
  "rule_hits": [],
  "engine_status": "success|partial|failed"
}
```

## Interface 6: Rule Engine -> Triage

```json
{
  "execution_id": "string",
  "claim_id": "string",
  "rule_hit_ids": ["string"]
}
```

## Interface 7: Triage -> Reviewer Workspace

```json
{
  "claim_id": "string",
  "execution_id": "string",
  "triage_level": "xanh|vang|cam|do",
  "summary": "string"
}
```

## Interface 8: All Modules -> Audit

Payload toi thieu:

```json
{
  "event_id": "string",
  "module_name": "string",
  "entity_type": "claim|batch|rule|review_task",
  "entity_id": "string",
  "action": "string",
  "action_result": "success|failed",
  "version_ref": "string",
  "created_at": "datetime"
}
```

## Error Contract

Tat ca module dung chung form:

```json
{
  "error_code": "string",
  "error_message": "string",
  "retryable": true,
  "details": {}
}
```

## Phuc hoi su co

- Module nao fail thi chi replay lai step do neu du input.
- Khong module nao duoc sua file goc cua module truoc.
- Moi module phai luu `last_successful_output`.
