# Quy Chuẩn Báo Cáo Batch Cron & Watchdog: Gom Làm 1 Báo Cáo Duy Nhất & Triệt Tiêu Rò Rỉ Stdout

## 1. Bài học thực tế & Phản ứng từ User (2026-09-23)
Trong quá trình vận hành batch upload avatar tự động sau ca tối, watchdog chạy cuốn chiếu lần lượt qua các Tik (Tik 7, Tik 8, Tik 3, Tik 4...). Sau khi hoàn tất mỗi Tik, watchdog gọi script tracker phụ trợ (`tiktok_account_tracker.py --machines ...`) để cập nhật lại trạng thái avatar vào SQLite DB.
Hàm cập nhật này lại in toàn bộ bảng tổng kết của tracker ra stdout (`print(f"[TRACKER RESCAN stdout]:\n{stdout_clean}")`).
Do cronjob được cấu hình ở chế độ `no_agent: true`, bất kỳ dữ liệu nào xuất hiện tại `sys.stdout` đều bị scheduler đóng gói và gửi thẳng vào nhóm Telegram Farm Alert.

Hậu quả:
- Người dùng liên tục nhận được các báo cáo lẻ tẻ: 16 máy (126 nick), 9 máy (69 nick)...
- Gây hoang mang nghiêm trọng vì tưởng nhầm toàn farm 160 máy bị rớt mạng hay lỗi chỉ còn 16 máy.
- Người dùng bức xúc phản hồi gắt:
  > *"ủa cron upload ava thì gom làm 1 sau khi chạy xong hết r báo, cứ báo xàm lồn gì thế này"*

## 2. Ba Nguyên Tắc Bất Biến Khi Vận Hành Batch Cronjob & Watchdog

### Nguyên tắc 1: CẤM BÁO CÁO LẺ TỪNG ĐỢT / TỪNG TIK
- Đối với các tác vụ chạy theo mẻ, theo vòng đời nhiều Tik (Upload Avatar, Render Video, Upload Video, Reg Hotmail/Gmail):
  - **TUYỆT ĐỐI CẤM** gửi tin nhắn báo cáo sau mỗi mẻ lẻ hoặc sau từng Tik riêng biệt.
  - Người dùng không có nhu cầu nhận 8-10 tin nhắn rác ngắt quãng trong đêm.

### Nguyên tắc 2: GOM LÀM 1 BÁO CÁO DUY NHẤT TOÀN FARM
- Watchdog phải chạy ngầm **hoàn toàn im lặng (100% Silent)** trong suốt quá trình xử lý các batch lẻ.
- **CHỈ ĐƯỢC PHÉP BÁO CÁO DUY NHẤT 1 LẦN** khi:
  1. Tất cả các Tik đã hoàn tất 100% (`all_done=True`), HOẶC
  2. Đã bước qua mốc kết thúc khung giờ ca làm việc (ví dụ sau 23:45 đối với ca tối).
- Báo cáo tổng kết bắt buộc phải gộp số liệu toàn farm (tách 2 cụm Kibe và Admin rõ ràng nếu có), nêu rõ số acc thành công trong ca (+N acc mới) và phân cụm các mã lỗi chi tiết.

### Nguyên tắc 3: TRIỆT TIÊU 100% STDOUT TRUNG GIAN TRONG `no_agent: true` CRON
- Cơ chế vận hành của Hermes Cronjob `no_agent: true`:
  - `stdout != ""` ➔ Tự động gửi tin nhắn đến Telegram đích.
  - `stdout == ""` (0 byte) ➔ Coi như phiên chạy bình thường, hoàn toàn im lặng.
- Mọi hàm phụ trợ, lệnh gọi subprocess (gọi ADB, git sync, tracker rescan, PowerShell launcher) bên trong script watchdog:
  - **CẤM TUYỆT ĐỐI** dùng lệnh `print(...)` in kết quả trung gian ra stdout.
  - Nếu cần log điều tra, bắt buộc ghi vào `sys.stderr.write(...)` hoặc ghi vào file log riêng biệt trong thư mục runtime.
  - Script watchdog chỉ được phép in ra `sys.stdout` tại duy nhất một điểm (Single Point of Output): hàm phát báo cáo tổng kết cuối ca.
