# deterministic-rule-engine

## Trach nhiem

- Chay rule deterministic theo version.
- Sinh `rule_hit` va tinh tac dong so tien.

## Input

- Parsed snapshot.
- Master snapshot.
- Eligibility result.
- Rule set version.
- Payment policy/rules config.
- Guideline draft JSONL va `internal_code_policy.mwp.json` cho ma nghiep vu trung gian `INT.*`.

## Output

- `rule_hit[]`
- Bao gom hit tu guideline draft neu line trong ho so khop `applies_to_codes` va thieu `required_evidence`.

## Failure Isolation

- Rule loi thi capture rieng.
- Cho phep disable rule loi ma khong dung ca engine.
