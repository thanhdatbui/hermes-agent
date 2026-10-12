# Watchdog Report Sanitization & Error Reason Cleaning

## 1. Nguyên Tắc Cốt Lõi: Chống Leak Stacktrace & Raw Dumps Vào Telegram
- Khi preflight test mạng/proxy (`ifconfig.me`), timeout hoặc rớt ADB/USB, chuỗi lỗi thô (`reason` / exception message) có thể chứa:
  - Raw HTTP Headers: `GET /ip HTTP/1.1\nHost: ifconfig.me...`
  - Đường dẫn tuyệt đối Windows/Linux: `'C:\Program Files (x86)\xiaowei\tools\adb.exe'`
  - Ký tự xuống dòng `\n`, stacktrace nhiều dòng.
- CẤM TUYỆT ĐỐI đưa nguyên văn `reason` thô này vào các template tin nhắn Telegram tổng kết ca/phiên (`follow_session_watchdog`, `feed_session_watchdog`).

## 2. Tiêu Chuẩn Bộ Lọc `classify_error_reason`
Mọi watchdog tổng hợp báo cáo bắt buộc chuẩn hóa qua hàm phân loại 1 dòng:
- **Lỗi mạng / Egress Proxy / ifconfig:** Gom về `Nghẽn đường truyền Proxy / 4G` hoặc `Lỗi kết nối VPN/Proxy`.
- **Lỗi ADB / USB / Offline:** Gom về `Mất kết nối ADB/USB`.
- **Lỗi Wi-Fi / AP:** Gom về `Mất kết nối Wi-Fi (AP)`.
- **Lỗi Popup / Dialog / Lock:** Gom về `Popup/Dialog bất thường` / `Kẹt Device Lock`.
- **Xử lý chuỗi còn lại:** Cắt dòng đầu tiên, regex xóa toàn bộ đường dẫn nhị phân `[A-Za-z]:\\[^\s]+`, giới hạn tối đa <= 60 ký tự trên 1 dòng duy nhất.
