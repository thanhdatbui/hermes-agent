# Quy Tắc Nguồn Dữ Liệu Độc Nhất (Excel Source of Truth) Cho Feed Session

## 1. Nguyên Tắc Cốt Lõi
- **`taikhoan_run_safe.xlsx` là truth duy nhất** cho toàn bộ 80 máy và 6 rows (tài khoản).
- Phiên nuôi feed đọc trực tiếp từ `taikhoan_run_safe.xlsx` theo số máy (`--machines 1,2..80`) và Row tài khoản (`--account-row-index 1..6`).

## 2. Cron Sync (`taikhoan-run-safe-sync`)
- Chỉ làm duy nhất nhiệm vụ đồng bộ 1-chiều từ `taikhoan_dat_v2_updated .xlsx` (+ `Tik1..Tik6.xlsx`) sang `taikhoan_run_safe.xlsx`.
- CẤM tự ý `rmtree` xoá thư mục `cohorts/` hay `manifests/` của ngày hiện tại khi farm đang có phiên chạy ngầm (tránh lỗi `cohort artifact assignment digest mismatch`).

## 3. Chạy Ca / Phiên Nuôi Acc
- Lệnh chạy chuẩn đọc trực tiếp Excel:
  ```powershell
  powershell -File "scripts/run-feed-session.ps1" -Row <1..6> -Machines 1,2..80 -AccountWorkbook "D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx" -Run
  ```
- Hoặc qua Python:
  ```bash
  python .\python_runner\run_tiktok.py --mode multi-machine-feed-session --machines 1..80 --account-workbook "D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx" --account-row-index <1..6>
  ```
