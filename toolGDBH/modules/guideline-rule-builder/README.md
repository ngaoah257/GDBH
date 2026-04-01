# guideline-rule-builder

## Muc dich

Module nay dung de dua cac file `docx` huong dan dieu tri vao quy trinh giám định theo huong:

1. `docx -> guideline statement candidate`
2. `guideline statement candidate -> guideline statement da chuan hoa`
3. `guideline statement da chuan hoa -> rule draft`
4. reviewer/nghiep vu duyet `rule draft` truoc khi dua vao engine chinh thuc

Module nay **khong** tu dong quyet dinh thanh toan. No tao cau truc trung gian de nghiep vu co the chuyen hoa huong dan dieu tri thanh rule co kiem soat.

## Ke hoach thuc hien

### Giai doan 1: Ingest docx

- Doc file `docx`
- Tach paragraph/bullet/heading thanh `statement candidate`
- Luu lai:
  - file goc
  - title/section
  - text goc
  - duong dan file
  - vi tri doan

### Giai doan 2: Chuan hoa guideline statement

Moi statement sau khi reviewer map se co 5 nhom chinh:

- `condition`
- `recommended_action`
- `contraindication`
- `required_evidence`
- `applies_to_codes`

Statement da chuan hoa duoc luu rieng de co the sua nhieu lan ma khong mat text goc.

### Giai doan 3: Sinh rule draft

Tu statement da chuan hoa, module sinh `rule draft` de reviewer/nghiep vu kiem tra:

- `draft_rule_id`
- `severity`
- `suggested_action`
- `trigger`
- `required_evidence`
- `decision_logic_text`

### Giai doan 4: Dua vao rule engine

- Chi cac `rule draft` da duoc duyet moi duoc dua vao registry/rule engine
- Khong dung statement raw de chay quyet dinh truc tiep

## Thu muc du lieu de xuat

```text
runtime/guideline-rules/
  raw/
  parsed/
  mappings/
  normalized/
  drafts/
  manifests/
```

## File dau vao

Ban dua cac file `docx` hoac `doc` vao mot thu muc, vi du:

```text
D:\laptrnh_tool\giamdinh\Guidelines
```

## Quy trinh thao tac tung buoc

Neu dung file `.doc`, module se tu convert sang `.docx` qua Microsoft Word COM tren Windows va luu ban chuyen doi tam trong thu muc `.converted-docx` canh file goc.

### Buoc 1: Tao statement candidate tu Word

Chay script:

```powershell
python scripts\build_guideline_candidates.py D:\laptrnh_tool\giamdinh\Guidelines D:\laptrnh_tool\giamdinh\toolGDBH\runtime\guideline-rules
```

Ket qua:

- `runtime/guideline-rules/parsed/guideline_candidates.jsonl`
- `runtime/guideline-rules/manifests/guideline_candidates.manifest.json`

### Buoc 2: Loc candidate nghiep vu

Chay script:

```powershell
python scripts\filter_guideline_business_candidates.py D:\laptrnh_tool\giamdinh\toolGDBH\runtime\guideline-rules\parsed\guideline_candidates.jsonl D:\laptrnh_tool\giamdinh\toolGDBH\runtime\guideline-rules
```

Ket qua:

- `runtime/guideline-rules/parsed/guideline_business_candidates.jsonl`
- `runtime/guideline-rules/manifests/guideline_business_candidates.manifest.json`

Buoc nay uu tien giu lai doan y khoa va loai bot:

- phan can cu/quyet dinh
- danh sach nhan su, ban tham dinh, ban thu ky
- loi mo dau hanh chinh

### Buoc 3: Chon 10-20 statement quan trong nhat

Mo file `guideline_business_candidates.jsonl` va uu tien cac doan co tinh chat:

- chi dinh
- chong chi dinh
- dieu kien phai co
- yeu cau bang chung
- phac do/thuoc/dich vu cu the

### Buoc 4: Chuan hoa statement

Tu `guideline_business_candidates.jsonl`, tao file `guideline_statements.normalized.jsonl` bang cach dien:

- `condition`
- `recommended_action`
- `contraindication`
- `required_evidence`
- `applies_to_codes`

Co the sua bang tay trong JSONL giai doan dau.

### Buoc 5: Ap mapping noi bo cho cac ma chua co trong danh muc nguon

Neu mot guideline can `applies_to_codes` nhung danh muc nguon chua co ma quy chieu ro rang, luu mapping noi bo tai:

- `runtime/guideline-rules/mappings/internal_code_mappings.json`

Chay script:

```powershell
python scripts\apply_guideline_internal_code_mapping.py D:\laptrnh_tool\giamdinh\toolGDBH\runtime\guideline-rules\normalized\guideline_statements.normalized.jsonl D:\laptrnh_tool\giamdinh\toolGDBH\runtime\guideline-rules\mappings\internal_code_mappings.json D:\laptrnh_tool\giamdinh\toolGDBH\runtime\guideline-rules\normalized\guideline_statements.normalized.jsonl
```

Ket qua:

- cap nhat `applies_to_codes`
- cap nhat `recommended_action.target_codes`
- cap nhat `required_evidence.codes` neu dung cung placeholder

### Buoc 6: Sinh rule draft

Chay script:

```powershell
python scripts\build_guideline_rule_drafts.py D:\laptrnh_tool\giamdinh\toolGDBH\runtime\guideline-rules\normalized\guideline_statements.normalized.jsonl D:\laptrnh_tool\giamdinh\toolGDBH\runtime\guideline-rules
```

Ket qua:

- `runtime/guideline-rules/drafts/guideline_rule_drafts.jsonl`

### Buoc 7: Reviewer/nghiep vu duyet rule draft

Kiem tra:

- severity co dung khong
- suggested action co dung khong
- required evidence co du/sat nghiep vu khong
- applies_to_codes co map dung thuoc/dich vu/VTYT khong

### Buoc 8: Dua rule da duyet vao engine

Sau khi duyet, moi chuyen rule draft thanh config runtime thuc te.

## Nguyen tac nghiep vu

- `docx` la nguon tri thuc, khong phai rule chay truc tiep
- chi `guideline statement da chuan hoa` moi duoc dung de sinh rule draft
- chi `rule draft da duyet` moi duoc dua vao deterministic engine

## Khi nao can lam tiep

Sau khi ban co 3-5 file `docx` mau, buoc tiep theo hop ly la:

- map thu cong 20-30 statement dau tien
- chot taxonomy `condition/recommended_action/contraindication/required_evidence`
- sau do moi nang cap sang giao dien duyet statement/rule draft
