# Tool GDBH

Tool GDBH la scaffold MVP cho he thong giám định BHYT theo huong thuc dung:

- tach ro may doc ho so va may ket luan
- rule engine chay theo version hieu luc van ban
- moi module xay dung doc lap de de sua, thay the, va rollback khi loi
- deterministic rules ra quyet dinh truoc, LLM chi de pha sau

Trang thai hien tai la `MVP scaffold`: da co khung tai lieu, parser XML toi thieu, rule registry, deterministic rule engine, triage va audit logging.

## Muc tieu

Du an huong toi mot pipeline giám định BHYT co the:

1. nhan goi ho so `GIAMDINHHS`
2. boc tach `FILEHOSO`, giai ma `NOIDUNGFILE`
3. chuan hoa du lieu thanh `claim_header` va `claim_line`
4. ap dung rule theo ngay hieu luc
5. phan luong `xanh/vang/cam/do`
6. luu audit trail de replay va doi chieu

## Kien truc tong quan

He thong duoc tach thanh cac module doc lap:

- `intake-gateway`
- `parser-normalizer`
- `master-data-service`
- `eligibility-service`
- `rule-registry`
- `deterministic-rule-engine`
- `case-triage`
- `reviewer-workspace`
- `audit-reporting`
- `scheduler-sla`
- `evidence-service` (pha 2)
- `anomaly-llm-assist` (pha 2)

Nguyen tac kien truc:

- moi module co `input`, `output`, `version`, `log` rieng
- khong de parser, rule, UI, audit tron lan
- thay doi phap ly phai version hoa
- moi sua doi phai replay va regression duoc

## Cau truc repo

```text
docs/       tai lieu phap ly, schema, rule, interface
modules/    tung module nghiep vu va ky thuat
shared/     model, error, contract, utils dung chung
scripts/    runner va tool ho tro
tests/      fixture, integration, regression
```

## Tai lieu chinh

- [Blueprint MVP](./reade.md)
- [Claim Schema](./docs/schemas/claim-schema.md)
- [Rule Catalog MVP](./docs/rules/rule-catalog-mvp.md)
- [Legal Mapping 2025-2026](./docs/legal/legal-mapping-2025-2026.md)
- [Module Interface Spec](./docs/architecture/module-interface-spec.md)

## Tinh nang da co

- Parser toi thieu cho goi `GIAMDINHHS`
- Boc tach `XML1` tu `FILEHOSO`
- Chuan hoa sang model claim dung chung
- Rule registry co version hieu luc
- Deterministic rule engine voi evaluator MVP dau tien
- Triage `xanh/vang/cam/do`
- Audit event log append-only theo JSONL
- Runner CLI de chay demo end-to-end

## Ke hoach trien khai hien tai

Huong uu tien hien tai la `chuyen mon dieu tri truoc`, khong mo rong UI hay workflow neu du lieu chuyen mon chua du.

1. Mo rong `parser-normalizer`
   - giu lai day du `FILEHOSO` de lam chung cu va truy vet
   - uu tien doc them cac XML phuc vu chuyen mon dieu tri nhu chi dinh, ket qua, thuoc, PTTT, CLS
   - bo sung fixture va integration test cho du lieu gan thuc te
2. Cuong hoa `master-data-service`
   - nap on dinh danh muc nhan luc, trang thiet bi, dich vu benh vien
   - chuan bi lookup phuc vu rule chuyen mon theo khoa, nguoi thuc hien, dich vu, thiet bi
3. Mo rong `deterministic-rule-engine` theo tung dot nho
   - dot 1: ton tai nhan luc, khoa phong, pham vi dich vu
   - dot 2: logic chuyen mon giua chan doan, dich vu, thuoc, thoi diem thuc hien
   - dot 3: doi chieu dieu kien trang thiet bi va tan suat/lap dich vu bat thuong
4. Nang cap `case-triage`
   - phan luong theo muc do nghi ngo chuyen mon, khong chi theo loi ky thuat
5. Chi mo rong `reviewer-workspace` sau khi da co du rule chuyen mon co gia tri

Nguyen tac thuc hien:

- moi buoc phai co test hoac fixture di kem
- uu tien thay doi nho, replay duoc
- rule moi phai dua tren du lieu parser da lay duoc va danh muc da doi chieu duoc

## Nhat ky thuc hien va diem dung

Muc nay dung de tiep tuc cong viec khi doi may tinh hoac can replay lai qua trinh phat trien.

### Da hoan thanh

1. `parser-normalizer`
   - da doc `XML1`, `XML2`, `XML3`
   - da doc them `XML4` thanh `clinical_results`
   - da doc them `XML5` thanh `clinical_notes`
   - da co integration test voi file that: `xulyXML/XML/data_112645_HT3382796012783_25029071_3176.xml`
2. `master-data-service`
   - da nap danh muc nhan luc tu `Danhmuc/FileNhanVienYTe.xlsx`
   - da nap danh muc trang thiet bi tu `Danhmuc/FileTrangThietBi.xlsx`
   - da nap danh muc dich vu tu `Danhmuc/FileDichVuBV.xlsx`
3. `deterministic-rule-engine`
  - da co `ELIG.CARD_STATUS.001`
  - da co `ELIG.ROUTE.001`
   - da co `MASTER.ITEM_CODE.001`
   - da co `MASTER.ITEM_EFFECTIVE.001`
   - da co `MASTER.PRACTITIONER_EXISTS.001`
   - da co `MASTER.PRACTITIONER_DEPARTMENT.001`
   - da co `MASTER.PRACTITIONER_SCOPE.001`
   - da co `STRUCT.HEADER_SUM.001`
   - da co `LOGIC.TIME_WINDOW.001`
   - da co `LOGIC.CLINICAL_CONTEXT.001`
     - canh bao khi ho so dieu tri thieu `XML5`
     - canh bao khi `XML4` co ket qua CLS nhung khong co dich vu tuong ung trong chi phi
     - canh bao khi dong thuoc/dich vu khong co dien bien XML5 gan thoi diem phat sinh
     - canh bao khi dien bien gan thoi diem phat sinh khong thay chan doan hoac boi canh chan doan
     - da co heuristic theo nhom thuoc:
       - `khang_sinh`
       - `giam_dau_khang_viem`
       - `corticoid`
       - `dinh_duong_truyen`
     - da co heuristic theo nhom dich vu:
       - `x_quang_nguc`
       - `sieu_am_o_bung`
       - `dien_tim`
     - da co heuristic theo nhom CLS:
       - `huyet_hoc`
       - `sinh_hoa_mau`
       - `nuoc_tieu`
     - da co heuristic theo khoa dieu tri o muc MVP:
       - `K01`
       - `K02`
       - `K03`
       - `K03.1`
       - `K19`
       - `K19.1`
       - `K19.2`
       - `K26`
       - `K33`
       - `K48`
       - `K48.1`
     - da co heuristic trang thiet bi tu `MA_MAY` trong `XML3`
       - `x_quang -> XQ.`
       - `sieu_am -> SA.`
       - `dien_tim -> ÐT./DT.`
       - `xet_nghiem_huyet_hoc -> HH.`
       - `xet_nghiem_sinh_hoa -> SH.`
       - `noi_soi -> NS./MNS.`
   - da co `LOGIC.DUPLICATE_LINE.001`
     - danh dau DVKT lap theo nguong tung nhom trong cung ngay
     - danh dau CLS lap theo nguong tung nhom va tung chi so trong cung ngay
4. `reviewer-workspace`
   - da co giao dien Dear PyGui de sua rule
   - da co nut chay thu rule tren 1 file XML

### Diem dung hien tai

- He thong da doc duoc bo ho so gan day du hon va da bat dau doi chieu boi canh lam sang.
- Chua kiem tra duoc "toan bo 1 benh an hoan chinh" theo nghia nghiep vu sau cung, vi van thieu cac rule:
  - doi chieu ma dich vu hieu luc
  - doi chieu thuoc, VTYT, CLS voi chan doan/dien bien
  - doi chieu trang thiet bi
  - rule tan suat lap bat thuong
  - rule thanh toan `PAY.*`

### Thu tu thuc hien tiep theo

1. Mo rong `MASTER.ITEM_CODE.001` va `MASTER.ITEM_EFFECTIVE.001`
   - hien tai moi doi chieu chac chan cho ma dich vu trong `XML3` loai `service` va `XML4`
   - chua doi chieu day du cho thuoc va VTYT vi chua nap danh muc rieng
2. Mo rong `LOGIC.CLINICAL_CONTEXT.001`
   - hien tai da doi chieu theo nguyen tac "co dien bien gan thoi diem phat sinh" va "dien bien co chan doan"
   - da bat dau co heuristic theo nhom thuoc va keyword trong dien bien
   - da bat dau co heuristic theo nhom dich vu va ma CLS
   - da bat dau co heuristic theo khoa dieu tri va trang thiet bi
   - chua doi chieu sau theo nghia nghiep vu sau cung giua tung thuoc/dich vu cu the voi tung chan doan cu the
   - buoc tiep theo la mo rong bang heuristic theo khoa/thiết bi cho nhieu ma hon va bo sung tan suat theo nguong nghiep vu
3. Mo rong `LOGIC.DUPLICATE_LINE.001`
   - da co nguong theo nhom DVKT
   - da co nguong theo nhom CLS
   - buoc tiep theo la dua nguong nay ra file cau hinh de chinh tren giao dien
4. Them rule thanh toan `PAY.*`
   - tach khoan da ket cau trong gia
   - gioi han muc thanh toan va ngoai pham vi
5. Nang cap giao dien reviewer-workspace
   - hien thi ket qua theo nhom: cau truc, dieu kien BHYT, nhan luc, dich vu, chuyen mon

### Lenh de khoi phuc va chay lai tren may moi

```powershell
cd toolGDBH
py -3.11 -m pip install -e . pytest
py -3.11 -m pytest
py -3.11 modules/reviewer-workspace/app.py
```

## Chay nhanh

Yeu cau toi thieu:

- Python `3.11+`
- `Danhmuc/` o cung cap voi `toolGDBH`
- `xulyXML/XML/` de chay bo du lieu that va benchmark

Lenh chay:

```powershell
py -3.11 scripts/run_mvp.py tests/fixtures/sample_giamdinhhs.xml 2026-03-30
```

Lenh nay se:

- parse goi `GIAMDINHHS`
- nap rule dang hieu luc
- chay deterministic rule engine
- triage ho so
- ghi audit event vao `runtime/audit`
- in ket qua JSON ra man hinh

## Workflow hien tai

```text
GIAMDINHHS
  -> parser-normalizer
  -> rule-registry
  -> deterministic-rule-engine
  -> case-triage
  -> audit-reporting
```

## Kiem thu

Da co scaffold test cho:

- parser
- rule registry
- rule engine
- triage
- audit reporting
- regression voi 5 ho so XML that
- benchmark lexical retrieval cho XML5

## Quy trinh local de nghi

1. Cai package va test dependency

```powershell
py -3.11 -m pip install -e . pytest
```

2. Chay test toan bo

```powershell
py -3.11 -m pytest
```

3. Chay reviewer workspace

```powershell
py -3.11 modules/reviewer-workspace/app.py
```

4. Build artifact XML5 va benchmark retrieval lexical baseline

```powershell
py -3.11 scripts/export_xml5_note_records.py
py -3.11 scripts/build_xml5_kb_artifacts.py runtime/xml5_note_records.jsonl runtime/knowledge-base
py -3.11 scripts/run_xml5_retrieval_baseline.py runtime/knowledge-base/queries/xml5_note_records.queries.jsonl runtime/knowledge-base/chunks/xml5_note_records.chunks.jsonl runtime/knowledge-base/retrieval/xml5_note_records.retrieval.jsonl runtime/knowledge-base/retrieval/xml5_note_records.benchmark.json
```

5. Sinh case record va doi chieu chan doan mau

```powershell
py -3.11 scripts/export_diagnosis_case_records.py
py -3.11 scripts/run_diagnosis_validation.py
```

6. Cap nhat snapshot regression khi co thay doi co chu dich

```powershell
py -3.11 scripts/export_regression_rule_hits.py
```

## Roadmap gan

1. Mo rong `parser-normalizer` de giu va doc them cac `FILEHOSO` phuc vu rule chuyen mon
2. Mo rong `master-data-service` cho doi chieu nhan luc, dich vu, trang thiet bi
3. Mo rong deterministic rules theo nhom rule chuyen mon dieu tri
4. Nang cap `case-triage` theo muc do nghi ngo chuyen mon
5. Tao `reviewer-workspace` toi thieu sau khi rule chuyen mon da on dinh

## Ghi chu

Repo nay dang o giai doan scaffold ky thuat va tai lieu. Chua phai ban san sang van hanh thuc te, nhung da du khung de tiep tuc phat trien theo huong module hoa va co the rollback an toan.
