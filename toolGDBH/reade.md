# Tool Giam Dinh BHYT: Thiet Ke MVP Theo Kieu Module Hoa

## 1. Muc tieu

Tai lieu nay chot huong trien khai thuc dung cho tool giam dinh BHYT:

- Tach ro `may doc ho so` va `may ket luan`.
- Toan bo quy tac phai chay theo `version hieu luc van ban`.
- Moi module xay dung rieng, co the sua, thay the, rollback neu loi.
- MVP chi de `deterministic rules` ra quyet dinh; AI/LLM chi dung o pha sau de doc chung cu va tom tat.

Muc tieu cua MVP:

- Doc dung goi ho so `GIAMDINHHS`.
- Boc tach `FILEHOSO`, giai ma `NOIDUNGFILE`, chuan hoa thanh du lieu claim.
- Kiem tra cau truc, danh muc, the BHYT, quyen loi, va cac rule thanh toan co can cu phap ly ro rang.
- Tra ket qua theo tung ho so va tung dong chi phi.
- Luu vet day du de co the doi chieu, sua rule, va chay lai.

## 2. Nguyen tac kien truc

He thong duoc chia thanh cac module doc lap, ket noi qua hop dong du lieu ro rang:

1. `intake-gateway`
2. `parser-normalizer`
3. `master-data-service`
4. `eligibility-service`
5. `rule-registry`
6. `deterministic-rule-engine`
7. `case-triage`
8. `reviewer-workspace`
9. `audit-reporting`
10. `scheduler-sla`
11. `evidence-service` (pha 2)
12. `anomaly-llm-assist` (pha 2)

Nguyen tac xay dung:

- Moi module co `input`, `output`, `log`, `version` rieng.
- Loi o module nao chi dung o module do, khong duoc lam hong toan bo pipeline.
- Tat ca ket qua trung gian deu duoc luu de co the `replay`.
- Moi rule phai co `rule_id`, `legal_basis`, `effective_from`, `effective_to`.
- Moi bo danh muc phai co `dataset_version`, `applied_from`, `applied_to`.

## 3. Kien truc tong the

Luong xu ly MVP:

1. `intake-gateway` nhan ho so.
2. `parser-normalizer` boc goi va chuan hoa du lieu.
3. `master-data-service` nap snapshot danh muc dung cho thoi diem hieu luc.
4. `eligibility-service` kiem tra the, muc huong, quyen loi.
5. `deterministic-rule-engine` chay bo rule theo version phap ly.
6. `case-triage` xep muc xanh/vang/cam/do.
7. `reviewer-workspace` cho nguoi giam dinh xem va xu ly.
8. `audit-reporting` luu vet, ket xuat bien ban, bao cao, doi chieu.

## 4. Cau truc thu muc de xay dung

De nghi chia repository theo module de de sua va phuc hoi:

```text
/docs
  /legal
  /rules
  /schemas

/modules
  /intake-gateway
  /parser-normalizer
  /master-data-service
  /eligibility-service
  /rule-registry
  /deterministic-rule-engine
  /case-triage
  /reviewer-workspace
  /audit-reporting
  /scheduler-sla
  /evidence-service
  /anomaly-llm-assist

/shared
  /contracts
  /utils
  /types
  /errors

/tests
  /fixtures
  /integration
  /regression
```

Moi module nen co cau truc noi bo:

```text
/modules/<module-name>
  /src
  /tests
  /config
  README.md
  CHANGELOG.md
```

## 5. Mo ta tung module

### 5.1 `intake-gateway`

Nhiem vu:

- Nhan goi ho so XML va metadata gui len.
- Kiem tra chu ky so/xac thuc neu co.
- Cap `claim_batch_id`, `claim_id`.
- Dua file goc vao kho luu tru bat bien.
- Day job sang `parser-normalizer`.

Input:

- Gói ho so XML.
- Thong tin don vi gui.
- Thoi diem gui.

Output:

- `intake_record`
- `raw_file_location`
- `processing_job`

Tach rieng de de sua/rollback:

- Neu parser loi, van giu duoc file goc.
- Co the replay tu `raw_file_location` ma khong can gui lai tu dau.

### 5.2 `parser-normalizer`

Nhiem vu:

- Doc `GIAMDINHHS`.
- Tach tung `FILEHOSO`.
- Giai ma `NOIDUNGFILE`.
- Parse `XML1`, `XML2` va cac XML khac.
- Chuan hoa ve model chung:
  - `claim_header`
  - `claim_line`
  - `claim_document_ref`

Input:

- File goc tu `intake-gateway`.

Output:

- Bo du lieu da chuan hoa.
- Danh sach loi cau truc/dinh dang.

Tach rieng de de sua/rollback:

- Khi thay doi schema XML, chi sua module nay.
- Luu `parsed_snapshot` theo version parser de co the so sanh truoc/sau.

### 5.3 `master-data-service`

Nhiem vu:

- Quan ly danh muc dung chung va danh muc noi bo co so KCB.
- Quan ly hieu luc theo ngay.
- Cung cap snapshot danh muc cho mot ho so tai thoi diem can giam dinh.

Du lieu quan ly:

- Ma thuoc, VTYT, DVKT, phong khoa.
- Danh muc co so.
- Danh muc cap nhat theo cac quyet dinh, thong tu.

Output:

- `master_snapshot`

Tach rieng de de sua/rollback:

- Khi bo ma thay doi, khong anh huong parser hay rule engine.
- Co the rollback ve `dataset_version` cu neu cap nhat danh muc loi.

### 5.4 `eligibility-service`

Nhiem vu:

- Kiem tra thong tin the BHYT.
- Kiem tra muc huong, quyen loi.
- Kiem tra lich su KCB va tinh huong thu hoi/tam khoa neu co.

Input:

- `claim_header`
- Nguon the/quyen loi

Output:

- `eligibility_result`

Tach rieng de de sua/rollback:

- Neu thay doi cach tra cuu the, chi sua module nay.
- Neu nguon du lieu ben ngoai loi, cho phep retry rieng ma khong phai chay lai parser.

### 5.5 `rule-registry`

Nhiem vu:

- Quan ly danh sach rule.
- Quan ly version, ngay hieu luc, can cu phap ly.
- Tach `rule quyet dinh` va `rule canh bao`.

Moi rule phai co toi thieu:

- `rule_id`
- `rule_name`
- `rule_type`
- `severity`
- `effective_from`
- `effective_to`
- `legal_basis`
- `condition_definition`
- `action_definition`
- `owner`
- `test_case_set`

Tach rieng de de sua/rollback:

- Sua rule khong can sua source parser.
- Rollback bang cach quay lai `rule_set_version`.

### 5.6 `deterministic-rule-engine`

Nhiem vu:

- Chay cac rule da duoc phe duyet.
- Dung snapshot dung version phap ly tai thoi diem tinh toan.
- Tra ket qua theo ho so va theo dong chi phi.

Nhom rule MVP:

1. Rule cau truc va dinh dang.
2. Rule doi chieu danh muc.
3. Rule the BHYT, muc huong, quyen loi.
4. Rule thanh toan co can cu phap ly ro.
5. Rule doi chieu tong tien, bang ke, thong tin logic co ban.

Output:

- `rule_hit`
- `affected_line_ids`
- `estimated_amount_impact`
- `suggested_action`

Tach rieng de de sua/rollback:

- Loi logic o 1 rule khong duoc lam sap ca engine.
- Moi rule chay isolated, co timeout, co error capture.
- Co the tat tung rule bang config.

### 5.7 `case-triage`

Nhiem vu:

- Xep hang ho so theo muc:
  - `xanh`
  - `vang`
  - `cam`
  - `do`

Nguyen tac:

- `xanh`: khong co loi hoac chi co canh bao nhe.
- `vang`: co canh bao can xem nhung chua can bo sung.
- `cam`: thieu chung cu hoac can giam dinh chu dong.
- `do`: co can cu manh de giam tru/xuat toan/tu choi.

Tach rieng de de sua/rollback:

- Co the doi chinh logic phan luong ma khong dong vao rule engine.

### 5.8 `reviewer-workspace`

Nhiem vu:

- Hien danh sach ho so.
- Xem ket qua tung rule.
- Xem dong chi phi bi anh huong.
- Ghi nhan ket qua xu ly cua giam dinh vien.
- Tao checklist tai lieu can bo sung.

Man hinh toi thieu cho MVP:

- Dashboard danh sach ho so.
- Man hinh chi tiet ho so.
- Man hinh chi tiet rule hit.
- Man hinh ghi chu, ket luan, yeu cau bo sung.

Tach rieng de de sua/rollback:

- Thay doi UI khong anh huong engine.
- Loi giao dien khong lam mat ket qua tinh toan da luu.

### 5.9 `audit-reporting`

Nhiem vu:

- Luu audit trail day du.
- Xuat bao cao giam dinh.
- Xuat ket qua doi chieu va bien ban lam viec.
- Ho tro truy vet: ho so nao, version nao, rule nao, ket luan nao.

Bat buoc luu:

- file goc
- parser_version
- dataset_version
- rule_set_version
- engine_version
- processing_time
- nguoi xu ly
- ket qua cuoi

Tach rieng de de sua/rollback:

- Khi can doi chieu sau nay, co the replay dung theo version cu.

### 5.10 `scheduler-sla`

Nhiem vu:

- Theo doi han xu ly theo quy dinh.
- Canh bao qua han tiep nhan, phan hoi, giám dinh, bo sung, bien ban.

Tach rieng de de sua/rollback:

- Logic nhac han va SLA khong chen vao engine nghiep vu.

### 5.11 `evidence-service` (Pha 2)

Nhiem vu:

- Luu PDF/scan/anh/HSBA dien tu.
- OCR va phan loai tai lieu.
- Gan chung cu vao `claim_id`, `line_id`, `rule_id`.

Tach rieng de de sua/rollback:

- LLM/OCR loi khong duoc anh huong MVP deterministic.

### 5.12 `anomaly-llm-assist` (Pha 2)

Nhiem vu:

- Tom tat dien bien.
- Dung timeline dieu tri.
- Goi y chung cu thieu.
- Danh dau diem bat thuong de reviewer xem.

Quy tac su dung:

- Khong tu quyet dinh thanh toan.
- Chi dua ra goi y.

## 6. Hop dong du lieu giua cac module

Can thong nhat mot so object chuan.

### 6.1 `claim_header`

```json
{
  "claim_id": "string",
  "facility_id": "string",
  "patient_id": "string",
  "insurance_card_no": "string",
  "visit_type": "outpatient|inpatient",
  "admission_time": "datetime",
  "discharge_time": "datetime",
  "primary_diagnosis_code": "string",
  "secondary_diagnosis_codes": ["string"],
  "route_code": "string",
  "total_amount": 0,
  "insurance_amount": 0,
  "patient_pay_amount": 0,
  "claim_effective_date": "date"
}
```

### 6.2 `claim_line`

```json
{
  "line_id": "string",
  "claim_id": "string",
  "line_type": "drug|supply|service|bed|lab|transport",
  "item_code": "string",
  "item_name": "string",
  "quantity": 0,
  "unit_price": 0,
  "amount": 0,
  "execution_time": "datetime",
  "ordering_time": "datetime",
  "department_code": "string",
  "practitioner_id": "string"
}
```

### 6.3 `rule_hit`

```json
{
  "rule_hit_id": "string",
  "claim_id": "string",
  "line_id": "string|null",
  "rule_id": "string",
  "severity": "info|warning|pending|reject",
  "legal_basis": "string",
  "message": "string",
  "estimated_amount_impact": 0,
  "required_evidence": ["string"],
  "suggested_action": "accept|warn|request_more|reduce|reject"
}
```

## 7. Version hoa de de sua va khoi phuc

Day la phan bat buoc.

### 7.1 Version can quan ly

- `parser_version`
- `schema_version`
- `dataset_version`
- `rule_set_version`
- `engine_version`
- `ui_version`

### 7.2 Nguyen tac rollback

- Khong ghi de ket qua cu.
- Moi lan chay tao `execution_id` moi.
- Ket qua cu duoc luu bat bien.
- Muon rollback chi can:
  - doi `active_version`
  - replay lai job

### 7.3 Replay

He thong phai cho phep:

- Chay lai 1 ho so bang parser moi.
- Chay lai 1 ho so bang bo rule cu.
- Chay lai ca lo ho so de regression test sau khi sua rule.

## 8. Co so du lieu de nghi

Khong nen dồn tat ca vao 1 bang lon. Nen tach:

### 8.1 Nhom intake

- `intake_batch`
- `intake_file`
- `raw_artifact`

### 8.2 Nhom claim

- `claim_header`
- `claim_line`
- `claim_document_ref`

### 8.3 Nhom master data

- `master_dataset`
- `master_item`
- `facility_catalog_item`

### 8.4 Nhom rule

- `rule_definition`
- `rule_version`
- `rule_test_case`
- `rule_activation`

### 8.5 Nhom xu ly

- `execution_run`
- `execution_step`
- `rule_hit`
- `triage_result`

### 8.6 Nhom nghiep vu nguoi dung

- `review_task`
- `review_note`
- `supplement_request`
- `supplement_response`

### 8.7 Nhom audit

- `audit_event`
- `export_report`

## 9. Du lieu toi thieu can co ngay

De MVP chay duoc, can thu thap ngay:

1. Ho so XML thanh toan tu HIS/EMR.
2. Bo ma dung chung va cac ban cap nhat co hieu luc 2025-2026.
3. Danh muc noi bo cua co so KCB.
4. Thong tin the BHYT, muc huong, quyen loi.
5. Cac quy tac phap ly da chot cho MVP.
6. Bang doi chieu ket qua giam dinh lich su neu co.

## 10. Rule backlog cho MVP

Khong nen viet qua nhieu rule ngay lan dau. Uu tien:

### Nhom A. Cau truc

- Thieu XML bat buoc.
- Loi giai ma/noi dung file.
- Sai kieu du lieu.
- Tong tien header khong khop sum line.

### Nhom B. Danh muc

- Ma dich vu khong ton tai.
- Ma thuoc/VTYT het hieu luc.
- Ma danh muc noi bo khong anh xa duoc vao bo ma dung chung.

### Nhom C. The va quyen loi

- The khong hop le.
- Sai muc huong.
- Sai tuyen/quyen loi.

### Nhom D. Thanh toan ro rang

- Khoan da ket cau trong gia nhung van tach tinh rieng.
- Dong chi phi vuot pham vi thanh toan.
- Muc thanh toan sai theo rule da quy dinh.

### Nhom E. Logic co ban

- Ngay vao/ra khong hop ly.
- Dung dich vu sau thoi diem ra vien.
- Lap dong chi phi trung nhau bat thuong.

## 11. Tieu chuan ket qua dau ra

Moi canh bao phai tra du:

- `rule_id`
- `muc do`
- `can cu phap ly`
- `ho so/dong chi phi bi anh huong`
- `so tien uoc tinh`
- `chung cu thieu`
- `hanh dong de nghi`

Vi du:

```json
{
  "rule_id": "PAY.INCLUDED_IN_PRICE.001",
  "severity": "reject",
  "legal_basis": "Thong tu 39/2024/TT-BYT",
  "claim_id": "CLM001",
  "line_id": "LINE009",
  "estimated_amount_impact": 125000,
  "required_evidence": [],
  "suggested_action": "reduce"
}
```

## 12. Kich ban loi va cach khoi phuc

### Tinh huong 1: Parser loi schema moi

Cach xu ly:

- Danh dau `parse_failed`.
- Khong mat file goc.
- Sua parser.
- Replay lai tu `raw_artifact`.

### Tinh huong 2: Cap nhat bo ma sai

Cach xu ly:

- Tat `dataset_version` moi.
- Kich hoat lai `dataset_version` cu.
- Replay cac ho so bi anh huong.

### Tinh huong 3: Rule moi gay false positive

Cach xu ly:

- Disable `rule_activation`.
- Quay ve `rule_set_version` truoc.
- Chay regression bo ho so mau.

### Tinh huong 4: UI loi

Cach xu ly:

- Ket qua xu ly van nam trong `audit-reporting`.
- Co the dung tam giao dien khac/doc truc tiep report.

## 13. Lo trinh trien khai 8 tuan

### Tuan 1-2

- Dung kho source.
- Chot contracts du lieu.
- Tao `intake-gateway`.
- Tao `parser-normalizer` doc bo mau XML.

### Tuan 3-4

- Tao `master-data-service`.
- Tao `rule-registry`.
- Nap rule MVP nhom A, B, C.

### Tuan 5-6

- Tao `deterministic-rule-engine`.
- Tao `case-triage`.
- Tao `audit-reporting`.

### Tuan 7

- Tao `reviewer-workspace` ban toi thieu.
- Viet regression tests tu bo ho so mau.

### Tuan 8

- Chay pilot.
- Ghi nhan false positive/false negative.
- Chot backlog pha 2.

## 14. Chot pham vi MVP

MVP se khong co cac phan sau trong dot dau:

- Khong doc scan/PDF de ra quyet dinh.
- Khong dung LLM de ket luan thanh toan.
- Khong co anomaly scoring phuc tap.
- Khong co workflow doi thoai nang cao.

MVP chi lam 4 viec that chac:

1. Doc dung.
2. Kiem dung.
3. Ket luan duoc voi rule ro rang.
4. Truy vet va replay duoc.

## 15. De xuat buoc tiep theo

Sau tai lieu nay, nen tao ngay 4 artefact ky thuat:

1. `docs/schemas/claim-schema.md`
2. `docs/rules/rule-catalog-mvp.md`
3. `docs/legal/legal-mapping-2025-2026.md`
4. `docs/architecture/module-interface-spec.md`

Neu tiep tuc trien khai ma nguon, uu tien xay theo thu tu:

1. `parser-normalizer`
2. `rule-registry`
3. `deterministic-rule-engine`
4. `audit-reporting`
5. `reviewer-workspace`
