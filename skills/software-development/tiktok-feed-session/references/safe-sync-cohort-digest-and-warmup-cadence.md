# Quy Trình Đồng Bộ Nguồn Cron Trực Tiếp Từ taikhoan_run_safe.xlsx & Xử Lý Cohort Digest Mismatch

## 1. Đồng bộ trực tiếp từ taikhoan_run_safe.xlsx cho 80 máy (1–80)
- `taikhoan_run_safe.xlsx` (Accounts sheet) là nguồn chân lý duy nhất (Single Source of Truth) cho 80 máy x 6 rows = 480 slots.
- Khi đồng bộ:
  1. Đọc trực tiếp `taikhoan_run_safe.xlsx` qua `scripts/hermes_taikhoan_sync_cron.py`.
  2. Lọc bỏ các ID rác (`ghjfghj`, `none`, `null`), ID trống, hoặc ID chứa ký tự cấm (`\/:= `).
  3. Cập nhật đồng bộ `hermes_cron_source_config.json`, `feed_state.json`, và `post_state.json` với state_revision chuẩn `sha256`.

## 2. Invariant: Tái tạo Manifest & Dọn Cohort cũ khi Source Config thay đổi
- **Hiện tượng lỗi nếu không dọn:**
  + `tiktok_watcher.py` (chu kỳ 15 phút): Báo lỗi `ValueError: MANIFEST_IDENTITY_MISMATCH` do `source_revision` mới khác với manifest cũ đầu ngày.
  + Runner (`multi-machine-feed-session.py`): Đọc file `cohort-v1-*.json` cũ trong `runtime/kibe/cron-state/cohorts/<day>/`, đối soát thấy `manifest_digest` bị lệch và ngắt fail-safe đồng loạt 80 máy trong 28s (`cohort artifact assignment digest mismatch`).
- **Quy tắc bắt buộc khi sync:**
  + Xóa sạch `runtime/kibe/cron-state/manifests/<today>/`.
  + Xóa sạch `runtime/kibe/cron-state/snapshot_bundles/<today>/`.
  + Xóa sạch `runtime/kibe/cron-state/cohorts/<today>/`.
  + Gọi `tiktok_picker.py` tái tạo manifest mới ngay lập tức.

## 3. Lịch Phân Bổ Ca Nuôi Mới & Quy Chuẩn Warmup Nick Mới (Row 5 & Row 6)
- **Lịch phân chia LANES theo ngày Chẵn / Lẻ:**
  + **Ngày Lẻ (Lane B):** Ca 1 (Row 1) + Ca 2 (Row 3) + Ca 3 (Row 5 - Warmup).
  + **Ngày Chẵn (Lane A):** Ca 1 (Row 2) + Ca 2 (Row 4) + Ca 3 (Row 6 - Warmup).
- **Lộ trình Warmup chuẩn 20 ngày (10 ngày tuổi thực tế):**
  + **Giai đoạn 1 (Ngày 1 -> Ngày 10 lịch = 5 ngày chạy thực tế):** Chỉ lướt Feed thuần (15 phiên lướt), 0 đăng video, 0 follow. Tích lũy cookie và định hình niche.
  + **Giai đoạn 2 (Ngày 11 -> Ngày 20 lịch = 5 ngày chạy thực tế tiếp theo):** Vừa lướt feed vừa đăng 1 video/ngày ở Phiên 3 (đủ 5 video/nick). Vẫn khóa follow chéo (Gate < 5 video).
  + **Giai đoạn 3 (Từ Ngày 21 lịch trở đi):** Nick đã đạt >= 5 video và trust cứng -> tự động mở Gate Follow chéo ngoài farm (Module 2).
