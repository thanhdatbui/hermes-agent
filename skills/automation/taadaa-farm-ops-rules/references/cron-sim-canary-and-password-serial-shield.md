# Quy Tắc Giả Lập Cron Live Canary & Chống Nhầm Password Vào Serial Máy

## 1. Quy tắc Giả lập Cron (Simulation & Canary Testing)
- **"Giả lập [giờ] rồi kích hoạt chạy"**: Là CHẠY THẬT (live run chạm thiết bị như khung giờ đó), TUYỆT ĐỐI CẤM nhầm thành cờ `--dry-run` hoặc trả về mock text tĩnh.
- **Kỷ luật nghiệm thu Cron**:
  - Mọi setup/sửa cron (dùng chung Kibe - Admin) BẮT BUỘC phải chạy thử end-to-end trên 1-2 máy thật đang rảnh (unlocked) ngay trong phiên trước khi bàn giao.
  - CẤM TUYỆT ĐỐI chỉ chạy dry-run rồi báo "đã xong/đã pass".
  - Nếu toàn farm đang bận (có live session giữ lock), BẮT BUỘC cắm watchdog tự động canh nhả lock để bắn lệnh thật nghiệm thu, không được báo cáo kết quả giả tạo.
  - Cron luôn luôn phải gửi report đầy đủ về Telegram/Home channels.

## 2. Guard Chống Nhầm Cột Password Vào Device Serial (`sync-safe-workbook.py`)
- Khi trích xuất serial từ file Excel nguồn (`taikhoan_dat_v2_updated .xlsx`), cột device ID có thể bị chèn nhầm ngày tháng (`23/08/2026`).
- **Anti-Pattern**: Quét tự do mọi ô trong hàng (`for c_str in row`). Vòng lặp này sẽ bốc nhầm cột `PASS MAIL` (`Emma2004wOjd`, `d93310aa`...) vì chúng khớp regex `^[A-Za-z0-9._:-]{4,80}$`, gán đè mật khẩu làm serial máy vào `taikhoan_run_safe.xlsx`. Hậu quả: Gây xung đột serial hàng loạt (`RuntimeError: Device map has conflicting valid serials`), làm văng toàn bộ batch launcher.
- **Best Practice**:
  - Chỉ kiểm tra fallback ở đúng cột kế tiếp (`serial_col + 1`) nếu cột đó tồn tại và khác `id_col`.
  - CẤM TUYỆT ĐỐI nhận giá trị trùng với `account_id` hoặc các cột nhạy cảm (ID, PASS, 2FA, MAIL, PASS MAIL).
  - Luôn chạy script kiểm tra sau khi build lại safe workbook: xác nhận đủ 640 dòng, 80 máy unique, 80 serial valid, 0 mật khẩu rò rỉ.
