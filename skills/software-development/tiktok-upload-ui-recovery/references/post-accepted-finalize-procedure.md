# Post-ACCEPTED wrap-up: finalize ledger + bump workbook (verified 2026-08-07)

Máy `POST_RECHECK_UNAVAILABLE` với `post_submission_state=ACCEPTED` nghĩa là bài ĐÃ
đăng nhưng post-verifier timeout → ledger entry còn `reserved`, workbook chưa
tăng. Nếu KHÔNG xử lý, phiên sau:
`next_video_number = workbook["Video Đã Đăng"] + 1` chọn lại chính video đã live,
và stale-release (`reserve(stale_after_seconds=1800)`) sẽ release entry `reserved`
cũ → **đăng nhầm lại video đó lần 2**. Bắt buộc finalize + bump.

## 1. Xác nhận video thật đã lên (bằng chứng)
Mở `runs/run_<serial>_<ts>/post-published-surface.png` qua `vision_analyze`:
- Profile có menu **Ghim lên đầu / Đặt ở chế độ riêng tư / Chia sẻ** trên video = video live (menu này chỉ hiện khi video đã đăng thành công).
- Kèm timestamp "N giây trước" + nút boost quảng cáo đỏ.

## 2. Finalize entry ledger reserved → verified_success
Entry files: `D:\CodexRuntime\tiktok-video\idempotency\media-fingerprints\<sha256>.json`
(mỗi file chứa key/machine/video_number/status/source_path/run_id/target_account).

```python
import json
from pathlib import Path
from tiktok_workflow.media_fingerprint import (
    MediaFingerprintLedger, MediaFingerprintReservation)

L = MediaFingerprintLedger(r'D:\CodexRuntime\tiktok-video')
# Lấy key từ việc khớp source_path/video_number/machine (KHÔNG gọi _identity_key với
# target_account giả — sai key → FileNotFoundError)
key = '<sha256>'  # json filename (bỏ .json)
p = L.directory / f'{key}.json'
e = json.load(open(p, encoding='utf-8'))
res = MediaFingerprintReservation(
    key=e['key'], sha256=e['sha256'], path=p, machine=e['machine'],
    target_account=e['target_account'], video_number=e['video_number'],
    run_id=e['run_id'])   # dùng run_id CỦA entry
out = L.finalize(res)     # → status verified_success
print(out['status'], out.get('verified_at'))
```

PITFALLS
- `finalize` require `reservation.path` là `pathlib.Path`, KHÔNG phải `str`.
- `finalize` check ownership: `run_id` phải khớp entry hiện tại (dùng `e['run_id']`, đừng tự bịa run_id).
- `_identity_key` chứa `target_account` trong key (sha256 + matcher + machine) — truyền `'@account'` giả → key khác → FileNotFound.

## 3. Bump workbook "Video Đã Đăng"
```python
import shutil, datetime
import openpyxl
p = r'D:\OneDrive\Tiktok\Tik1.xlsx'
shutil.copy2(p, p.replace('.xlsx', f'.bak-{datetime.datetime.now():%Y%m%d_%H%M}.xlsx'))
wb = openpyxl.load_workbook(p, data_only=False); ws = wb['TaiKhoan']
h = [c.value for c in ws[1]]; vd = h.index('Video Đã Đăng')
for row in ws.iter_rows(min_row=3):
    if row[0].value == <MACHINE>: row[vd].value = <new_count>  # nâng lên số video đã đăng
wb.save(p)
```
Sheet `TaiKhoan`, cột A = `Máy`, cột H = `Video Đã Đăng`. Worker không tự update vì report MANUAL_REVIEW.

## 4. Verify đã đóng lỗ
Sau finalize: `reserve()` cho video đó sẽ raise `MediaFingerprintDuplicateError`
(chặn đăng lại) thay vì release. Đã apply máy 10 (video 7), 22 (6), 30 (6) — confirmed.