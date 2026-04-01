# Clinical Disease Profile

## Muc dich

`disease_profiles` trong `clinical_policy.mwp.json` dung de khai bao boi canh lam sang theo tung benh ma khong can sua `engine.py`.

Moi profile benh co the khai bao:

- ma ICD hoac prefix ICD ap dung
- alias chan doan de nhan dien trong XML5
- tu khoa boi canh theo khoa
- mau dich vu/thuoc/CLS can co bang chung XML5

## Cau truc tong quat

```json
{
  "profile_id": "DX.C61.001",
  "diagnosis_code_prefixes": ["C61"],
  "diagnosis_aliases": ["ung thu tuyen tien liet", "psa"],
  "department_context_keywords": {
    "K33": ["ung thu", "psa", "tuyen tien liet"]
  },
  "line_rules": [
    {
      "rule_id": "prostate_mri",
      "line_types": ["service"],
      "item_codes": ["02.9999.0001"],
      "item_code_prefixes": [],
      "item_name_keywords": ["mri tuyen tien liet"],
      "department_codes": ["K33"],
      "required_note_keywords": ["psa", "xam lan"],
      "required_note_match": "any",
      "context_label": "mri danh gia ung thu tuyen tien liet"
    }
  ],
  "result_rules": [
    {
      "rule_id": "psa_followup",
      "service_codes": ["23.9999.0001"],
      "indicator_keywords": ["psa"],
      "required_note_keywords": ["psa", "theo doi"],
      "required_note_match": "all",
      "context_label": "theo doi chi so psa"
    }
  ]
}
```

## Nguyen tac match

- `diagnosis_code_prefixes`: profile duoc kich hoat khi ICD chinh hoac ICD kem theo bat dau bang mot prefix nay.
- `diagnosis_aliases`: duoc cong vao tap tu khoa chan doan de tim boi canh trong XML5.
- `department_context_keywords`: neu dong chi phi nam o khoa tuong ung, XML5 phai co it nhat mot tu khoa trong tap nay.
- `line_rules`: ap dung cho `claim.lines` loai `drug` hoac `service`.
- `result_rules`: ap dung cho `claim.clinical_results`.
- `required_note_match`:
  - `any`: XML5 chi can co mot tu khoa.
  - `all`: XML5 phai co day du tat ca tu khoa.

## Cach mo rong

1. Them profile moi vao `modules/deterministic-rule-engine/config/clinical_policy.mwp.json`.
2. Khai bao ICD, alias, va cac `line_rules` / `result_rules` can doi chieu.
3. Them test fixture cho benh moi.
4. Chay `py -3.11 -m pytest -q`.

## Ghi chu

- Neu benh moi da khai bao trong `disease_profiles`, khong can them nhanh `if Cxx` trong Python.
- Rule `LOGIC.CLINICAL_CONTEXT.001` van la rule danh gia chung; khac biet theo benh nam o config.
