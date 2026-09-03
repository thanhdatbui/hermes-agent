# Cron Manifest, Journal Synchronization & Windows Locking Rules

## 1. Cơ chế Đồng Bộ Source Config ↔ Manifest ↔ Cohort ↔ Journal
Khi danh sách tài khoản trong `taikhoan_run_safe.xlsx` thay đổi (thêm máy mới, đổi nick, cập nhật số video):
- `source_revision` trong `hermes_cron_source_config.json` sẽ thay đổi theo hash SHA-256 mới.
- **Hiện tượng lỗi nếu không đồng bộ sạch:**
  1. `MANIFEST_IDENTITY_MISMATCH` / `ACTIVE_MANIFEST_CONFLICT`: Runner hoặc Watchdog phát hiện `source_revision` trong `ACTIVE.json` không khớp với `hermes_cron_source_config.json`.
  2. `cohort artifact assignment digest mismatch`: Runner tải file cohort được sinh từ manifest cũ nhưng đối chiếu với manifest mới.
  3. `JournalStore` từ chối append vì `manifest_sha256` trong các bản ghi journal cũ khác với snapshot hiện tại.

### Quy tắc xử lý chuẩn (Automated Invalidation & Race-Condition Guard)
1. **Kiểm tra runner active trước khi invalidation:**
   - Trong `scripts/hermes_taikhoan_sync_cron.py`, luôn gọi `is_feed_runner_active()` trước khi cập nhật `cron_source_config` hoặc dọn dẹp manifest.
   - Nếu có runner đang chạy, HOÃN (defer) việc tái tạo manifest sang tick kế tiếp để tránh phá vỡ SHA256 digest binding của các tiến trình con đang chạy.
2. **Bảo tồn thư mục Cohorts:**
   - Dọn sạch `manifests/YYYY-MM-DD`, `snapshot_bundles/YYYY-MM-DD` và `journal/*.jsonl`.
   - **TUYỆT ĐỐI KHÔNG xóa `cron-state/cohorts/YYYY-MM-DD`** vì các cohort artifact là dữ liệu bất biến lịch sử phục vụ đối soát và watchdog reporting.
3. Tự động gọi `tiktok_picker.py` để sinh ngay lập tức `manifest` và `ACTIVE.json` mới chuẩn theo 80 máy.

---

## 2. Quy tắc Đọc Trực Tiếp Excel taikhoan_run_safe.xlsx (Direct Workbook Execution)
Khi chạy trực tiếp qua `run-feed-session.ps1 -Row <row> -Machines <list>` không kèm `-CohortArtifact` và `-AssignmentManifest`:
- `flows/multi_machine_feed_session.py` tự động bypass `_apply_cohort_identity` (`cohort_bound = False`).
- Runner đọc trực tiếp dữ liệu từ `taikhoan_run_safe.xlsx` theo `account_row_index` (Row 1..6):
  + Ngày lẻ (1, 3, 5): Ca 1 (Row 1), Ca 2 (Row 3), Ca 3 (Row 5).
  + Ngày chẵn (2, 4, 6): Ca 1 (Row 2), Ca 2 (Row 4), Ca 3 (Row 6).
- Loại bỏ hoàn toàn rủi ro digest mismatch / manifest drift giữa các phiên.

---

## 2. Windows File Locking & Journal Path Case-Sensitivity Pitfall
Trên hệ điều hành Windows:
- Hệ thống tập tin không phân biệt hoa thường (`D:\Taadaa\...` và `d:\taadaa\...` trỏ cùng một file).
- Module `journal.py` quản lý thread-local locks qua `_HELD_LOCKS` dạng `set[str]`.
- **Anti-Pattern:** Nếu lưu key thô `str(path.resolve())`, việc một caller dùng chữ hoa và caller khác dùng chữ thường sẽ dẫn đến:
  - `_read_unlocked()` báo `RuntimeError: journal lock required`.
  - `msvcrt.locking()` ném `OSError: [Errno 36] Resource deadlock avoided` hoặc `PermissionError: [Errno 13] Permission denied`.

### Giải pháp chuẩn
1. Luôn chuẩn hóa khóa đường dẫn:
   ```python
   key = str(path.resolve()).lower()
   ```
2. Auto-reset journal khi manifest thay đổi: Trong `_read_unlocked()`, nếu đọc dòng đầu tiên phát hiện `manifest_sha256 != self.snapshot.manifest_sha256`, tự động `self.path.unlink(missing_ok=True)` và trả về `[]` thay vì ném exception làm gián đoạn cron runner.

---

## 3. Quy tắc Ánh Xạ Serial Thiết Bị Mở Rộng (Máy 75 – 80)
Bảng `EXTRA_MACHINES` trong `scripts/sync-safe-workbook.py` phải khớp chính xác 1-1 với cột `device ID` (cột 10) trong `taikhoan_dat_v2_updated .xlsx`:
- Máy 75: `ce011711d4cd802905`
- Máy 76: `9885b64d56305a3731`
- Máy 77: `ce05160595e7953b04`
- Máy 78: `ce0916090a9d320a01`
- Máy 79: `ce0516059d279f3e03`
- Máy 80: `ce061606cd45950405`

*Lưu ý:* Tuyệt đối không hoán đổi serial giữa các máy (ví dụ gán nhầm serial M75 sang M79). Picker sẽ phát hiện xung đột `MAPPING_CONFLICT` (một serial gán cho nhiều máy hoặc một máy có nhiều serial) và fail-closed dừng tạo manifest.
