# Legal Mapping 2025-2026

## Muc dich

Tai lieu nay mapping van ban phap ly vao module va rule. Day la lop cau noi giua doi nghiep vu va doi ky thuat.

## Van ban muc tieu

### Thong tu 12/2026/TT-BTC

Phan ap dung:

- Quy trinh tiep nhan du lieu va giám dinh.
- Ho so de nghi thanh toan.
- SLA phan hoi, bo sung, bien ban.
- Yeu cau doi chieu du lieu, thong tin the, quyen loi, lich su.

Module anh xa:

- `intake-gateway`
- `eligibility-service`
- `deterministic-rule-engine`
- `scheduler-sla`
- `audit-reporting`

### Thong tu 39/2024/TT-BYT

Phan ap dung:

- Dieu kien, ty le, muc thanh toan.
- Nguyen tac da ket cau trong gia/ chua ket cau trong gia.
- Quy tac thanh toan ngay giuong, kham, dich vu lien quan.

Module anh xa:

- `rule-registry`
- `deterministic-rule-engine`

### QD 130/2023, QD 4750/2023, QD 3176/2024

Phan ap dung:

- Chuan du lieu bang ke chi tiet.
- Ma truong, cau truc XML, quy tac gui nhan.

Module anh xa:

- `parser-normalizer`
- `docs/schemas`

### QD 3276/QD-BYT nam 2025

Phan ap dung:

- Cap nhat bo ma dung chung lien quan gui du lieu dien tu.

Module anh xa:

- `master-data-service`
- `rule-registry`

## Bang mapping phap ly -> ky thuat

| Nhom phap ly | Module | Kieu xay dung |
| --- | --- | --- |
| Tiep nhan ho so | intake-gateway | Validate, luu file goc, replay |
| Chuan du lieu XML | parser-normalizer | Parser versioned |
| Danh muc va hieu luc | master-data-service | Snapshot by effective date |
| The, muc huong, quyen loi | eligibility-service | External lookup + cached result |
| Dieu kien thanh toan | deterministic-rule-engine | Deterministic rules |
| SLA xu ly | scheduler-sla | Timeline + nhac han |
| Doi chieu va truy vet | audit-reporting | Immutable audit trail |

## Nguyen tac cap nhat van ban

- Moi van ban moi duoc dang ky thanh `legal_source`.
- Moi quy tac phat sinh phai lien ket toi it nhat 1 `legal_source`.
- Van ban het hieu luc khong xoa; chi dong `effective_to`.
- Truoc khi kich hoat rule moi phai chay regression.
