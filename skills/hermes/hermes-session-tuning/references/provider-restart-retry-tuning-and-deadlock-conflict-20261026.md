# Tinh Chỉnh Cửa Sổ Retry Hermes Khi Provider Restart & Tránh Mâu Thuẫn Watchdog / Anti-Flapping (26/10/2026)

## 1. Hiện Tượng & Trải Nghiệm Gây Bực Bội (User Frustration)
- Khi OmniRoute (:20129) bị deadlock do proxy rớt hàng loạt kết hợp stream nặng và watchdog kích hoạt force-restart, cổng 20129 tạm đóng trong khoảng **25–35 giây** (thời gian Node.js biên dịch Next.js, nạp SQLite, hydrate settings).
- Hermes Gateway gửi request sang gặp `Connection Refused`. Với cấu hình mặc định (`api_max_retries: 3`, `api_retry_delay: 3.0s`):
  - Chuỗi retry trải dài: ~3s → ~6s → ~12s (tổng thời gian kiên nhẫn chỉ có **~15–18 giây**).
  - Cổng 20129 chưa kịp mở lại thì Hermes đã đốt hết 3 lượt retry, lập tức ngắt turn và gửi thông báo lỗi ra Telegram:
    `⚠️ The model provider failed after retries. I kept raw provider details out of chat; check gateway logs for diagnostics.`
  - Hậu quả: Người dùng đang chat dở ở nhiều topics (5–10 sessions) đồng loạt bị văng lỗi và buộc phải gõ lại tin nhắn vào từng topic rất phiền phức.

---

## 2. Phân Tích 3 Mâu Thuẫn Với Setting Đã Fix Trước Đây (Conflict Analysis)

Khi nảy sinh ý định "tăng retry" hoặc "ép watchdog restart nhanh hơn", bắt buộc đối soát với 3 bản vá lịch sử để tránh tái phát sự cố nghiêm trọng:

### A. Mâu thuẫn khi tăng thuần số lần retry (`api_max_retries: 6–8`) (Incident 02/10/2026)
- **Setting từng fix:** Ngày 02/10, hệ thống dính sự cố **Thundering Herd Retry Storm** khi OmniRoute chạm ngưỡng V8 Heap Pressure 7.1GB (HTTP 503). Khi đó 10 session cùng lúc retry dồn dập 5–6 lần tạo ra bão 50–60 requests/phút, khiến Node.js không kịp dọn rác (GC) và sập hoàn toàn. Hệ thống đã phải hạ trần `api_max_retries` từ 5 xuống **`3`**.
- **Nguy cơ tái phát:** Nếu tăng thuần số lần retry lên 6–8 lần mà giữ delay ngắn, khi OmniRoute chập chờn 503, bão retry sẽ tái diễn và đánh sập tiến trình.

### B. Mâu thuẫn khi hạ trần Deadlock `$MaxDeadlockFailures` của Watchdog (từ 12 xuống 4) (Incident 05/10/2026)
- **Setting từng fix:** Trong `omniroute_watchdog.ps1`, tham số `$MaxDeadlockFailures = 12` đi kèm cơ chế:
  1. `OMNIROUTE_CHAT_ADMISSION_QUEUE_MS = 120000` (cho phép request xếp hàng tới 120s khi có prompt nặng 400k tokens).
  2. Cơ chế **Anti-Flapping**: `$MaxRestartsInWindow = 3` trong 15 phút (`900s`).
  3. Mỗi chu kỳ kiểm tra: Timeout 15s + Sleep 15s = ~30s. 12 lần = ~360s (6 phút).
- **Nguy cơ tái phát:** Nếu hạ xuống 4 lần (~90s–120s), khi có các subagent gửi prompt nặng 300k–400k tokens, OmniRoute bận tính toán sẽ làm `/api/health` chậm 2–3 nhịp. Watchdog sẽ **bắn nhầm (False-Kill)** tiến trình đang xử lý hợp lệ. Khi bị bắn nhầm 3 lần liên tiếp trong 15 phút, Anti-Flapping khóa chặt restart $\rightarrow$ OmniRoute chết cứng 15 phút!

### C. Mâu thuẫn khi ép Fallback sang 9Router (Port 20128) (Incident 01/10 & 22/10/2026)
- **Setting từng fix:** 
  1. 9Router trên port 20128 đòi hỏi auth riêng và thường xuyên cạn pool Antigravity (`401 No active credentials`).
  2. Fallback sang proxy ngoài dễ gây lỗi **mất context / trắng context** do lệch schema tool-calling, khiến bot mất trí nhớ lịch sử hội thoại.

---

## 3. Cấu Hình Cân Bằng Chuẩn Xác (Sweet Spot Balance)

Giải pháp tối ưu không gây bão tải và không xung đột với các bản vá trước:
**Giữ số lần retry ở mức vừa phải (`api_max_retries: 4`) và giãn cách ban đầu bằng `api_retry_delay: 6.0s`**.

### Lệnh thiết lập chuẩn:
```bash
python D:/Taadaa/tools/manage_hermes_config.py set agent.api_max_retries 4 --type int
python D:/Taadaa/tools/manage_hermes_config.py set agent.api_retry_delay 6.0 --type float
```

### Cơ chế nhịp chờ:
- Nhịp 1: Chờ ~6s (kèm jitter ~6–7s).
- Nhịp 2: Chờ ~12s (kèm jitter ~12–14s).
- Nhịp 3: Chờ ~24s (kèm jitter ~24–28s).
- Nhịp 4: Chờ ~48s (kèm jitter ~48–55s).
- **Tổng thời gian kiên nhẫn chờ:** **~90–100 giây**.

### Hiệu quả thực tế:
1. **Bao trọn thời gian restart:** OmniRoute watchdog cần ~25–35s để đưa tiến trình UP trở lại. Ở nhịp retry thứ 3 hoặc 4, cổng 20129 vừa mở là Hermes kết nối thành công ngay $\rightarrow$ Tự động sinh câu trả lời, không ngắt turn, user không phải chat lại.
2. **Khống chế trần tải:** Mỗi session chỉ phát sinh tối đa 4 requests, trải dài trong 90s thay vì dồn dập trong 15s $\rightarrow$ Hoàn toàn an toàn trước bão tải 503 và không làm sập Node.js.
