# High-Speed CDP Link Claim & Profile Readiness Partitioning

## 1. Bản chất sự cố & Bài học sống còn từ User
- **Cảnh báo từ User:** Không được preflight rà soát live khi shop vừa phát link vì link ưu đãi/activation (Google One, AI Premium...) sẽ bị người khác húp hết chỉ trong 2-4 phút.
- **Giải pháp dứt điểm:** Phải phân vùng Profile GPM thành các nhóm trạng thái cố định từ trước trong CSDL (`profile_data.db`):
  - **Group Ready (ID: 10 - `Google_Live_Ready`):** Chỉ chứa profile đã login Google thành công 100%, cookie active, proxy sống. Khi có link, script chỉ query `GET /api/v3/profiles?group_id=10` mất đúng **0.05s** và bắn song song ngay.
  - **Group Cooldown/Error (ID: 11 - `Google_Cooldown_Error`):** Chứa các profile văng session, dính cờ nhạy cảm `signin/rejected?rrk=77` (ngâm 7 ngày), sai pass, hoặc lỗi proxy. Tuyệt đối không chạm vào khi bắn link.

## 2. Quy tắc chống lag máy & Kill Chrome mồ côi (Resource Discipline)
- **Vấn đề:** Mở hàng loạt profile qua GPM Local API (`/api/v3/profiles/start/{id}`) nếu không kiểm soát chặt sẽ để lại hàng chục/hàng trăm tiến trình `chrome.exe` mồ côi chạy ngầm, ngốn 100% RAM/CPU gây treo máy.
- **Kỷ luật Concurrency:**
  - Không bao giờ chạy quá 3-5 profile cùng lúc trên máy PC (`asyncio.Semaphore(3)` hoặc `Semaphore(5)`).
  - Khối `finally` của từng task **BẮT BUỘC** gọi `GET /api/v3/profiles/stop/{id}`.
  - Sau mỗi batch lớn, kiểm tra và dọn dẹp bằng Python:
    ```python
    import psutil
    for p in psutil.process_iter(['name', 'exe']):
        exe = (p.info.get('exe') or '').lower()
        if 'gpmlogin' in exe and ('chrome.exe' in exe or 'gpmdriver.exe' in exe):
            try: p.kill()
            except Exception: pass
    ```

## 3. Kiến trúc Claim Link Google Service Activation siêu tốc
- Sử dụng Playwright Async kết nối trực tiếp qua CDP:
  1. Gọi GPM API `/api/v3/profiles/start/{id}?win_scale=0.5` lấy `remote_debugging_address`.
  2. Bắt tay WebSocket CDP: `playwright.chromium.connect_over_cdp(f"http://{addr}")`.
  3. `page.goto(url, wait_until="domcontentloaded", timeout=15000)` (không chờ tải ảnh/css nặng).
  4. Inject selector tìm nút nhận:
     `button:has-text("Tham gia"), button:has-text("Accept"), button:has-text("Bắt đầu"), button:has-text("Activate")`
  5. Đóng browser và nhả port ngay lập tức.
- Tốc độ đạt được: ~4.5 giây / profile, 10 link hoàn tất trong ~10 giây khi chạy concurrency 5.
