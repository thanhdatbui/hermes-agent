# Chuẩn Hóa & Đồng Bộ Ngưỡng Device Lock TTL (3600s) và Ngưỡng Cảnh Báo Watchdog (60 Phút / 1 Giờ)

## 1. Bối cảnh & Chuẩn hóa đồng bộ 60 phút
Trước ngày 06/09/2026, watchdog từng sử dụng ngưỡng cảnh báo sớm 40 phút cho lock `running` khiến operator dễ nhầm tưởng thời lượng lock của farm bị giảm từ 1h xuống 40 phút.

Hệ thống đã **đồng bộ toàn diện toàn bộ ngưỡng cảnh báo và thời lượng lock về 60 phút (1 giờ)** để thống nhất với toàn bộ farm:
- Lock thường (running / feed / upload / batch) và lock `blocked` đều có ngưỡng cảnh báo: **60 phút**.
- Máy lock dưới 60 phút tuyệt đối KHÔNG bị gắn cờ cảnh báo `⚠️`.
- Chỉ khi lock $\ge$ 60 phút mới gắn tag: `⚠️ (VƯỢT NGƯỠNG 60P: {duration}p)`.

---

## 2. Bản chất hai cơ chế độc lập

### Cơ chế 1: Thu hồi Lock quá hạn (Reaper - `reap-dead-owner-locks.py`)
- **Vị trí file:** `D:\Taadaa\tiktok-luot nuoi acc\scripts\reap-dead-owner-locks.py` (dòng 37)
- **Thông số:** `LOCK_TTL_SECONDS = 3600` (đúng 60 phút / 1 giờ).
- **Nguyên lý hoạt động:**
  - Chạy theo cron định kỳ (15 phút/lần) hoặc được watchdog gọi preflight.
  - Chỉ thu hồi (di chuyển file lock sang thư mục quarantine `~/.codex/device-locks-reaped/`) khi tuổi lock thực tế **$\ge 3600$ giây (đủ 1 giờ)** hoặc khi tiến trình chủ đã chết (`owner_dead`).
  - **Kết luận:** Khóa thiết bị luôn được bảo lưu đủ 60 phút.

### Cơ chế 2: Giám sát và gửi cảnh báo Telegram (Watchdog - `watch_device_locks.py`)
- **Vị trí file:**
  - Runtime: `C:\Users\Kibe\AppData\Local\hermes\scripts\watch_device_locks.py` (dòng 15-16)
  - Git Repo Template: `D:\Taadaa\Hermes\deploy\hermes-home\scripts\watch_device_locks.py`
  *(BẮT BUỘC đồng bộ cả 2 nơi khi chỉnh sửa)*
- **Thông số đã đồng bộ:**
  ```python
  ALERT_THRESHOLD_MINUTES = 60          # Ngưỡng cảnh báo lock thường running/feed (> 60 phút)
  ALERT_THRESHOLD_BLOCKED_MINUTES = 60  # Đồng bộ toàn bộ ngưỡng lock về 60 phút (1 giờ)
  ```
- **Quy tắc hiển thị cảnh báo:**
  - Khi lock $\ge$ 60 phút: `⚠️ (VƯỢT NGƯỠNG 60P: {duration}p)`
  - Khi lock < 60 phút: Không gắn cờ cảnh báo (hiển thị sạch sẽ thông tin trạng thái máy).
- **Kết luận:** Ngưỡng cảnh báo Watchdog và TTL Reaper giờ đây hoàn toàn đồng bộ ở mốc 60 phút (1 giờ).

---

## 3. Phân biệt Lệch Chu Kỳ Giữa Watchdog Alert và Cron Reaper (Hiện Tượng Báo Quá Hạn Lúc 65-71 Phút)
- **Chu kỳ chạy lệch pha:**
  - Watchdog `watch_device_locks.py` chạy phút: `1, 16, 31, 46` mỗi giờ.
  - Reaper `reap-dead-owner-locks.py` chạy phút: `0, 15, 30, 45` mỗi giờ (`*/15`).
- **Trường hợp máy bị `blocked`:**
  - Trạng thái `blocked` (lỗi cần giữ hiện trường cho operator) có TTL đúng 60 phút. Trong 60 phút đầu, Reaper giữ nguyên không dọn dù tiến trình chủ đã thoát.
  - Khi một máy bị `blocked` tại thời điểm `06:37 - 06:42`:
    - Đến `07:37 - 07:42`: Lock mới tròn 60 phút.
    - Tại thời điểm `07:45`: Nếu preflight timeout hoặc chu kỳ reaper trước đó chưa tới hạn, hoặc watchdog chạy lúc `07:46/07:48`: Tuổi lock đã đạt `66 - 71 phút` -> Watchdog lập tức phát hiện $\ge 60$ phút và bắn cảnh báo Telegram là **HOÀN TOÀN ĐÚNG THIẾT KẾ**.
    - Ngay chu kỳ Reaper kế tiếp lúc `07:49:05`: Reaper quét thấy `blocked_expired age=71m > 60m` và dọn toàn bộ vào quarantine `~/.codex/device-locks-reaped/`, giải phóng thiết bị cho batch tiếp theo.
- **Kết luận giải thích cho User/Operator:**
  - Không phải cron không chạy hay lỗi không nhả lock, mà do **Reaper chạy theo chu kỳ 15 phút** nên máy vượt ngưỡng 60 phút ở khoảng giữa 2 chu kỳ (61 - 74 phút) sẽ bị Watchdog bắt được và cảnh báo trước khi chu kỳ Reaper kế tiếp dọn dẹp.

---

## 5. Kiến Trúc Dọn Lock Và Reset Màn Hình (Auto-Reap & ADB Clean)
- **Tự động đưa máy về HOME khi nhả lock:**
  - Trong `reap-dead-owner-locks.py`, hàm `_cleanup_device_screen(serial)` tự động kích hoạt qua ThreadPoolExecutor (max_workers=16) cho mọi serial được reap:
    ```python
    adb -s <serial> shell am force-stop com.ss.android.ugc.trill
    adb -s <serial> shell am force-stop com.zhiliaoapp.musically
    adb -s <serial> shell input keyevent 3  # KEYEVENT_HOME
    ```
  - Khi dọn lock thành công, app TikTok bị force-stop và máy luôn được đưa về màn hình chính (HOME) để đảm bảo an toàn cho ca chạy tiếp theo.

## 6. Triết Lý Thiết Kế Tránh Báo Động Giả (Anti-Spam Alert vs Auto-Heal) — ĐÃ TRIỂN KHAI (13/09/2026)
- **Vấn đề "Sắp được quét nhả lock mà tự nhiên còn báo":**
  - Trước đây Watchdog và Reaper cùng đặt ngưỡng 60 phút và Reaper chạy chu kỳ 15 phút. Trong khoảng 60 - 75 phút khi Reaper chưa kịp kích hoạt chu kỳ, Watchdog chạy vào phút 46/48 bắt được lock 66-71p và bắn cảnh báo làm phiền Operator trong khi máy chuẩn bị được dọn tự động.
- **Chuẩn hóa kiến trúc đã áp dụng:**
  1. **Tăng tốc độ Reaper (`*/5 * * * *`):** Cron `reap-dead-owner-locks` được chỉnh chạy mỗi 5 phút (thay vì 15 phút). Máy vừa chạm mốc TTL 60p sẽ được dọn và đưa về HOME trong vòng 1-5 phút.
  2. **Watchdog chỉ cảnh báo bất thường thực sự (Fail-safe Alert >= 90 Phút):**
     - Đặt `ALERT_THRESHOLD_MINUTES = 90` và `ALERT_THRESHOLD_BLOCKED_MINUTES = 90` trong `watch_device_locks.py`.
     - Từ 0 - 60 phút: Máy chạy tác vụ hoặc giữ hiện trường cho operator.
     - Từ 60 - 65 phút: Reaper tự động dọn âm thầm vào quarantine, chạy ADB force-stop và đưa máy về HOME sạch sẽ.
     - Chỉ khi lock kẹt **$\ge 90$ phút** (tức Reaper đã chạy hơn 6 chu kỳ mà không thể nhả do tiến trình bất tử hoặc kẹt IO file lock), Watchdog mới kích hoạt bắn cảnh báo Telegram yêu cầu can thiệp thủ công.

---

## 4. Checklist điều tra khi gặp thắc mắc về Lock Duration
1. **Kiểm tra file lock thực tế:** Quét `~/.codex/device-locks/machine_*.lock.json`, xem `mtime` và timestamp tạo lock.
2. **Kiểm tra nhật ký Reaper:** Xem `~/.codex/device-locks-reaped/` để xác nhận lý do thu hồi (reap reason) — lock chỉ bị thu hồi nếu `age >= 60m` hoặc `owner_dead`.
3. **Kiểm tra cron run log gần nhất:** Đọc file output tại `~/AppData/Local/hermes/cron/output/b63730cc5c85/` (Reaper) và `71c2a1b6268c/` (Watchdog) để đối chiếu timestamp chạy và kết quả dọn dẹp.
4. **Đồng bộ song song Runtime & Repo Git:** Khi sửa script watchdog, phải luôn áp dụng đồng bộ `C:\Users\Kibe\AppData\Local\hermes\scripts\watch_device_locks.py` sang `D:\Taadaa\Hermes\deploy\hermes-home\scripts\watch_device_locks.py` và chạy `py_compile` cả 2 file.
