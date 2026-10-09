# Kỹ Thuật Behavioral Entropy & Anti-Clustering Toàn Diện (TikTok Phone Farm)

Tài liệu chuẩn hóa kiến trúc mô phỏng hành vi người thật và phân tán nhịp chạy chống gom cụm (Clustering Detection) của ByteDance Security SDK (`libmetasec_ml.so`).

---

## 1. Tầng Cử Chỉ Cảm Ứng (Touch Layer)

### A. Độ nghiêng ngón tay tự nhiên (Human Natural Thumb Drift)
- **Vấn đề cốt lõi:** Vuốt dọc thẳng tắp $dx = 0$ (`start_x == end_x`) là chữ ký bot thô thiển 100% của lệnh `adb shell input swipe`.
- **Thiết kế chuẩn:**
  - `start_x`: ngẫu nhiên trong khoảng `[465, 525]` (tâm màn hình 1080p).
  - `end_x`: lệch tự nhiên $\Delta X = [-18, +12]\text{px}$ theo góc vung ngón cái người thuận tay phải (`start_x + random.randint(-18, 12)`).
  - **Hành lang an toàn:** Toàn bộ điểm vuốt phải nằm trọn trong khoảng an toàn $X \in [450, 540]$. Cách xa vùng nhạy cảm kích hoạt Camera Story bên trái ($0 \dots 150\text{px}$) và Profile bên phải ($930 \dots 1080\text{px}$) hơn 300px.
  - **Skew Fallback (Phòng thủ đa tầng):** Nếu có bất kỳ tham số vuốt ngoài nào bị lệch quá mức ($|\Delta X| > 30\text{px}$), hệ thống tự động cưỡng chế ép thẳng đứng `end_x = start_x` để triệt tiêu hoàn toàn nguy cơ văng màn hình.

### B. Cuộn Lưới Video Profile & Restore (Upload Engine)
- Áp dụng trong `adapter.py` cho cả thao tác cuộn lưới và restore màn hình: `drift_x = start_x + random.randint(-15, 12)`, duration ngẫu nhiên `420ms - 490ms`.

---

## 2. Tầng Hỗn Loạn Hành Vi (Behavioral Entropy & De-correlation)

### A. Nhịp Vuốt Ngược Xem Lại Video (Rewind Swipe - Tạo Session Narrative)
- **Bản chất người thật:** Người thật không bao giờ lướt 20 video 1 chiều tăm tắp. Họ thỉnh thoảng quẹt ngược lại để xem lại đoạn mở đầu hoặc đọc caption của video vừa lướt qua.
- **Quy tắc triển khai:**
  - Kích hoạt trong feed session từ video thứ 3 trở đi (`swipe_count >= 3`), không phải video cuối ca (`not is_last_video`).
  - Tỷ lệ ngẫu nhiên: `random.randint(5, 8)%` (trung bình 1-2 phiên mới có 1 lần vuốt ngược).
  - Tọa độ vuốt ngược: `[sx, 480] -> [ex, 1380]`, duration `350 - 450ms`.
  - Ngâm dừng xem lại: `time.sleep(random.uniform(2.0, 4.0))`.
  - **Chốt chặn an toàn (`allow_downward`):** Mọi lệnh vuốt thông thường mặc định vẫn cưỡng chế vuốt lên (`start_y > end_y`). Cử chỉ vuốt ngược bắt buộc phải mang cờ tường minh `allow_downward=True`.

### B. Bấm Lưu Bookmark Độc Lập (Independent Bookmark)
- **Phá vỡ tương quan cứng ($Like \rightarrow Save$):** Người dùng thật thường bấm Lưu các video hay, video kiến thức mà không cần bấm Like.
- **Quy tắc triển khai:**
  - Tỷ lệ `random.randint(3, 5)%` kích hoạt khi video **không được like** (hoặc đã like từ trước, hoặc nút like không tìm thấy).
  - Điều kiện an toàn: Tọa độ nút Bookmark phải thuộc thanh công cụ bên phải (`center[0] >= 750`).
  - Delay ngâm tự nhiên: `1.0s - 2.2s` trước khi tap.
  - **Fail-Closed Verification:** Kiểm tra kết quả ADB (`res is not None and res.ok is True`), nếu thất bại trả về `False` ngay, không báo cáo thành công ảo.

### C. Xem Lướt Bình Luận (Comment Peek)
- Độc quyền trên video Deep Inspect (tỷ lệ `12%`):
  1. Tìm nút bình luận bên phải (`center[0] >= 750`).
  2. Bấm mở sheet, ngâm đọc `2.0s - 4.0s`.
  3. Có 50% xác suất cuộn nhẹ 1 nhịp ngắn (`300ms`) đọc tiếp `1.0s - 2.0s`.
  4. Bấm Back (`input keyevent 4`) đóng sheet, nghỉ `0.6s - 1.2s`.
  5. Closed-loop verification: Kiểm tra focused package, nếu mất focus TikTok hoặc lỗi thì ghi log `failed_dismissal` và trả về `False`.

### D. Phân Tầng Tỷ Lệ Like Theo Tab
- Following: `random.randint(30, 60)%` mỗi phiên.
- Friends: `random.randint(50, 80)%` mỗi phiên.
- For You: Giữ mức `8%` tự nhiên (tại nhịp Deep Inspect bù trừ bằng `20%`).

---

## 3. Tầng Lịch Trình Cron & Chống Gom Cụm (Anti-Clustering & Micro-Jitter)

### A. Invariant Khóa Cứng Giờ Cron Hệ Thống (CẤM SỬA GIỜ CRON)
- **Nguyên nhân cấm:**
  1. `tiktok_picker.py` có Silent Window từ `02:00` đến `05:59` sáng. Sửa giờ cron sớm (ví dụ 05:50) sẽ bị nuốt ca, không cấp quyền chạy.
  2. `feed_session_watchdog.py` quét theo half-open interval `SESSION_WINDOWS` (`06:00 - 08:00`, `08:00 - 12:00`...). Sửa giờ cron chạy sớm sẽ khiến kết quả bị gán nhầm vào Ca 4 Đêm, dẫn đến Watchdog Ca 1 bắn Farm Alert đỏ vì không tìm thấy folder.
  3. Các watchdog mắt xích cuốn chiếu (`post-morning-gmail-2fa-watchdog` lúc 08:00, `post-noon-chain-watchdog` lúc 14:00) dựa vào mốc giờ chuẩn.

### B. Giải Pháp Micro-Jitter Nội Bộ (Safe In-Process Jitter)
- Giữ nguyên giờ bắn Cron (`06:00`, `08:00`, `12:00`...).
- Trong `run-feed-session.ps1`, ngay trước khi gọi Python điều khiển thiết bị, chèn đoạn ngâm dừng ngẫu nhiên từ 1 đến 3 phút:
  ```powershell
  $isRecoveryMode = ($effectiveSwipes -gt 0) -or ($RecoveryTestSwipes -gt 0) -or $PSBoundParameters.ContainsKey("RecoveryTestSwipes")
  if ($Run -and -not $DisableSessionJitter -and -not $isRecoveryMode -and $SessionJitterMaxSeconds -gt 0) {
      $sessionJitterSec = Get-Random -Minimum $SessionJitterMinSeconds -Maximum ($SessionJitterMaxSeconds + 1)
      Write-Host "Applying natural session start jitter: sleeping $sessionJitterSec s before launching devices..."
      Start-Sleep -Seconds $sessionJitterSec
  }
  ```
- **Tại sao an toàn tuyệt đối:**
  1. Tiến trình PowerShell đã active ngay từ đầu tick cron $\rightarrow$ `feed_session_watchdog.py` kiểm tra `is_feed_runner_active() == True` nên kiên nhẫn chờ, không bao giờ báo lỗi.
  2. 160 điện thoại Galaxy S7 chỉ thực sự kết nối vào TikTok lúc `06:01`, `06:02`, `06:03`... hoàn toàn lệch trôi tự nhiên.
  3. Kết hợp với `MachineStartStaggerMs = 2000, 8000` (so le 2s đến 8s giữa các máy) $\rightarrow$ Triệt tiêu 100% chữ ký phát hiện chu kỳ cơ học (Periodic Anomaly) của ByteDance.
  4. Tự động bypass jitter khi chạy chế độ phục hồi kiểm thử (`-RecoveryTestSwipes`) hoặc khi truyền `-DisableSessionJitter`.
