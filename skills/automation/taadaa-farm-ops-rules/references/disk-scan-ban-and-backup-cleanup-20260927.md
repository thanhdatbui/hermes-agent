# Cấm Quét Đĩa Diện Rộng & Kỷ Luật Quy Hoạch Backup (2026-09-27)

## 1. Kỷ luật Quét Đĩa O(1) (Bất di bất dịch)
- **Sự cố thực tế**: Coordinator tự ý chạy `grep -rn "debug_40_pass_screen" /d/Taadaa/Tiktok_Reg/`, quét đụng các thư mục cache phân quyền chặt (`.pytest-basetemp-*`), gây lỗi *Permission denied* và làm terminal bị deadlock timeout 600s.
- **Quy tắc tuyệt đối**:
  - CẤM TUYỆT ĐỐI Coordinator và Worker tự ý chạy `grep -rn`, `find`, `os.walk`, `glob(recursive=True)`, `search_files` diện rộng trên toàn bộ ổ `D:/Taadaa` (kể cả `.ai-runs/`, `runtime/`).
  - CHỈ ĐƯỢC inspect đúng file/đường dẫn cụ thể đã biết trước O(1).
  - Khi cần tìm log/artifact: Dùng các công cụ chuyên dụng như `inspect_machine.py <N>`, đọc trực tiếp artifact theo timestamp phiên cụ thể hoặc đường dẫn chuẩn.

## 2. Quy chuẩn Kho Lưu Trữ Backup OneDrive
- **Vấn đề**: Các script tạo backup (`.bak`, `.backup_before_*`, snapshot) để lung tung tại thư mục gốc `D:/OneDrive/TaadaaData/kibe/`, làm rác thư mục khiến User không phân biệt được file data đang hoạt động.
- **Quy hoạch chuẩn**:
  - Thư mục gốc `D:/OneDrive/TaadaaData/kibe/` CHỈ CHỨA DUY NHẤT các file canonical đang hoạt động:
    - `taikhoan_dat_v2_updated .xlsx` (Database tổng của Farm)
    - `taikhoan_run_safe.xlsx`
    - `Tik1.xlsx` đến `Tik8.xlsx`
    - `PROXYgandienthoai.xlsx`
    - `master_gmail_manager.xlsx` & `gmail_clean_v2.xlsx`
  - Toàn bộ các file backup phiên bản, checkpoint lịch sử BẮT BUỘC gom gọn vào:
    `D:/OneDrive/TaadaaData/kibe/workbook-backups/archive_history/`
