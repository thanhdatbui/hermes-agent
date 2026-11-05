---
name: cron-rolling-cooldown-and-anti-stagnation
description: "Kỷ luật thiết kế cronjob/watchdog quét theo lô: chống bẫy lặp vô tận (Stateless Stagnation Loop), rolling cooldown cuốn chiếu và báo cáo Telegram fail-closed."
version: 1.0.0
---
# Cron Rolling Cooldown & Anti-Stagnation Discipline

## 1. Triệu Chứng Bệnh Lý: Bẫy Stateless Stagnation Loop
1. **Lặp vô tận ở nhóm lỗi đầu tiên:**
   - Các watchdog/cron quét tài khoản theo lô (như `cron_auto_feed_chatgpt_pool.py`, `post_morning_gmail_2fa_watchdog.py`) thường query DB với `LIMIT N` cố định (ví dụ 5, 10) kèm `ORDER BY Id ASC`.
   - Khi N tài khoản đầu tiên gặp sự cố (văng Google Auth, dính xác minh thiết bị Galaxy S7, checkpoint SMS/captcha, proxy die), batch thất bại.
   - Ở tick tiếp theo (sau 5-15 phút), vì DB vẫn ở trạng thái chưa hoàn thành, query lại bốc đúng N tài khoản lỗi đó ra thử lại.
   - Hậu quả: Watchdog rơi vào bẫy lặp vô tận, đè đúng các nick lỗi ra thử hàng trăm lần, bỏ rơi toàn bộ hàng trăm tài khoản khỏe mạnh phía sau.
2. **Khóa cứng bộ lọc quá hẹp:**
   - Script chỉ lọc duy nhất một nhóm nhỏ (ví dụ `GroupId == 10`), bỏ rơi các group lớn khác (như `GroupId == 1`) dù có tài khoản hợp lệ.
3. **Nuốt log khi thất bại toàn bộ:**
   - Script dùng điều kiện `if success_list:` để gửi báo cáo. Khi fail toàn bộ (`success_list = []`), script im lặng hoàn toàn, không báo Telegram, khiến Operator không biết hệ thống bị kẹt.
4. **Bẫy Kẹt Vĩnh Viễn Đa Giai Đoạn (Multi-Stage Pipeline Stagnation):**
   - Khi supervisor quản lý nhiều stage nối tiếp (Login -> Reg -> Change Info), nếu nhánh unblock 48h chỉ mở cho stage đầu, các tài khoản fail ở stage sau sẽ bị kẹt vĩnh viễn trong `BLOCKED`. Tra cứu quy chuẩn mở khóa đa tầng tại `references/lifecycle-supervisor-multistage-cooldown-unblock.md`.

---

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
