# Chiến lược Thuê số 5sim & Định tuyến Cronjob Farm (Codex Hotmail + GPM)

## 1. Cơ chế Thuê số 5sim & Lazy Cache Refresh
1. **Lazy Refresh Cache (TTL = 1 giờ):**
   - File cache: `D:\Taadaa\runtime\kibe\cron-state\5sim_best_pools.json`.
   - Khi script chạy, nếu cache đã cũ hơn 1 giờ (`CACHE_TTL_SECONDS = 3600`), script tự fetch bảng giá live của OpenAI từ 5sim.
   - Tiêu chuẩn lọc tự động: Giá $\le 0.12\$$, kho sẵn $>20$ số, tỉ lệ nhận code 24h $>0\%$.
   - Sắp xếp ưu tiên: Việt Nam $\rightarrow$ rate 24h cao nhất $\rightarrow$ giá rẻ nhất.
   - Khi nhiều worker chạy song song: Worker đầu tiên ghi cache, các worker sau đọc ngay lập tức (0.001s), chống nghẽn và chống rate limit HTTP 429.
2. **Quy tắc Thử 3 Lần / Nước (100% Hoàn tiền khi hủy):**
   - Cấu hình `country_tries = 3`: Mỗi quốc gia trong pool thử tối đa 3 số liên tiếp.
   - Nếu số không về OTP sau 45-90s hoặc bị OpenAI từ chối: Lập tức gọi API Cancel để 5sim hoàn tiền $100\%$ về ví, sau đó lấy số tiếp theo của cùng nước đó.
   - Thử đủ 3 lần của nước đó thất bại mới chuyển sang nước tiếp theo.
3. **Chiến thuật Tạm tắt trên OmniRoute để Ngâm 48h:**
   - Sau khi hoàn tất OAuth callback trên port 1455, script lập tức chạy SQL:
     ```sql
     UPDATE provider_connections SET is_active = 0 WHERE id = ?
     ```
   - Mục đích: Tránh để tài khoản mới tạo bị router đẩy request dồn dập kích hoạt kiểm tra bot.
   - Cronjob quét định kỳ mỗi giờ (`no_agent=True`) sẽ tự động bật lại `is_active = 1` sau đúng 48 tiếng ngâm an toàn.

---

## 2. Quy tắc Bất biến: Định tuyến Cronjob Báo cáo Farm & Watchdog (Anti-DM Leak)
- **Triệu chứng:** User đang làm việc riêng với Coordinator thì nhận bản tin watchdog/tiến độ farm (render, download, report 6h...) đổ vào chat riêng Telegram. Phản ứng: *"gì thế, tự nhiên ném report vào đây?"*.
- **Nguyên nhân:** Khi tạo cronjob trong phiên chat cá nhân (DM/private topic), scheduler mặc định `deliver='origin'`.
- **Kỷ luật định tuyến:**
  1. Mọi cronjob định kỳ của Farm (Watchdog, Báo cáo tiến độ 6h, Đồng bộ hóa, Healthcheck) **BẮT BUỘC** phải đặt:
     - `deliver='telegram:-5373649734'` (Kênh Farm Alerts chính thức).
     - Hoặc `deliver='local'` nếu chỉ ghi output ra log đĩa.
  2. **CẤM TUYỆT ĐỐI** dùng `deliver='origin'` hoặc `deliver='origin,telegram:...'` cho cronjob tự động định kỳ.

---

## 3. Script-Only Cronjobs Bắt buộc `no_agent=True`
- **Triệu chứng:** Cronjob báo lỗi:
  `⚠️ Cron failed: Skipped to prevent unintended spend: global inference config drifted...`
- **Quy tắc:**
  - Cronjob chạy script Python/Bash thuần túy (quét DB, đồng bộ file, dọn dẹp, kiểm tra cổng) **BẮT BUỘC** đặt:
    - `no_agent=True`
    - `script='<path_to_script.py>'`
  - Đảm bảo 0 tốn token LLM, thực thi tức thì, và không bao giờ bị dừng do cơ chế drift guard của Hermes.
