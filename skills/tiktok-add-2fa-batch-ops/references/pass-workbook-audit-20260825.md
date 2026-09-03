# Audit pass workbook ↔ tracking artifacts (2026-08-25)

## Bối cảnh
Reg flow `social_reg_v1.py` chạy với `--defer-tracking-write`: success ghi pass vào JSON riêng, hẹn flush workbook sau. Một số nick không được flush → cột D (PASS) trống dù TikTok có pass thật. Batch add-2FA đọc pass từ workbook nên tưởng nick chưa có pass.

## Đường dẫn dữ liệu chuẩn
- Tracking artifacts: `D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\<timestamp>\batch_1\stt_<N>\tracking_result_stt<N>_<mail>.json`
  - Field quan trọng: `tiktok_id`, `password`, `tracking_row`, `written_at`, `email`, `serial`.
  - Mỗi lần reg/retry ghi file mới — lấy bản `written_at` mới nhất theo tiktok_id.
- Workbook: `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`, sheet `Tài Khoản`. Cột: A=Máy(stt), B=Tik, C=ID(tiktok_id), D=PASS, E=2FA, F=GMAIL.
- Reg nhập pass qua AdbKeyboard base64 (`ADB_KEYBOARD_INPUT_TEXT`) — KHÔNG qua shell → không thể bị ăn ký tự đặc biệt.

## Kết quả audit 25/08 (77 nick trong artifacts)
- Khớp tuyệt đối artifact ↔ workbook: 59 nick.
- Thiếu pass trong workbook (artifact CÓ): 7 nick — dauntscyw62 (row197), donieovhdvc (row61), juwancortese60 (row93), kylarpwp2ht (row21), lanawakt0mv (row85), lyndiaschles21 (row77), yaelmssp62p (row532).
- Không có trong workbook: lieuhoan03, tanglam024.
- Lệch pass 3 row (245 ancilqaz063, 613 rudysbhzx4h, 625 ruffumyxkvv): workbook giữ bản hợp lệ khác bản artifact cuối — do reg retry/rotate sau khi artifact ghi; KHÔNG tự đè workbook bằng artifact cho nhóm này.
- Pass legacy trong workbook (97 nick dạng `Ten@Ks` / `Ten+số+@`): là định dạng farm cũ, KHÔNG phải lỗi ghi.

## Quy trình backfill pass cho 1 lô nick
```python
import json, glob, shutil, openpyxl
from datetime import datetime
from pathlib import Path

WB = r'D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx'
# 1. Lấy artifact mới nhất mỗi tiktok_id
latest = {}
for f in glob.glob(r'D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\**\tracking_result_*.json', recursive=True):
    d = json.load(open(f, encoding='utf-8'))
    tid = d.get('tiktok_id')
    if tid and d.get('password'):
        if tid not in latest or d.get('written_at','') > latest[tid][0]:
            latest[tid] = (d.get('written_at',''), d['password'], f)
# 2. Với từng row cần vá: assert ID khớp, backup copy2, ghi cột D, reopen verify
```
- Backup bắt buộc trước mỗi lần ghi workbook (`shutil.copy2` sang thư mục backup riêng với timestamp).
- Sau ghi: reopen `data_only=True` kiểm tra cột D khác rỗng.

## Bài học escape khi test pass thủ công
`adb shell input text <pass>` đi qua shell MSYS — ký tự `& ! @ # ( ) $ ...` bị diễn giải. Escape giống `_input_password` (live_phase_b_adapter.py):
- space → `%s`; các ký tự trong `&<>|;()$\`"'!?#@*[]{}` → thêm `\` phía trước; gõ TỪNG ký tự một lệnh.
- Test sai cách này làm pass ĐÚNG báo "Mật khẩu sai" — đã từng kết luận nhầm trên m76 trước khi retest.

## Script tái sử dụng đã lưu
- `C:\Users\Kibe\AppData\Local\hermes\scripts\f2a_pass_backfill_9nicks.py` — backfill lô nick thiếu PASS (đã vá 9/9 ngày 25/08, backup từng lần ghi + verify reopen). Thay list `targets` để dùng cho lô khác.
- `C:\Users\Kibe\AppData\Local\hermes\scripts\f2a_verify_stuck_pass.py` + `f2a_stuck_machines.json` — verify pass workbook trên máy đang kẹt màn xác minh danh tính (escape chuẩn, lock + release đúng, không in pass ra output).
- Lưu ý API lock: `acquire_device_lock()` là keyword-only — gọi `acquire_device_lock(machine=M, serial=S, project='tiktok-add-bao-mat-f2a', user_authorized=True)`, KHÔNG truyền positional.
