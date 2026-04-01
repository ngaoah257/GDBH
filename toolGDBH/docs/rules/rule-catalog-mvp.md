# Rule Catalog MVP

## Muc dich

Danh muc rule MVP chi gom rule deterministic, co can cu phap ly ro, co the test hoi quy.

## Cau truc rule

Moi rule phai co:

- `rule_id`
- `rule_name`
- `rule_group`
- `severity`
- `legal_basis`
- `effective_from`
- `effective_to`
- `input_scope`
- `decision_logic`
- `suggested_action`
- `owner`

## Nhom rule MVP

### A. Structure Validation

1. `STRUCT.REQUIRED_FILE.001`
- Kiem tra goi ho so co XML bat buoc.
- Hanh dong: `request_more`

2. `STRUCT.DECODE.001`
- Kiem tra `NOIDUNGFILE` giai ma thanh cong.
- Hanh dong: `request_more`

3. `STRUCT.TYPE.001`
- Kiem tra kieu du lieu cac truong bat buoc.
- Hanh dong: `request_more`

4. `STRUCT.HEADER_SUM.001`
- Tong tien header phai khop tong line.
- Hanh dong: `warn`

5. `STRUCT.LINK_KEY.001`
- `MA_LK` phai lien ket thong nhat giua XML1 va cac bang con lai.
- Hanh dong: `request_more`

6. `STRUCT.LINE_AMOUNT.001`
- `THANH_TIEN_BV` phai bang `SO_LUONG * DON_GIA`.
- Hanh dong: `warn`

7. `STRUCT.ADMISSION_DISCHARGE.001`
- `NGAY_VAO` khong duoc sau `NGAY_RA`.
- Hanh dong: `warn`

### B. Master Data Validation

1. `MASTER.ITEM_CODE.001`
- Ma dich vu/thuoc/VTYT phai ton tai trong bo ma hieu luc.
- Hanh dong: `request_more`

2. `MASTER.ITEM_EFFECTIVE.001`
- Ma danh muc phai con hieu luc tai ngay ap dung.
- Hanh dong: `reduce`

3. `MASTER.FACILITY_MAPPING.001`
- Danh muc noi bo phai anh xa vao bo ma dung chung.
- Hanh dong: `request_more`

### C. Eligibility Validation

1. `ELIG.CARD_STATUS.001`
- The BHYT hop le tai thoi diem kham chua benh.
- Hanh dong: `reject`

2. `ELIG.BENEFIT_LEVEL.001`
- Muc huong dung theo thong tin the.
- Hanh dong: `reduce`

3. `ELIG.ROUTE.001`
- Tuyen chuyen va quyen loi huong dung quy dinh.
- Hanh dong: `reduce`

### D. Payment Rules

1. `PAY.INCLUDED_IN_PRICE.001`
- Khoan da ket cau trong gia khong duoc tach thanh toan rieng.
- Hanh dong: `reduce`

2. `PAY.OUT_OF_SCOPE.001`
- Dong chi phi ngoai pham vi thanh toan BHYT.
- Hanh dong: `reject`

3. `PAY.PRICE_LIMIT.001`
- Muc thanh toan khong vuot tran/ty le duoc phep.
- Hanh dong: `reduce`

### E. Logical Consistency

1. `LOGIC.TIME_WINDOW.001`
- Dich vu khong duoc phat sinh sau thoi diem ra vien neu khong co can cu.
- Hanh dong: `warn`

2. `LOGIC.DUPLICATE_LINE.001`
- Dong chi phi lap bat thuong can danh dau.
- Hanh dong: `warn`

3. `LOGIC.CLINICAL_CONTEXT.001`
- Kiem tra logic co ban giua loai dich vu va boi canh dieu tri.
- Hanh dong: `request_more`
- Cau hinh theo tung benh qua `disease_profiles` trong `clinical_policy.mwp.json`, xem them `docs/schemas/clinical-disease-profile.md`.

## Thu tu uu tien

- Nhom A va B chay truoc.
- Nhom C chay sau khi co `claim_header` hop le.
- Nhom D va E chay sau khi co snapshot danh muc va eligibility.

## Chinh sach thay doi

- Rule moi phai co test case.
- Rule doi logic phai tao `rule_version` moi, khong ghi de version cu.
- Rule false positive cao phai co co che disable nhanh qua `rule_activation`.
