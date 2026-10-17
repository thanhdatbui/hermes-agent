# GPM Login Re-login Loop, Proxy Burst Safeguards, and Distinct Telemetry

## 1. Sự Cố Thực Tế: Infinite Re-login Loop & Proxy Burst Spam (17/10/2026)
- **Hiện tượng:** Watchdog `gpm-gmail-login-shifts-watchdog` (`post_evening_gpm_login_watchdog.py`) báo cáo:
  `Kết quả ca: ✓ 44 | ✗ 1 | proxy_limit 2/port/ngày | Hoàn tất ca sáng`
  `Bỏ qua an toàn: 32 acc nhường máy đang bận cron khác (TikTok/Avatar)`
- **Sự thật khi đối soát file state:**
  - Thực tế chỉ có 9 tài khoản được xử lý trong ca. Trong đó 5 tài khoản bị lôi ra login lại 7 đến 9 lần liên tục (`laphuong...` 9 lần, `dinhlan...` 9 lần, `lelinh...` 8 lần, `ninhy...` 7 lần, `minhan...` 7 lần).
  - Proxy port bị băm tới 8–9 lần/sáng (cổng `20004`: 9 lần, `20007`: 9 lần), vi phạm nghiêm trọng hạn mức an toàn `2/port/ngày`.
  - Dòng text *"32 acc nhường máy đang bận cron khác (TikTok/Avatar)"* là văn mẫu ngụy biện/chế số liệu (GPM chạy trên PC Chrome, hoàn toàn không chiếm máy farm).

---

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
1. **Unreconciled State (Trạng thái không được xóa sau xử lý):**
   - Script nuôi GPM (`cron_gpm_gmail_nurture.py`) đánh dấu tài khoản mất session thành `status: NEEDS_LOGIN` trong `gpm_gmail_nurture_state.json`.
   - Watchdog login đọc trạng thái này và gắn cờ `is_relogin = True`.
   - **Bug:** Sau khi login GPM thành công, script **không cập nhật lại trạng thái** trong `gpm_gmail_nurture_state.json` về `LOGIN_OK` hoặc xóa khỏi `NEEDS_LOGIN`.
2. **Bypass Seen-Emails & Proxy-Limit Vô Điều Kiện:**
   - Khi `is_relogin = True`, watchdog cho phép tài khoản bypass qua danh sách `seen_emails` của ngày và miễn trừ chốt chặn `proxy_limit`.
   - Cứ mỗi 5 phút cron thức dậy, 5 tài khoản trên vẫn còn nhãn `NEEDS_LOGIN` nên lại được xếp ưu tiên 1 và tiếp tục bị login lại vô tận.
3. **Thống Kê Không Phân Biệt Distinct:**
   - Bộ đếm `total_success` cộng dồn mỗi lần login thành công thay vì đếm số tài khoản duy nhất (`len(set(processed_emails))`), biến 5 acc lặp thành con số ảo "✓ 44".

---

## 3. Quy Tắc Bắt Buộc Khi Thiết Kế Watchdog Re-login GPM
1. **Chốt Chặn Re-login Cứng (Max 1 Re-login/Acc/Ngày):**
   - Kể cả tài khoản được đánh dấu `is_relogin` (do mất session), mỗi tài khoản **CHỈ ĐƯỢC PHÉP login tối đa đúng 1 lần trong 24 giờ**.
   - Phải ghi nhận `last_login_date` và chặn ngay nếu đã login trong ngày, tuyệt đối không cho phép bypass `seen_emails` nhiều lần.
2. **Reconcile State Hai Chiều (Bi-directional State Reconcile):**
   - Ngay sau khi login GPM thành công cho tài khoản `NEEDS_LOGIN`, **bắt buộc ghi đè trạng thái** trong `gpm_gmail_nurture_state.json` thành `status: LOGIN_OK`, `repaired_at: <ISO timestamp>`.
3. **Bảo Vệ Ngưỡng Proxy 4G Tối Thượng:**
   - Proxy limit (2 acc/port/ngày) là hạn mức an toàn bảo vệ IP không bị Google checkpoint.
   - Tài khoản re-login **vẫn tiêu tốn request trên proxy**. Nếu port đã đạt 2 lượt/ngày thì tài khoản re-login phải đợi sang ngày hôm sau hoặc đổi port khác, cấm miễn trừ vô tội vạ.
4. **Trung Thực Trong Báo Cáo Telemetry (No Fabricated Text):**
   - Chỉ số báo cáo phải là số tài khoản duy nhất: `✓ {len(set(success_emails))} acc (distinct)`.
   - In rõ số lượt thực tế trên proxy: `proxy_usage: max {max_port_hits}/port`.
   - Tuyệt đối cấm ghép các lý do ngụy biện ("nhường máy TikTok", "chờ farm rảnh") vào báo cáo khi nghiệp vụ chạy độc lập trên PC.
