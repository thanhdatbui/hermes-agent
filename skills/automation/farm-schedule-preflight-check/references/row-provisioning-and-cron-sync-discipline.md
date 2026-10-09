# Kỷ Luật Reg Bù Hàng Tài Khoản & Cơ Chế Provisioning On-Demand (12/09/2026)

## 1. Bản Chất Kiến Trúc
- **Không còn khái niệm "Reg sau ca nuôi":** Mọi cơ chế reg bù hoặc auto-task ad-hoc sau khi phiên nuôi kết thúc đã bị loại bỏ hoàn toàn để bảo vệ thời gian làm mát thiết bị và chống xung đột lock với ca tiếp theo.
- **Cơ chế chính thức:**
  1. **Preflight On-Demand trước ca nuôi (`tiktok_runner.py`):** Tự động gọi `ensure_row_accounts.py <row>` trước khi spawn feed session (~5 phút trước ca nuôi). Nếu Row đó thiếu acc trên bất kỳ máy nào (`ID = None` trong `taikhoan_run_safe.xlsx` hoặc `taikhoan_dat_v2_updated .xlsx`), script kiểm tra kho mail sạch (`gmail_clean_v2.xlsx`):
     - Nếu có sẵn mail: Kích hoạt batch reg riêng để bù nick vào đúng slot thiếu.
     - Nếu kho mail chưa có sẵn (`Cần mua mail`): Script tạm dừng/hoãn reg bù mà không can thiệp bừa bãi.
  2. **Safe-Skip Graceful trong Feed Session:** Khi phiên nuôi khởi chạy (Phiên 1 hoặc Phiên 2), nếu máy vẫn chưa có tài khoản cho Row đó, worker sẽ tự động bỏ qua an toàn với log `account row <row> is empty (no username) for machine <M>, skipping` (`final_status: config-error`, `blocker_type: script-blocker`). Đây là hành vi safe-skip thiết kế có chủ đích, không làm đứt đoạn hay crash cả batch của 79 máy còn lại.
  3. **Đã xóa hoàn toàn cron đêm:** Cron `night-chain-reg-pipeline` (01:00 AM) và toàn bộ nhánh Reg TikTok ban đêm đã bị loại bỏ triệt để. Tuyệt đối không phục hồi hay nhắc lại.

## 2. Quy Tắc Bắt Buộc Về Vị Trí Slot (Row-Discipline Invariant)
- **CẤM TUYỆT ĐỐI điền dồn lấp các slot trước:**
  - Nếu thiếu acc ở Row 6, tài khoản mới reg bù **BẮT BUỘC phải được điền chính xác vào Row 6** (tương ứng với dòng slot 6 trong `taikhoan_dat_v2_updated .xlsx` và `taikhoan_run_safe.xlsx`).
  - Tuyệt đối không để thuật toán tự động tìm slot trống đầu tiên (first-empty) rồi điền vào Row 5 hay các row trước đó khi các row đó chưa tới ca hoặc đang được để trống có chủ đích.
- **Khai báo trong `ensure_row_accounts.py`:**
  - Hàm `apply_results(row)` bắt buộc nhận tham số `row`.
  - Đọc ma trận dòng từ sheet `'Tài Khoản'`, tính toán chính xác `target_excel_row` và `target_tik` cho đúng `row` đó và ghi đè vào kết quả JSON trước khi gọi `apply_deferred_tracking_results.py`.

## 3. Quản Lý Đồng Bộ Cron Deployment (Cross-Host & Local Sync)
- Khi chỉnh sửa hoặc cải tiến bất kỳ script cron nào tại repo:
  - Nguồn chuẩn lưu tại: `D:\Taadaa\Hermes\deploy\hermes-home\scripts\`
  - Kho OneDrive dùng chung (share toàn farm & Admin): `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\`
  - Thư mục nạp runtime của Hermes Cron trên máy hiện tại: `C:\Users\<user>\AppData\Local\hermes\scripts\`
- **BẮT BUỘC:** Sau khi sửa hoặc pull bản mới trên repo, phải copy đồng bộ ngay vào cả thư mục `AppData\Local\hermes\scripts\` lẫn `Taadaa_Sync_Shared\hermes-cron\scripts\`.
- **Python Environment trong Cron Script:** Các cron script gọi subprocess bắt buộc sử dụng interpreter farm chuẩn (`D:\Taadaa\python-envs\automation\Scripts\python.exe` hoặc helper `target_python()`). Tuyệt đối không dùng `sys.executable` vì môi trường venv mặc định của Hermes Agent thiếu các package như `openpyxl`, dẫn đến lỗi ngầm im lặng.
