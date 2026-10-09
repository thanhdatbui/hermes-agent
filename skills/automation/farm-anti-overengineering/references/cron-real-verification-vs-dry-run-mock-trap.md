# Cron Real Verification vs Dry-Run Mock Trap

## 1. Bài học từ sự cố (Incident Lesson)
- **Sự cố**: Khi sửa lỗi watchdog chuỗi sau ca trưa (`post_noon_chain_watchdog.py`), Coordinator chạy lệnh `--dry-run` thấy in ra `TOTAL=40 SUCCESS=40` tưởng là thành công và vội vàng báo cáo chốt phiên. Thực chất `--dry-run` chỉ là chuỗi string mock hardcode, hoàn toàn không gọi vào script thực tế.
- **Hậu quả**: Lỗi ngầm bên trong chưa hề được kiểm chứng:
  1. Subprocess chạy từ thư mục gốc `C:\Users\Kibe` thiếu `cwd` dẫn đến load file `gmail_reg_v10.py` rác trong home directory gây `AttributeError`.
  2. Runner 2FA bị truyền sai tham số CLI (`--all-online`, `--workers` thay vì `--live`, `--max-workers`).
  3. Kẹt dead-owner device locks làm watchdog tự động skip âm thầm.

## 2. Kỷ luật kiểm thử Cron (Anti-Overengineering & Reality Check)
- **CẤM TUYỆT ĐỐI nghiệm thu bằng mock / dry-run**: Việc in ra vài dòng giả lập không có giá trị bảo đảm chất lượng.
- **Canary máy thật ngay trong phiên**:
  - Khi thiết lập hoặc sửa chữa bất kỳ cron nào, BẮT BUỘC chạy thử nghiệm thật trên 1-2 máy đang rảnh.
  - Sử dụng cờ `--force` để bypass điều kiện khung giờ nếu đang test ngoài giờ chạy chính thức của cron.
- **Xác thực toàn vẹn môi trường (Execution Environment)**:
  - Luôn đảm bảo `cwd` được truyền tường minh vào `subprocess.run(..., cwd=str(REPO_DIR))` để tránh ô nhiễm `sys.path`.
  - Luôn xác nhận luồng ghi dữ liệu quan trọng (ghi token, pass, mã 2FA) được commit vào file Excel đích và có kiểm tra xác thực sau khi ghi (`reopen_verify`).
- **Luôn gửi báo cáo**: Mọi cron watchdog bắt buộc phải xuất thông tin ra stdout để cơ chế cron auto-delivery gửi report về đúng kênh Telegram đã cấu hình.
