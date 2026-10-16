# Kỷ Luật Nuôi Gmail GPM Cuốn Chiếu & Quy Tắc Cooldown Re-login

## 1. Quy Tắc Cooldown Proxy: Re-login vs Acc Mới (Hard User Invariant)

### 1.1. Nguyên tắc cốt lõi
- **Chỉ thị dứt khoát của User:** *"Log in acc bị văng thì k tính cooldown 24h. Chỉ acc mới log lên ms bị tính"*.
- **Acc mới (chưa có profile / login lần đầu):** Bắt buộc tuân thủ trần cứng `MAX_LOGINS_PER_PROXY = 2 acc / port / ngày` để chống cháy dải IP 4G và chống bot-check Google.
- **Acc cũ bị văng cookie (Re-login):** Đã có profile GPM gán proxy cố định 1:1 từ trước. Đây thuần túy là thao tác refresh cookie trên đúng dải IP quen thuộc. **BẮT BUỘC MIỄN TRỪ HOÀN TOÀN COOLDOWN 24H**, cho phép watchdog bốc đi login khôi phục session ngay trong ca kế tiếp mà không phải chờ sang ngày hôm sau.

### 1.2. Hiện thực trong code (`post_evening_gpm_login_watchdog.py`)
- Candidate dict mang cờ `is_relogin = is_lost_session`.
- Khi duyệt qua bộ đếm proxy:
  ```python
  is_relogin = c.get("is_relogin", False)
  if not is_relogin:
      if port and current_run_proxy_count.get(port, 0) >= MAX_LOGINS_PER_PROXY:
          log(f"[CANDIDATE-FILTER] {c.get('email')} skipped: proxy port {port} reached daily limit")
          continue
  else:
      log(f"[CANDIDATE-FILTER] {c.get('email')}: RE-LOGIN acc bị văng session -> MIỄN TRỪ proxy limit 2/ngày trên port {port}")

  filtered.append(c)
  seen_mids.add(mid)
  if port and not is_relogin:
      current_run_proxy_count[port] = current_run_proxy_count.get(port, 0) + 1
  ```

---

## 2. Kỷ Luật Nuôi Profile Gmail Group 10 (`cron_gpm_gmail_nurture.py`)

### 2.1. Concurrency Cuốn Chiếu (Rolling Concurrency = 5)
- **Cấu hình chuẩn:** `--concurrency 5 --stagger 30`.
- Chạy 5 worker song song so le 30s (Staggered Launch) chống sốc RAM, CPU và nghẽn socket CDP của GPMLogin Local API (`:19995`).
- Khi 1 profile nuôi xong (2–3 phút xem YouTube hoặc đọc Google News/Search), hệ thống lập tức dọn dẹp Chromium zombie và bốc ngay profile tiếp theo trong hàng đợi.

### 2.2. Chu kỳ giãn cách giữ Session ấm (Warm Session Invariant = 48h)
- **Cấm ngâm quá 5 ngày:** Google tự thu hồi cookie (session timeout) đối với tài khoản ngủ đông. Giãn cách cũ 5 ngày làm tăng tỷ lệ acc bị văng cookie âm thầm.
- **Chu kỳ tối ưu:** `NURTURE_INTERVAL_SECONDS = 2 * 86400` (48 giờ / 2 ngày). Mỗi tài khoản được tương tác ít nhất 1 lần mỗi 2 ngày, vừa giữ cookie luôn tươi (warm), vừa tạo fingerprint tự nhiên như người dùng thật.

### 2.3. Trần an toàn hằng ngày (Daily Quota Cap = 30 acc/ngày)
- **Hằng số bảo vệ:** `MAX_DAILY_NURTURE = 30`.
- **Lý do bắt buộc phải giới hạn trần:**
  1. *Bảo vệ Băng thông Proxy 4G:* Kịch bản nuôi có xem YouTube. Thả nổi nuôi cả ngày sẽ đốt cạn dung lượng gói 4G Mobi (`5101..5138`), làm nghẽn mạng dàn điện thoại S7 đang nuôi/up clip TikTok.
  2. *Bảo vệ Tài nguyên PC:* 5 profile ngốn 3–4GB RAM. Nuôi thành từng đợt ngắn rồi tắt dứt điểm giúp máy chủ mát và ổn định.
- **Cơ chế:** Khi số lượng acc nuôi thành công trong ngày chạm mốc 30 (`count_nurtured_today() >= 30`), script phát telemetry `daily_nurture_limit_reached` và dừng các tick còn lại trong ngày.

---

## 3. Kiến Trúc Báo Cáo: Silent Watchdog Hàng Giờ + Digest 6H

### 3.1. Watchdog nuôi hàng giờ (`gpm-gmail-nurture-watchdog`) $\rightarrow$ Silent Watchdog
- Mặc định bật cờ `--silent` (`action="store_true"`):
  - **100% Profile thành công:** KHÔNG xuất stdout (stdout rỗng). Theo cơ chế Hermes Cron Delivery, stdout rỗng = Silent, không bắn tin nhắn rác lên Telegram.
  - **Phát hiện lỗi hoặc `NEEDS_LOGIN` (văng cookie):** Bắn alert khẩn cấp ra stdout:
    ```text
    [GPM NURTURE ALERT] Phát hiện 1/5 profile lỗi hoặc văng login:
    - user@gmail.com: CHƯA_LOGIN (NEEDS_LOGIN, 45.2s)
    ```
    Alert được tự động gửi ngay về Telegram để người vận hành hoặc ca login kế tiếp xử lý.

### 3.2. Báo cáo gộp định kỳ 6H (`cron_gpm_gmail_nurture_6h_report.py`)
- **Cronjob:** `gpm-gmail-nurture-6h-report` (job_id: `96ea8cc3093b`).
- **Lịch chạy:** `0 */6 * * *` (`00:00, 06:00, 12:00, 18:00`), gửi về kênh GPM (`telegram:-5256944036`).
- **Nội dung chuẩn 1 thông điệp:**
  ```text
  📊 [BÁO CÁO 6H: TIẾN ĐỘ NUÔI GMAIL GPM]
  • Tổng số profile Group 10 (Google Live Ready): 77
  • Đã nuôi trong 6h qua: 10 lượt (5 workers cuốn chiếu)
  • Tài khoản giữ session ấm (<48h): 75/77 profile (97.4%)
  • Tiến độ trần an toàn hôm nay: 20/30 profile
  • Trạng thái session Google: ✓ 100% cookie sống tốt, không có acc văng
  ```
