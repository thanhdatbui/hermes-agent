---
name: cron-watchdog-anti-stagnation-architecture
description: "Kiến trúc và quy chuẩn thiết kế Watchdog/Cron chống bẫy vòng lặp bế tắc vô tận (Infinite Stagnation Loop), rolling cooldown và bảo toàn cuốn chiếu tài khoản."
version: 1.0.0
---
# Cron Watchdog Anti-Stagnation Architecture

## 1. Bản Chất Bệnh "Vòng Lặp Bế Tắc Vô Tận" (Infinite Stagnation Loop)
Khi xây dựng các watchdog / cron tự động nạp token, cứu session hoặc bật bảo mật 2FA cho kho tài khoản lớn (GPM Profiles, ChatGPT Web, 2FA Gmail, Codex):
- **Triệu chứng:** Script chạy liên tục hàng chục lần nhưng chỉ xử lý lặp đi lặp lại đúng 5–10 tài khoản lỗi, toàn bộ hàng trăm tài khoản khỏe mạnh phía sau bị bỏ rơi hoàn toàn.
- **Nguyên nhân gốc rễ (Stateless Query):**
  Hàm lấy ứng viên chỉ query đơn giản theo thứ tự tĩnh:
  `SELECT Id, Name FROM Profiles WHERE ... ORDER BY Id ASC LIMIT N`
  Khi N tài khoản đầu tiên gặp sự cố (văng session Google, Google bắt xác minh Galaxy S7, proxy die, Cloudflare block):
  1. Lần chạy 1: N tài khoản thất bại (0/N).
  2. Lần chạy 2 (5–15 phút sau): Vì N tài khoản này vẫn chưa hoàn tất, hàm query **LẠI TIẾP TỤC BỐC ĐÚNG N TÀI KHOẢN ĐÓ RA CHẠY LẠI**.
  3. Lặp lại vô hạn: Nuốt sạch tài nguyên, giam hãm hệ thống và nuốt log nếu không có cảnh báo Telegram.

---

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
