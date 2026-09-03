# DUPLICATE_MEDIA_BLOCKED — Batch Repair

## Triệu chứng
- Alert: `upload_subprocess_nonzero`, reason `DUPLICATE_MEDIA_BLOCKED`
- `report.json`: `status=MANUAL_REVIEW`, reason chứa `[DUPLICATE_MEDIA_BLOCKED] Exact media SHA-256 already verified for machine=N, account=xxx`
- `execution.log`: `[MEDIA_FINGERPRINT] [DUPLICATE_MEDIA_BLOCKED] Exact media SHA-256 already verified...`

## Root cause
`Video Đã Đăng` trong workbook (TikN.xlsx + taikhoan_run_safe.xlsx) thấp hơn số video đã được ledger fingerprint xác nhận là `verified_success`. Điều này xảy ra khi:
- Run bị crash hoặc MANUAL_REVIEW **sau khi** post thành công và ledger finalize → workbook counter không tăng
- Legacy backfill fingerprint được thêm sau khi video đã đăng thật

Kết quả: ca nuôi tiếp theo tính `video_number = workbook_count + 1`, nhưng video đó đã có SHA-256 khớp với entry `verified_success` trong ledger → bị chặn.

## Không phải lỗi code — chỉ cần sync counter

## Quy trình fix batch

### Bước 1: Scan toàn bộ workbook vs ledger
Chạy script tại `D:/Taadaa/tmp/check_fp_v2.py` (hoặc tự tạo tương tự):

```python
import glob, json, os, openpyxl

FP_DIR = 'D:/CodexRuntime/tiktok-video/idempotency/media-fingerprints'
WORKBOOK_ROOT = 'D:/OneDrive/TaadaaData/kibe'
TIK_FILES = [('Tik1.xlsx',1),('Tik2.xlsx',2),('tik3.xlsx',3),('Tik4.xlsx',4),('Tik5.xlsx',5),('Tik6.xlsx',6)]

# Load fingerprint ledger
fp_files = glob.glob(f'{FP_DIR}/*.json')
verified = {}
for f in fp_files:
    with open(f, 'r', encoding='utf-8') as h:
        d = json.load(h)
    if d.get('status') == 'verified_success' or d.get('post_verified') is True:
        m = str(d.get('machine', '')).strip()
        acc = str(d.get('target_account', '')).strip().lstrip('@').casefold()
        vnum = int(d.get('video_number') or 0)
        if m and acc and vnum > 0:
            key = (m, acc)
            verified.setdefault(key, set()).add(vnum)

# Scan workbooks
discrepancies = []
for fname, slot in TIK_FILES:
    fpath = f'{WORKBOOK_ROOT}/{fname}'
    wb = openpyxl.load_workbook(fpath, data_only=True)
    ws = wb['TaiKhoan'] if 'TaiKhoan' in wb.sheetnames else wb.active
    for r in range(2, ws.max_row + 1):
        m_val = ws.cell(row=r, column=1).value
        id_val = ws.cell(row=r, column=3).value
        folder_val = ws.cell(row=r, column=4).value
        v_posted = ws.cell(row=r, column=8).value
        if not m_val or not id_val:
            continue
        m_str = str(m_val).strip()
        acc_norm = str(id_val).strip().lstrip('@').casefold()
        try:
            v_count = int(v_posted) if v_posted is not None else 0
        except: v_count = 0
        key = (m_str, acc_norm)
        if key in verified:
            vnums = sorted(verified[key])
            max_v = max(vnums)
            if max_v > v_count:
                discrepancies.append({'file': fname, 'row': r, 'machine': m_str,
                                      'account': id_val, 'folder': folder_val,
                                      'workbook_count': v_count, 'max_verified': max_v, 'verified_vnums': vnums})

for d in discrepancies:
    print(f"[{d['file']}] M{d['machine']:>2} | {d['account']:<24} | WB={d['workbook_count']} -> max={d['max_verified']}")
```

### Bước 2: Fix batch
Với mỗi dòng lệch, cập nhật `Video Đã Đăng = max_verified` trong:
1. `TikN.xlsx` (cột 8)
2. `taikhoan_run_safe.xlsx` (cột 4, match theo machine + account)
3. Sync local copy: `D:/Taadaa/tiktok-luot nuoi acc/data/taikhoan_run_safe.xlsx`

Luôn backup trước (`shutil.copyfile(src, bak)`) với timestamp.

Script đầy đủ: `D:/Taadaa/tmp/fix_workbook_video_count.py` (đã chạy 2026-09-02).

### Bước 3: Đưa máy về Home (nếu còn hold MANUAL_REVIEW)
```bash
adb -s <serial> shell input keyevent 3
```

## PITFALL: Tại sao không chạy SHA hash file mp4?
Hashing toàn bộ video folder (`D:/TIKTOK-videonuoinick/`) để so sánh với ledger SHA-256 → timeout 900s. Dùng `video_number` từ ledger thay vì hash thật — đủ để phát hiện lệch.

## PITFALL: Ledger có thể chứa backfill legacy
Các record có `legacy_backfill: true` vẫn count là verified — không bỏ qua khi scan.

## Kết quả session 2026-09-02
7 dòng lệch được fix: Tik1 M14, Tik2 M19/M20/M23, Tik3 M34/M69, Tik4 M37. Lệch lớn nhất: M14 hong.bo.anh83 WB=5 vs Ledger max=13.
