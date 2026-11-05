# Kỷ Luật Canh Máy Rảnh Cuốn Chiếu Toàn Farm (Opportunistic Idle-Machine Architecture)

## 1. Bản Chất Kiến Trúc
Thay vì cố định lịch chạy theo các khung giờ cứng (dễ gây thắt cổ chai, nghẽn mạng 4G và bỏ phí các khoảng nghỉ 2-4 tiếng giữa các ca nuôi của điện thoại Farm):
- Chuyển toàn bộ các cronjob tác vụ phụ (Cứu session, Bật 2FA, Reg nick, Đổi tên, Up avatar) sang cơ chế **Canh Máy Rảnh Cuốn Chiếu (Opportunistic Idle-Machine)** quét liên tục (`*/15 * * * *` hoặc `*/5 * * * *`).
- Chặn cứng 3 ca cao điểm nuôi feed của Farm:
  * Ca 1: `05:15 – 09:30`
  * Ca 2: `11:45 – 15:30`
  * Ca 3: `17:45 – 21:30`
  * Dọn cache: `04:00 – 04:30`
- Ngoài các khung giờ này, cronjob được phép chạy bất kỳ lúc nào khi thỏa mãn 2 điều kiện:
  1. `is_machine_idle(mid) == True`: Máy không dính active lock và không nằm trong đệm 15 phút trước ca nuôi tiếp theo.
  2. Máy thật online ADB.

---

## 2. Bảng Phân Tầng Độ Ưu Tiên (Priority Hierarchy) Khi Tranh Chấp Máy Rảnh
Đăng video TikTok đã được tích hợp trực tiếp vào Ca Nuôi chính (Cadence chính), không tham gia tranh chấp ngoài giờ rảnh. Các tác vụ phụ được xếp tầng nghiêm ngặt:

| Priority | Tác vụ | Cronjob phụ trách | Cơ chế nhường quyền / Vận hành |
|:---:|:---|:---|:---|
| **P0 (Khẩn cấp)** | **Cứu Gmail văng login (`NEEDS_LOGIN`)** | `post_evening_gpm_login_watchdog.py` | Ưu tiên số 1 toàn farm. Miễn trừ giới hạn proxy 2 acc/ngày, bốc máy ngay khi S7 rảnh để cứu session. |
| **P1 (Bảo mật)** | **Bật 2FA Gmail & 2FA TikTok** | `post_morning_gmail_2fa_watchdog.py`<br>`cron_night_tiktok_2fa_watchdog.py` | Bật bảo vệ tài khoản mới trước khi đưa vào khai thác. Chạy cả ngày khi máy rảnh. |
| **P2 (Chuẩn hóa)** | **Chuỗi sau ca trưa (Reg Gmail) & Avatar/Đổi tên** | `post_noon_chain_watchdog.py`<br>`post_evening_avatar_watchdog.py`<br>`tiktok_rename_rolling_watchdog.py` | Chạy cuốn chiếu khi máy rảnh. |
| **P3 (Dọn dẹp)** | **Reset app, dọn lock chết, dọn cache** | `farm_idle_screen_and_app_healer.py`<br>`reap-dead-owner-locks.py` | Đưa máy về Home an toàn. |

---

## 3. Chống Retry Đè (Anti-Loop & Idempotency Invariants)
- **Quy tắc User Chấn Chỉnh:** *"1 cron chạy xong trong ngày r thì đến cron khác nhé chứ k phải lỗi là cứ đè ra retry đâu"*.
- **Idempotency Gate:**
  * Bắt buộc có kiểm tra `already_ran_today(today_str)`. Khi một cron batch/chain đã hoàn tất mục tiêu trong ngày hôm nay $\rightarrow$ Bắt buộc **Exit 0 im lặng**, tuyệt đối không chạy lại lần 2.
- **Circuit Breaker Cooldown:**
  * Khi gặp lỗi hoặc vừa kết thúc một lượt chạy (kể cả partial/fail), bắt buộc kích hoạt `is_in_cooldown(threshold_minutes=45..60)`.
  * Không được đè máy ra retry liên tục mỗi tick làm nghẽn thiết bị và chặn đường các cron P0/P1 khác.
