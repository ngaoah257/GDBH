# diagnosis-validator

## Muc dich

Module nay dung de doi chieu:

1. `ma benh / chan doan trong XML`
2. `tai lieu/guideline ung voi ma benh do`
3. `chung cu thuc te trong ho so XML`

Muc tieu khong phai la "tu dong ket luan bac si chan doan sai", ma la tra loi cau hoi nghiep vu:

- ho so hien co co du chung cu de bao ve ma chan doan nay khong
- ma chan doan co phu hop voi trieu chung / CLS / dieu tri da phat sinh khong
- dang o muc:
  - `strong_match`
  - `partial_match`
  - `missing_evidence`
  - `suspected_mismatch`

## Pham vi giai doan 1

Giai doan dau chi dung module nay de:

- dinh nghia schema
- build `diagnosis_case_record` tu XML da parse
- luu `diagnosis_guideline_profile`
- luu `diagnosis_validation_result`

Chua lam:

- engine ket luan hoan chinh
- mapping day du tu guideline/docx
- UI review chi tiet

## Schema chinh

### 1. `diagnosis_guideline_profile`

Day la cau truc tri thuc cho tung ma benh hoac nhom ma benh.

Moi profile gom:

- `profile_id`
- `diagnosis_codes`
- `diagnosis_label`
- `specialty`
- `source_documents`
- `required_symptoms`
- `required_tests`
- `supporting_findings`
- `exclusion_findings`
- `recommended_services`
- `recommended_drugs`
- `evidence_rules`

### 2. `diagnosis_case_record`

Day la record trich tu ho so XML de doi chieu cho tung claim:

- `claim_id`
- `primary_diagnosis_code`
- `secondary_diagnosis_codes`
- `clinical_keywords`
- `service_codes`
- `drug_codes`
- `result_codes`
- `result_keywords`
- `note_refs`
- `timeline_refs`

### 3. `diagnosis_validation_result`

Ket qua doi chieu tam thoi cho tung ma benh:

- `claim_id`
- `diagnosis_code`
- `profile_id`
- `validation_status`
- `matched_symptoms`
- `matched_tests`
- `missing_evidence`
- `conflicting_evidence`
- `recommended_action`
- `summary`

## Thu muc de xuat

```text
runtime/diagnosis-validation/
  profiles/
  case-records/
  results/
  manifests/
```

## Ke hoach thuc hien

### Giai doan 1: Tao profile theo ma benh

- chon tung ma ICD hoac nhom ICD uu tien
- map guideline/docx sang `diagnosis_guideline_profile`
- uu tien profile cho cac ma benh gap nhieu va ton kem

### Giai doan 2: Trich evidence tu XML

- lay XML1/XML2/XML3/XML4/XML5
- chuan hoa thanh `diagnosis_case_record`
- tap trung vao:
  - trieu chung
  - CLS
  - hinh anh
  - thuoc/dich vu lien quan

### Giai doan 3: Doi chieu profile voi case

- kiem tra symptom/test/findings
- danh dau thieu chung cu
- danh dau mau thuan
- sinh `diagnosis_validation_result`

### Giai doan 4: Noi vao reviewer/rule engine

- hien thi ket qua trong reviewer workspace
- tao rule dang:
  - `DX.EVIDENCE.MISSING.*`
  - `DX.CLINICAL_MISMATCH.*`
  - `DX.CODE_THERAPY_MISMATCH.*`

## Cach dung giai doan dau

Trong giai doan nay, module cung cap:

- schema Python dataclass
- helper save/load JSONL
- builder tao `diagnosis_case_record` tu `ParsedClaim`

Buoc tiep theo hop ly sau module nay la:

1. tao 5-10 `diagnosis_guideline_profile` mau
2. build `diagnosis_case_record` tu 20-30 ho so XML
3. quan sat field nao du de doi chieu, field nao con thieu

## Export `diagnosis_case_record` tu thu muc XML

Chay script:

```powershell
python scripts\export_diagnosis_case_records.py D:\laptrnh_tool\giamdinh\xulyXML\XML D:\laptrnh_tool\giamdinh\toolGDBH\runtime\diagnosis-validation\case-records\diagnosis_case_records.jsonl
```

Neu khong truyen tham so, script se tu tim thu muc XML qua bien moi truong `TOOLGDBH_XML_DIR` hoac path mac dinh.

Ket qua:

- `runtime/diagnosis-validation/case-records/diagnosis_case_records.jsonl`

## Chay doi chieu profile voi case record

Da co file profile mau:

- `runtime/diagnosis-validation/profiles/sample_diagnosis_profiles.jsonl`

Chay script:

```powershell
python scripts\run_diagnosis_validation.py D:\laptrnh_tool\giamdinh\toolGDBH\runtime\diagnosis-validation\case-records\diagnosis_case_records.jsonl D:\laptrnh_tool\giamdinh\toolGDBH\runtime\diagnosis-validation\profiles\sample_diagnosis_profiles.jsonl D:\laptrnh_tool\giamdinh\toolGDBH\runtime\diagnosis-validation\results\diagnosis_validation_results.jsonl
```

Ket qua:

- `runtime/diagnosis-validation/results/diagnosis_validation_results.jsonl`

Trang thai giai doan dau co the la:

- `strong_match`
- `partial_match`
- `missing_evidence`
- `suspected_mismatch`
- `missing_profile`
