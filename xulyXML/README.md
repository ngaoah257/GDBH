# Xu ly XML giam dinh

Script `extract_giamdinh_xml.py` quet cac file XML trong thu muc con `XML`, giai ma noi dung `NOIDUNGFILE`, va xuat ra mot file Excel nhieu sheet theo `LOAIHOSO`.

## Yeu cau

- Python 3
- Co quyen chay `pip install` trong moi truong Python dang dung

## Cau truc thu muc

```text
xulyXML/
|-- XML/
|   |-- *.xml
|-- output/
|-- extract_giamdinh_xml.py
|-- README.md
```

## Cach chay

Chay voi cau hinh mac dinh:

```powershell
python extract_giamdinh_xml.py
```

Tuy chinh thu muc input va file output:

```powershell
python extract_giamdinh_xml.py -i XML -o output\giamdinh_loaihoso.xlsx
```

## Cai dat thu vien

- Script tu kiem tra va tu dong cai dat thu vien con thieu, hien tai la `openpyxl`
- Khong can chay lenh cai dat thu cong truoc
- Script se dung chinh interpreter dang chay file de goi:

```powershell
python -m pip install openpyxl
```

## Dau vao

- Thu muc mac dinh: `XML`
- Script se doc tat ca file `*.xml` nam truc tiep trong thu muc nay

## Dau ra

- File mac dinh: `output\giamdinh_loaihoso.xlsx`
- Moi sheet tuong ung voi mot `LOAIHOSO`
- Moi dong trong sheet gom cac cot:
  - `source_file`
  - `file_index`
  - `loaihoso`
  - `key_path`
  - `value`
  - `decode_status`

## Logic xu ly

1. Parse XML bao ngoai `GIAMDINHHS`
2. Tim cac node `.//HOSO/FILEHOSO`
3. Lay `LOAIHOSO` va `NOIDUNGFILE`
4. Thu giai ma base64
5. Neu noi dung sau giai ma la XML hop le, script flatten thanh cap `key_path/value`
6. Gom ket qua theo `LOAIHOSO` va ghi ra cac sheet Excel

## Ket qua kiem tra thuc te

Da kiem tra voi file:

- `XML/data_112645_HT3382796012783_25029071_3176.xml`

Ket qua:

- XML goc co 8 `FILEHOSO`
- Tao thanh cong file `output\giamdinh_loaihoso.xlsx`
- Workbook co 8 sheet:
  - `XML1`
  - `XML14`
  - `XML2`
  - `XML3`
  - `XML4`
  - `XML5`
  - `XML7`
  - `XML8`

So dong da ghi:

- `XML1`: 66
- `XML14`: 22
- `XML2`: 3900
- `XML3`: 5922
- `XML4`: 1248
- `XML5`: 288
- `XML7`: 26
- `XML8`: 22

## Luu y

- Sheet dang du lieu hien tai la dang `key_path/value`, phu hop cho doi soat va loc du lieu.
- Neu can dang "moi ho so la 1 dong, moi truong la 1 cot", can doi sang logic pivot theo schema tung `LOAIHOSO`.
