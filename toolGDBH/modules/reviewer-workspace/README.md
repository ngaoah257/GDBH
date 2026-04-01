# reviewer-workspace

## Trach nhiem

- Hien thi ho so, rule hit, so tien anh huong.
- Ghi nhan ket qua xu ly va yeu cau bo sung.
- Cho phep nguoi dung khong gioi lap trinh xem va chinh sua rule tu giao dien Dear PyGui.

## Input

- `triage_result`
- `rule_hit[]`

## Output

- `review_task`
- `review_note`

## Failure Isolation

- UI loi khong lam mat ket qua audit da luu.

## Chay UI Rule Workspace

Chay tu root repo:

```powershell
py -3.11 modules/reviewer-workspace/app.py
```

Man hinh hien tai cho phep:

- tim rule theo `rule_id`, ten, nhom
- xem chi tiet rule dang luu trong `modules/rule-registry/config/rules.mwp.json`
- chinh `severity`, `decision_logic`, `suggested_action`, `owner`, `effective_from`, `effective_to`
- bat/tat `enabled`
- luu thay doi truc tiep vao file rule registry
