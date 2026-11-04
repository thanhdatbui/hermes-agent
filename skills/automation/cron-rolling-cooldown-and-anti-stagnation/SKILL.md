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

---

## 2. Chuẩn Thiết Kế Bắt Buộc (Rolling Cooldown Invariant)

### A. Cơ chế Rolling Cooldown / Exclude
Mọi script quét theo lô (batch/watchdog) bắt buộc phải có cơ chế ghi nhớ trạng thái tạm thời để cuốn chiếu:
1. **State-based Exclusion trong ngày (`excluded_today`):**
   - Đọc `STATE_FILE` khi bắt đầu lượt quét.
   - Bất kỳ tài khoản nào đã được thử trong ngày (kể cả `success`, `failed`, hoặc `pending`) phải được đưa vào tập `excluded_today` để query tự động bỏ qua, nhường lượt cho các tài khoản phía sau.
2. **Time-based Cooldown Cache (`failed_candidates_cooldown.json`):**
   - Đối với cron chạy liên tục 24/7 (như Auto-Feed ChatGPT Pool): Khi acc fail, gán cooldown 12h:
     ```python
     if now_ts - fail_ts < 12 * 3600:
         continue  # Bỏ qua để cuốn chiếu hết dàn acc
     ```
   - Khi tài khoản được cứu/nạp thành công, tự động xóa khỏi danh sách cooldown.

### B. Mở rộng Bộ Lọc & Nâng Công Suất
- Không được hardcode duy nhất 1 GroupId hẹp nếu các group khác cũng chứa tài khoản hợp lệ (ví dụ `if gid not in (1, 10): continue` hoặc cung cấp cờ `--all-groups`).
- Nâng batch size tương xứng với thời gian rảnh của GPM/Farm (ví dụ từ 5 lên 10-15 profiles/tick nếu máy rảnh và tài nguyên CPU/RAM đảm bảo).

### C. Kỷ Luật Báo Cáo Sự Cố Telegram (Fail-Closed Observability)
- Tuyệt đối cấm nuốt lỗi khi toàn bộ batch thất bại.
- Nếu có tài khoản thất bại (bị văng Google Auth, dính check device, checkpoint), watchdog bắt buộc phải gom danh sách và gửi tin nhắn cảnh báo về Telegram chuyên trách (kèm đích danh email/máy và lý do kẹt) để Operator can thiệp xử lý tay, không để tài khoản bị lãng quên.
