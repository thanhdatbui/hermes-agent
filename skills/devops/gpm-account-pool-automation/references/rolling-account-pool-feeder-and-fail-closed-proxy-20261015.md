# Rolling Account Pool Feeder with Fail-Closed Proxy & Zombie Cleanup (15/10/2026)

## 1. Bối cảnh & Vấn đề
Khi xây dựng và mở rộng account pool cho ChatGPT Web (`chatgpt-web-pool`), các kịch bản cũ thường gặp phải các lỗi:
1. **Lọc sót danh sách tài khoản:** Hardcode regex `@gmail\.com` khiến hệ thống bỏ sót toàn bộ kho tài khoản Hotmail (hơn 460 profile) vốn đã đăng nhập sẵn ChatGPT web trong GPM.
2. **Zombie Chrome Leak:** Khi mở GPM qua API `/profiles/start/{pid}`, nếu chỉ gọi `/profiles/stop/{pid}` mà không dọn sạch tiến trình con hoặc khi script gặp lỗi bất ngờ, hàng chục tiến trình `chrome.exe` sẽ bị bỏ rơi, chiếm dụng toàn bộ RAM/CPU của máy.
3. **Chạy thủ công bằng tay:** Không có cron tự động nạp cuốn chiếu, dẫn đến việc thiếu hụt pool khi các tài khoản cũ bị rate-limit hoặc hết quota.

---

## 2. Kiến trúc Giải pháp Chuẩn (Script `cron_auto_feed_chatgpt_pool.py`)

### A. Cơ chế 5 Worker Song Song Cuốn Chiếu
- Dùng `ThreadPoolExecutor(max_workers=5)` để xử lý đồng thời 5 profile mỗi đợt.
- Quét động candidate chưa có trong pool từ SQLite GPM (`profile_data.db`):
  ```python
  c_omni = sqlite3.connect(OMNI_DB_PATH)
  active_emails = set(r[0].lower().strip() for r in c_omni.execute("SELECT email FROM provider_connections WHERE provider='chatgpt-web' AND is_active=1").fetchall() if r[0])
  c_omni.close()
  ```
- Ưu tiên nhặt Hotmail trước (vì tỷ lệ có sẵn session token live cao hơn), sau đó đến Gmail.

### B. Chốt an toàn Fail-Closed Proxy 1-1
- BẮT BUỘC tra cứu và gán đúng proxy trong `proxy_registry` và `proxy_assignments` TRƯỚC KHI bật `is_active = 1`:
  - Dải Mobi (ports `5101`..`5138`): host `test.taadaa.click`, user `mobi<port-5100>`, pass `TaadaaMobi#2026!`.
  - Dải MikroTik (ports `10001`..`10007`): host `mirotik1.taadaa.click`.
- Nếu không tìm thấy proxy tương ứng trong registry: BẮT BUỘC bỏ qua (SKIP), tuyệt đối không kích hoạt connection để tránh lỗi `[Proxy Fast-Fail]` hoặc lộ IP thật.

### C. Cam kết Đóng Sạch Profile 100% (Zombie Cleanup Invariant)
Khối `finally` của từng worker BẮT BUỘC phải thực thi 2 tầng dọn dẹp:
1. Gọi GPM API: `requests.get(f"{GPM_API_BASE}/profiles/stop/{pid}", timeout=10)`.
2. Kill trực tiếp qua `psutil` hoặc `taskkill` đối với mọi process Chrome có command line chứa đường dẫn `profile_path`:
   ```python
   for proc in psutil.process_iter(['name', 'cmdline']):
       if proc.info['name'] == 'chrome.exe' and profile_path in " ".join(proc.info['cmdline'] or []):
           proc.kill()
   ```

### D. Khóa chống chạy đè (File Lock)
Dùng `D:/Taadaa/GPM auto/logs/cron_auto_feed_chatgpt_pool.lock` ghi PID và timestamp. Nếu tick trước đang chạy (< 5 phút), tick sau tự động bỏ qua để tránh nghẽn GPM API.

---

## 3. Lên lịch Cronjob Tự Động
- Đăng ký cronjob Hermes với chu kỳ `*/15 * * * *` (mỗi 15 phút):
  ```bash
  cronjob create --name "cron-auto-feed-chatgpt-pool" --schedule "*/15 * * * *" --deliver local --workdir "D:\Taadaa\GPM auto\scripts" --prompt "Chạy python \"D:/Taadaa/GPM auto/scripts/cron_auto_feed_chatgpt_pool.py\""
  ```
- Cờ `deliver='local'` đảm bảo ghi log ngầm vào hệ thống, không spam tin nhắn batch lên Telegram của Operator.
