# Taikhoan Run Safe Direct Cron Sync & Manifest Regeneration Protocol (01/09/2026)

## 1. Nguồn Sự Thật Duy Nhất: `taikhoan_run_safe.xlsx`
- Loại bỏ toàn bộ các bước tạo config trung gian thủ công rải rác: `taikhoan_run_safe.xlsx` (D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx) là nguồn sự thật duy nhất cho toàn bộ 80 máy (1..80), mỗi máy 6 slots (480 rows).
- Script `scripts/hermes_taikhoan_sync_cron.py` (chạy định kỳ qua cron `taikhoan-run-safe-sync` mỗi 5 phút) tự động đồng bộ trực tiếp từ `taikhoan_run_safe.xlsx` sang `hermes_cron_source_config.json`, `feed_state.json`, và `post_state.json`.

## 2. Invariant: Ánh Xạ 1:1 Serial & Chống Lỗi `MAPPING_CONFLICT`
- `SourceConfig._validate_machine_serials` bắt buộc quan hệ 1-1 chặt chẽ giữa `machine` và `serial`:
  - 1 machine chỉ được gán đúng 1 serial duy nhất.
  - 1 serial không được xuất hiện trên 2 machine khác nhau.
- Bảng serial cho dàn máy mở rộng (M75..M80) trong `scripts/sync-safe-workbook.py` (`EXTRA_MACHINES`) phải khớp chính xác:
  - M75: `ce011711d4cd802905`
  - M76: `9885b64d56305a3731`
  - M77: `ce05160595e7953b04`
  - M78: `ce0916090a9d320a01`
  - M79: `ce0516059d279f3e03`
  - M80: `ce061606cd45950405`
- Tuyệt đối không hardcode đảo lộn serial giữa các máy (trước đây M75 bị gán serial M79, M76 bị gán serial M78...), tránh gây exception `ValueError: MAPPING_CONFLICT` làm nghẽn picker.

## 3. Atomic Manifest & Cohort Regeneration Khi Nguồn Thay Đổi
- Khi `hermes_cron_source_config.json` thay đổi, chữ ký `source_revision` sẽ thay đổi.
- Nếu không tái tạo manifest và dọn cohort cache, hai lỗi nghiêm trọng sẽ xảy ra:
  1. `tiktok_watcher.py` (chạy mỗi 15 phút) đối soát thấy `source_revision` mới khác manifest cũ trong ngày -> văng exception `ValueError: MANIFEST_IDENTITY_MISMATCH`.
  2. Runner khởi động đọc cohort cache cũ -> đối soát thấy `manifest_digest` bị lệch -> kích hoạt fail-safe dừng 80 máy đồng loạt với lỗi `[cohort-identity] machine N cohort target mismatch: cohort artifact assignment digest mismatch` và bắn Farm Alert giữ hiện trường.
- **Quy trình tái tạo chuẩn tự động (đã tích hợp vào sync cron):**
  1. Xóa thư mục manifest ngày hiện tại: `runtime/kibe/cron-state/manifests/YYYY-MM-DD`.
  2. Xóa thư mục snapshot bundles ngày hiện tại: `runtime/kibe/cron-state/snapshot_bundles/YYYY-MM-DD`.
  3. Xóa thư mục cohort cache ngày hiện tại: `runtime/kibe/cron-state/cohorts/YYYY-MM-DD`.
  4. Chạy `tiktok_picker.py` với biến môi trường `HERMES_CRON_PICKER_ENABLED=1` để sinh `ACTIVE.json` và manifest mới đồng bộ 100% với `source_revision`.

## 4. Lịch Phân Bổ Ca Nuôi Mới & Lộ Trình Warmup Cho Row 5, 6
- **Phân bổ LANES theo ngày Chẵn / Lẻ (Cập nhật 01/09/2026):**
  - **Ngày Lẻ (Lane B):** Ca 1 (06:00) = **Row 1** + Ca 2 (12:30) = **Row 3** + Ca 3 (19:00) = **Row 5** `(1, 3, 5)`.
  - **Ngày Chẵn (Lane A):** Ca 1 (06:00) = **Row 2** + Ca 2 (12:30) = **Row 4** + Ca 3 (19:00) = **Row 6** `(2, 4, 6)`.
  - Row 1 và Row 2 chỉ nuôi Ca Sáng (Block 1), nhường Ca Tối (Block 3) để nuôi warmup Row 5 và Row 6.
- **Lộ trình Warmup 20 ngày cho Row 5, 6 (chạy xen kẽ 2 ngày 1 lần = 10 ngày hoạt động thật):**
  - **10 ngày đầu (5 ngày chạy thực tế):** Chỉ lướt Feed thuần (0 đăng video, 0 follow).
  - **10 ngày tiếp theo (5 ngày chạy thực tế):** Lướt Feed + Đăng 5 video đầu tiên (mỗi ngày 1 video ở Phiên 3, Gate follow vẫn khóa vì < 5 video).
  - **Từ ngày 21 trở đi:** Bắt đầu mở Gate Follow chéo ngoài farm (Module 2) khi nick đã đủ trust và có $\ge 5$ video.
