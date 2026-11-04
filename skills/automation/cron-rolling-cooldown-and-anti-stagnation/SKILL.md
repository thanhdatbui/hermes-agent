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

### C. Phân Luồng Xác Thực Theo Domain (Anti-Provider-SSO Mismatch)
- Khi gộp nhiều loại domain (Gmail, Hotmail/Outlook) vào cùng một pool cuốn chiếu:
  - **CẤM TUYỆT ĐỐI** dùng chung luồng đăng nhập (ví dụ: ép `Continue with Google` / Google SSO lên các tài khoản Hotmail).
  - Profile Hotmail không có session Google trong GPM; nếu văng session mà tự động click Google SSO sẽ dẫn đến chuyển hướng sang `accounts.google.com`, tìm không thấy email, kẹt timeout và gây chết chùm 100% batch.
  - Phân luồng chặt: Google SSO chỉ chạy với `@gmail.com`. Với Hotmail, nếu mất session-token thì fail-fast hoặc chuyển sang luồng Direct Mail+Pass/Graph OTP, không để tài khoản bị phạt cooldown oan.

### D. Kỷ Luật Báo Cáo Sự Cố Telegram (Fail-Closed Observability vs Chống Spam Storm)
- Xem case study chi tiết: `references/anti-spam-storm-and-high-frequency-cron-reporting.md` và `references/silent-cron-vs-periodic-watchdog-separation.md`.
- **Tách biệt tuyệt đối giữa Silent Cron và Periodic Watchdog:**
  - **Với cron xử lý tần suất cao (<= 30 phút/lần, ví dụ */5, */15):** BẮT BUỘC vận hành theo chuẩn **Silent Cron**. Xử lý liên tục, lưu state vào JSON/DB, và **CẤM TUYỆT ĐỐI** gọi hàm gửi Telegram (`send_telegram_report`, `requests.post`) ở cuối hàm `main()` hoặc sau mỗi batch 5–10 acc. Điều này ngăn ngừa triệt để tình trạng bão spam làm rác kênh chat của User.
  - **Với watchdog báo cáo định kỳ (chu kỳ 6h / 12h / 24h):** Gom toàn bộ số liệu xử lý của cả chu kỳ vào 1 báo cáo tổng hợp duy nhất gửi về kênh Telegram chuyên trách theo đúng lịch hẹn.
  - **Ngưỡng cảnh báo tức thời duy nhất cho cron ngắn:** CHỈ được phép gửi alert tức thời khi phát hiện sự cố hạ tầng tê liệt diện rộng (100% proxy cụm die, GPM API sập hoàn toàn, DB corrupt).
- **Khóa chết kênh đích, cấm Bleed sang Farm Alerts (`-5373649734`):**
  - CẤM TUYỆT ĐỐI để script nghiệp vụ nhánh (GPM, ChatGPT pool, Orders) fallback về kênh mặc định `REPO_GROUP_ROUTING['default']` (kênh Farm Alerts máy vật lý).
  - Bắt buộc hardcode hoặc cấu hình đích danh `chat_id` chuyên trách (ví dụ GPM Auto: `-5256944036`). Nếu chưa xác định được kênh đích chuyên trách, mặc định BẮT BUỘC ghi log local, TUYỆT ĐỐI KHÔNG gửi về Farm Alerts.

### E. Bảo Toàn Metadata Nguồn (Anti-Proxy-Port Desync Trap)
- Xem case study chi tiết: `references/case-study-gpm-auto-feed-chatgpt-rescue-and-port-desync.md`.
- Khi worker chạy bóc token/session từ profile GPM, dict kết quả trả về bắt buộc phải lưu giữ toàn bộ metadata (`port`, `host`, `pid`). Tránh lỗi worker bóc token thành công nhưng hàm sync database lại skip toàn bộ do thiếu thông tin proxy port trong kết quả trả về.

### F. Vệ Sinh Chuỗi Báo Lỗi & URL Trích Xuất (Anti-OAuth-URL-Dumping Trap)
- Xem case study & quy chuẩn: `references/sanitized-error-reporting-and-url-filtering.md`.
- **CẤM TUYỆT ĐỐI** ném nguyên văn `page.url` chứa query parameters khổng lồ của Google/Microsoft OAuth (`part=...`, `rart=...`, `clientid=...`) vào chuỗi báo lỗi gửi Telegram.
- Bắt buộc bóc tách query params bằng `clean_url = page.url.split('?')[0][:80]` để thông báo ngắn gọn, đúng bản chất màn hình kẹt, không gây rác và ức chế cho người dùng.
- Khi sửa đổi logic thông báo lỗi qua `unified_patch_pipeline.py`, bắt buộc truyền kèm file test tương ứng (`--file scripts/... --file tests/...`) để vượt qua `MANDATORY_TEST_DELTA_GUARD`.
