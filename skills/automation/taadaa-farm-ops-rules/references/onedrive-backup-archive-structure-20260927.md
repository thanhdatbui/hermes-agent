# Quản trị Thư mục OneDrive TaadaaData & Lưu trữ Backup

## Quy hoạch thư mục dữ liệu TaadaaData (Kibe & Admin)
Để tránh thư mục làm việc chính trên OneDrive bị ngập tràn hàng trăm file backup phiên bản (`.bak`, `.backup_before_*`, `tx_snap_*`) làm che khuất các file dữ liệu đang vận hành thực tế:

### 1. File dữ liệu Canonical (Chỉ giữ ở thư mục gốc `D:/OneDrive/TaadaaData/kibe/`):
- `taikhoan_dat_v2_updated .xlsx` (Database tài khoản tổng)
- `taikhoan_run_safe.xlsx` & `taikhoan_run_safe_combined.xlsx`
- `Tik1.xlsx` đến `Tik8.xlsx`
- `PROXYgandienthoai.xlsx`
- `master_gmail_manager.xlsx` & `gmail_clean_v2.xlsx`
- `gmail_live_tong.txt` & `gmail_die_tong.txt`
- `tiktok_stats_farm.xlsx`

### 2. Thư mục gom lưu trữ toàn bộ Backup:
- Tất cả các file sao lưu tự động, snapshot theo giờ, bản backup trước khi swap/clean BẮT BUỘC gom về:
  `D:/OneDrive/TaadaaData/kibe/workbook-backups/archive_history/`
- Tuyệt đối không sinh file backup trực tiếp đè lên thư mục gốc mà không chuyển vào `archive_history/`.
