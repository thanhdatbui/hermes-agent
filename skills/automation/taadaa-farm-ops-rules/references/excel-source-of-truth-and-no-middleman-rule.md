# Quy Tắc Nguồn Dữ Liệu Độc Nhất (Excel Source of Truth) & Cấm Tự Chế Trung Gian

## 1. Nguyên Tắc Cốt Lõi
- **`taikhoan_run_safe.xlsx` là truth duy nhất** cho toàn bộ 80 máy và 6 rows (tài khoản).
- Toàn bộ các luồng tự động hoá trên farm (Nuôi Feed, Follow, Upload) phải **đọc trực tiếp từ file Excel**, không được tự chế thêm tầng logic/manifest trung gian làm phát sinh lỗi gián đoạn.

## 2. Cron Sync (`taikhoan-run-safe-sync`)
- **Nhiệm vụ duy nhất:** Đồng bộ 1-chiều dữ liệu từ `taikhoan_dat_v2_updated .xlsx` (+ `Tik1..Tik6.xlsx`) sang `taikhoan_run_safe.xlsx`.
- **TUYỆT ĐỐI CẤM:**
  - CẤM tự sinh file JSON trung gian (`hermes_cron_source_config.json`, `feed_state.json`...).
  - CẤM tự ý `shutil.rmtree` xoá thư mục `cohorts/` hay `manifests/` của ngày hiện tại khi farm đang có phiên chạy ngầm (gây lỗi `cohort artifact assignment digest mismatch`).
  - CẤM can thiệp vào tiến trình runtime của runner.

## 3. Cron Nuôi Acc (Feed Session)
- Khởi chạy runner đọc trực tiếp từ `taikhoan_run_safe.xlsx` theo số máy (`--machines 1,2..80`) và Row tài khoản (`--account-row-index 1..6`).
- Không phụ thuộc vào cohort artifact hay assignment manifest digest khi chạy thực tế trên máy thật.

## 4. Luồng Follow & Upload
- **Follow (`tiktok-follow`):** Đọc trực tiếp `taikhoan_run_safe.xlsx` qua `WorkbookMapping` lấy Machine, Serial, ID, Video count.
- **Upload (`Tiktok-video`):** Đọc trực tiếp các file `Tik1.xlsx` .. `Tik6.xlsx` theo hàng và số video đã đăng.
