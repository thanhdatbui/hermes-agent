# Avatar smoke + lock takeover (2026-08-05 session detail)

## Chạy avatar smoke (chỉ up avatar, không đăng video)

Launcher `run_tiktok_upload_batch.ps1` KHÔNG có flag avatar-smoke → chạy trực tiếp python:

```bash
printf 'AVATAR-SMOKE\n' | env -i PATH="/c/Windows/system32:/c/Windows:/d/Taadaa/python-envs/automation/Scripts:/c/Users/Kibe/AppData/Local/Programs/Python/Python312" \
  HOME="C:\\Users\\Kibe" USERPROFILE="C:\\Users\\Kibe" PYTHONPATH="D:\\Taadaa\\Tiktok-video\\scripts" \
  "D:/Taadaa/python-envs/automation/Scripts/python.exe" -c \
  "import sys; sys.path.insert(0, r'D:\Taadaa\Tiktok-video\scripts'); from tiktok_workflow.run_post import main; sys.exit(main())" \
  --config "D:\\CodexRuntime\\tiktok-video\\config-machine-62.yaml" \
  --workflow-workbook "D:\\OneDrive\\Tiktok\\Tik1.xlsx" \
  --machine <N> --avatar-smoke --no-dry-run \
  --force-avatar-upload --force-avatar-machines <N> --avatar-source-root "D:\\video goc"
```

Pitfalls (đã dính 2026-08-05):
- Token xác nhận là **`AVATAR-SMOKE`**, không phải YES (YES → abort).
- Bắt buộc `env -i` sạch + `PYTHONPATH=scripts` — không env -i → `No module named
  automation_core.usb_popup` (hermes venv chèn sys.path).
- `-c "...; main()"` KHÔNG dùng `--` phân cách (argparse không nhận) — đặt args trực tiếp sau `-c`.
- Chạy qua `terminal(background=true, notify_on_complete=true)` — foreground 600s kill giữa run.

## Giành lock cross-consumer (user-authorized FULL_SCOPE_TAKEOVER)

Khi máy bị consumer khác (`tiktok-luot nuoi acc` feed session) giữ lock SỐNG
(pid sống, `owner_active=true`) nhưng user cho phép giành để up avatar:

1. Backup 2 file lock: `machine_<N>.lock.json` + `serial_<serial>.lock.json` → `backup_takeover_<date>/`.
2. Ghi evidence JSON vào `evidence_takeover_<date>/`:
   `{schema, taken_at, authorized_by, machines, previous_owner{pid,project,command,status}, backup_dir}`.
3. Xóa cả 2 file lock (chỉ xóa machine lock → vẫn SKIPPED_LOCKED).
4. Sau khi xong việc, lock mới do workflow tự quản lý (release khi DONE/handoff).

Lưu ý: feed scheduler `recovery_runtime` có thể re-acquire lock giữa chừng —
nếu máy bị feed lấy lại sau khi giành, kết quả workflow có thể FAILED
(`DEVICE_LOCK_FAILED`) hoặc app ở trạng thái lạ (SplashActivity kẹt).

## Fix AVATAR_UPLOAD_MENU_MISSING (commit 6c16368, COMPAT-AVATAR-004)

Fallback chain trong `_handle_ensure_avatar_impl`:
exact "Tải ảnh lên" → `text_contains="Tải ảnh"` → `text_contains="Thư viện"` →
`resource_id="g9u"` → fail-closed `AVATAR_UPLOAD_MENU_MISSING`.

Test: `test_avatar_upload_menu_falls_back_to_contains_variants` — mock trực tiếp
chuỗi `_tap_if_found` fallback, KHÔNG gọi `_handle_ensure_avatar_impl` nguyên khối
(nó đi nhiều nhánh: `_reserve_avatar_recovery`, `_looks_like_profile_root`,
`usb_popup_activity_present`, media_manager — mock thiếu 1 cái là fail khó debug).

## AVATAR_PICKER_NO_MATCH (sau khi menu fallback hoạt động)

Push avatar OK, mở picker OK nhưng similarity=0.047 < 0.600 → workflow không tự
chọn được tile. Đây là false-negative khung tròn ở giai đoạn PICKER. Máy giữ ở
picker; cần user xác nhận ảnh hiện đúng (user xác nhận > pixel correlation)
trước khi chỉnh ngưỡng/verify.
