# Dual-Cluster Local Cache & Remote Workbook Lock Resilience

## 1. Bản Chất Sự Cố Tranh Chấp File Trên Cụm Remote (Admin)
- **Kibe (Local USB Fleet):** Chỉ 1 PC Kibe đọc/ghi vào `D:\OneDrive\TaadaaData\kibe`, không có tranh chấp giữa các PC.
- **Admin (Remote LAN Fleet):** Thư mục `D:\OneDrive\TaadaaData\admin` được đồng bộ giữa PC Kibe và Admin-PC. Khi `single_writer_workbook_update` tạo file tạm `.{stem}.{rand}.xlsx` rồi dùng `os.replace`, tiến trình sync của OneDrive trên 2 máy có thể bắt lock vào file tạm hoặc file đích, gây `PermissionError / Access is denied` giữa chừng. File chính thức bị mất/xóa và để lại file rác dot-file.

## 2. Kiến Trúc Dual-Storage Local Cache Cho Remote Cluster
- **Cấm phụ thuộc đơn điểm vào đường dẫn OneDrive:** Mọi cụm remote (như Admin) bắt buộc phải cấu hình dual-output tương tự Kibe trong sync cron:
  - Output 1 (Local cache): `D:\Taadaa\runtime\admin\taikhoan_run_safe.xlsx`
  - Output 2 (OneDrive sync): `D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx`
- **Output Existence Invariant trong Cron Sync:**
  - Cron đồng bộ (`hermes_taikhoan_sync_cron.py`) CẤM chỉ so sánh signature của file nguồn (`source_sig` / `tik_sigs`) rồi thoát sớm (`return 0`).
  - BẮT BUỘC kiểm tra `outputs_exist = all(out.exists() for out in outputs if out.parent.exists())`. Nếu bất kỳ file safe nào biến mất khỏi đĩa, cron 5 phút phải tự động kích hoạt sync tái tạo ngay lập tức.

## 3. Account Workbook Resolver & Validated Fallback Trong Runner
- Trong runner điều phối (`tiktok_runner.py`), không truyền cứng `account_workbook`:
  - Dùng hàm giải quyết `_resolve_account_workbook(cluster)`.
  - Kiểm tra tính hợp lệ bằng `_is_valid_account_workbook(path)`: kiểm tra file tồn tại, dung lượng `> 0`, mở được qua `openpyxl`, có ít nhất một dòng dữ liệu hợp lệ (không rỗng).
  - Ưu tiên đường dẫn chính (`account_workbook` trên OneDrive).
  - Nếu đường dẫn chính hỏng/mất nhưng `runtime_root / "taikhoan_run_safe.xlsx"` hợp lệ: tự động fallback sang bản local cache và phát log WARNING `account_workbook_selected source=fallback`.
  - Nếu cả hai đều không hợp lệ: trả về rỗng (`""`), log ERROR `account_workbook_unavailable` và skip cụm an toàn (fail-closed), tuyệt đối không để runner crash hoặc chạy với file hỏng.

## 4. Chống Nuốt Cụm Máy Trong Báo Cáo Watchdog
- Khi một cụm máy bị skip hoặc không có lượt chạy, watchdog sinh block:
  `• Trạng thái: Không có lượt chạy nào trong phiên (Chưa chạy / Bị skip)`
- Trong các hàm lọc report theo module (như `format_follow_report_from_blocks`):
  - Nếu không tìm thấy header của module (`• Follow chéo`):
  - BẮT BUỘC phải có nhánh `else` giữ lại các dòng `• Trạng thái`.
  - Tuyệt đối không drop cả cụm ra khỏi báo cáo để đảm bảo tính minh bạch 100% telemetry cả 2 cụm máy gửi về Telegram.
