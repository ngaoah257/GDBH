# master-data-service

## Trach nhiem

- Quan ly bo ma dung chung va danh muc co so.
- Tra snapshot theo ngay hieu luc.

## Input

- `claim_effective_date`
- `facility_id`

## Output

- `master_snapshot`

## Failure Isolation

- Sai bo ma co the rollback theo `dataset_version`.
