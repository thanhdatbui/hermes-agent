# Hermes cron watchdog sync — example hoàn chỉnh (verified 2026-08-10)

Mẫu thực tế đã deploy: auto-sync `taikhoan_run_safe.xlsx` từ `taikhoan_dat_v2_updated .xlsx`
mỗi 1 phút qua Hermes cron, **im lặng khi source không đổi, báo 1 dòng khi sync**.

## Kiến trúc 3 lớp

```
Hermes cron job (no_agent=true, schedule "*/1 * * * *", repeat=0)
  └─ script = ~/.hermes/scripts/taikhoan_sync_cron_launcher.py   (LAUNCHER — bắt buộc ở đây)
       └─ subprocess → D:\Taadaa\tiktok-luot nuoi acc\scripts\hermes_taikhoan_sync_cron.py  (WRAPPER — trong repo, commit được)
            └─ subprocess → scripts/sync-safe-workbook.py  (script sync THẬT của repo)
```

Lý do 3 lớp: cron tool từ chối path tuyệt đối (`Script path must be relative to
~/.hermes/scripts/`), và repo script cần chạy bằng python env có `automation_core`
(`D:\Taadaa\python-envs\automation\Scripts\python.exe`), không phải python mặc định của Hermes.

## Launcher — `~/.hermes/scripts/taikhoan_sync_cron_launcher.py`

```python
"""Hermes cron launcher -> repo wrapper hermes_taikhoan_sync_cron.py."""
from __future__ import annotations
import subprocess, sys

PYTHON = r"D:\Taadaa\python-envs\automation\Scripts\python.exe"
WRAPPER = r"D:\Taadaa\tiktok-luot nuoi acc\scripts\hermes_taikhoan_sync_cron.py"

def main() -> int:
    completed = subprocess.run(
        [PYTHON, WRAPPER],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=300, check=False,
    )
    if completed.stdout: sys.stdout.write(completed.stdout)
    if completed.stderr: sys.stderr.write(completed.stderr)
    return completed.returncode

if __name__ == "__main__":
    raise SystemExit(main())
```

## Wrapper — repo `scripts/hermes_taikhoan_sync_cron.py`

Logic lõi (watchdog pattern):
1. Đọc source `taikhoan_dat_v2_updated .xlsx` → signature `(size, mtime_ns)`.
2. So với state JSON (`runtime/taikhoan-sync-state.json`): giống → `return 0` (stdout rỗng = cron silent).
3. Khác → gọi `sync-safe-workbook.py --source ... --output <safe>` cho từng file safe tồn tại.
4. Thành công → ghi state `{source_sig, last_sync}`, `print("Da dong bo ...")` (1 dòng, non-empty → Telegram).
5. Lỗi → KHÔNG cập nhật state (`last_error` giữ lại) → lần sau retry; in `TAIKHOAN_SYNC_ERROR:`.

Điểm quan trọng:
- Signature so sánh theo `mtime_ns` (nanosecond) — không bỏ sót thay đổi trong cùng giây.
- Cập nhật state SAU khi sync thành công; lỗi giữ state cũ → retry tự nhiên.
- File safe đích: `D:\Taadaa\tiktok-luot nuoi acc\data\taikhoan_run_safe.xlsx` + bản OneDrive
  `D:\OneDrive\codex_gmail_debug\tiktok-luot nuoi acc\data\taikhoan_run_safe.xlsx` (nếu tồn tại).

## Tạo job cron

```text
cronjob action=create
  name: taikhoan-run-safe-sync
  no_agent: true
  script: taikhoan_sync_cron_launcher.py     # relative — TUYỆT ĐỐI KHÔNG path đầy đủ
  schedule: */1 * * * *                       # cron expr; "1m" hay "every 1m" đều ra once!
  repeat: 0                                   # BẮT BUỘC — nếu không, repeat="once"
```

Sau create, READ response: phải thấy `"repeat": "forever"`. Nếu thấy `"repeat": "once"`,
update lại với `schedule="*/1 * * * *"` + `repeat=0` cho tới khi `"forever"`.

## Verify

1. Chạy tay wrapper trước khi tạo cron: lần 1 in báo sync (state chưa có), lần 2 stdout rỗng (exit 0).
2. `cronjob action=run` → response `last_status: ok`, `execution_success: true`.
3. Verify nội dung file safe: 80 máy × 6 slots, header `May | Device ID | ID` (dùng openpyxl
   `read_only=True, data_only=True` — tránh lock OneDrive).
4. Xóa Windows task cũ: `schtasks /Delete /TN TiktokLogIn-TaikhoanSync /F` (nếu task cũ là
   bản watcher trùng chức năng — tránh 2 cơ chế cùng ghi 1 file).

## Bài học liên quan từ session

- Script sync THẬT của farm là `sync-safe-workbook.py` (đọc header linh hoạt, EXTRA_MACHINES
  75-80, 6 slots/máy) — KHÔNG phải `tiktok-log-in/scripts/sync_taikhoan_run_safe.mjs` (bản cũ
  hard-code cột 10). Khi cần đồng bộ workbook, dùng script của repo tiktok-luot nuoi acc.
- Commit chỉ file của mình khi repo đang có diff chưa commit của worker khác
  (`git add scripts/hermes_taikhoan_sync_cron.py` riêng, KHÔNG `git add -A`); entry HANDOFF
  để worker kia commit chung (tránh kéo diff lạ vào commit của mình).
