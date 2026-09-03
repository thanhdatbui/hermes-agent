# Safe Workbook Cron Sync & Manifest Reconciliation

## Single Source of Truth (`taikhoan_run_safe.xlsx`)
- **Nguyên tắc cốt lõi:** Không tạo các file cấu hình trung gian hay workbook trùng lặp. Bảng `taikhoan_run_safe.xlsx` là sự thật duy nhất cho danh sách nick chạy farm.
- **Quy trình đồng bộ trực tiếp:**
  + `scripts/hermes_taikhoan_sync_cron.py` đọc trực tiếp từ `taikhoan_run_safe.xlsx`.
  + Tự động map đủ 80 máy (1–80) x 6 slots = 480 slots.
  + Tự sinh `hermes_cron_source_config.json`, `feed_state.json`, `post_state.json` với `state_revisions` và `source_revision` đầy đủ, chuẩn xác.

## Atomic Manifest & Journal Invalidation on Source Change
- **Vấn đề:** Khi `source_config` thay đổi (`source_revision` mới), nếu các file trạng thái cũ còn tồn tại:
  1. `tiktok_watcher.py` báo lỗi `ValueError: MANIFEST_IDENTITY_MISMATCH` vì active manifest cũ mang `source_revision` khác.
  2. `tiktok_runner.py` báo lỗi `ValueError: ACTIVE_MANIFEST_CONFLICT` hoặc `ValueError: cohort artifact assignment digest mismatch` vì cohort/journal mang `manifest_digest` cũ.
  3. `JournalStore` báo lỗi `MANIFEST_IDENTITY_MISMATCH` nếu file `.jsonl` cũ chứa `manifest_sha256` khác với manifest mới.
- **Quy tắc xử lý bắt buộc khi `source_config` thay đổi:**
  Script đồng bộ phải tự động dọn sạch các thư mục sau cho ngày hiện tại trước khi tái tạo manifest mới:
  + `runtime/kibe/cron-state/manifests/<day>/`
  + `runtime/kibe/cron-state/snapshot_bundles/<day>/`
  + `runtime/kibe/cron-state/cohorts/<day>/`
  + `runtime/kibe/cron-state/journal/*.jsonl`
  + Tự động kích hoạt `tiktok_picker.py` ngay trong bước sync để xuất bản `ACTIVE.json` mới đồng bộ.

## Windows Path & File Locking Constraints (`msvcrt` / `process_lock`)
- **Case Sensitivity on Windows:** Đường dẫn file trên Windows không phân biệt hoa thường. Khi lưu path vào `_HELD_LOCKS` hoặc kiểm tra lock `process_lock` / `JournalStore`, bắt buộc phải chuẩn hóa `str(path.resolve()).lower()`.
- **Safe LK_UNLCK Guard:** Không bao giờ gọi `msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)` trong `finally` nếu cờ `locked` là `False` (do `LK_LOCK` bị lỗi hoặc dính deadlock tránh `[Errno 36]`), tránh phát sinh `PermissionError: [Errno 13]`.
- **Auto-reset Stale Journals:** `JournalStore._read_unlocked()` phải kiểm tra `manifest_sha256` của event đầu tiên trong file `.jsonl`. Nếu không khớp với `self.snapshot.manifest_sha256`, tự động unlink file và trả về `[]` để tránh làm crash runner.
