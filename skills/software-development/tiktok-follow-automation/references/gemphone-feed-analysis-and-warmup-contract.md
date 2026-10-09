# Tài liệu thực nghiệm: Khảo sát GemPhoneFarm (Anh Khoa) & Triển khai Post-Cooldown Warmup + Ad Fast-Skip (2026-09-12)

## 1. Bản chất kỹ thuật: Ngâm nick qua đêm (Session Settling Myth) vs Cold Start
- **Thực nghiệm & Phân tích hệ thống:**
  - Ngâm app TikTok idle offline qua đêm không tạo ra Trust Score backend: `No telemetry/traffic = No server-side scoring`.
  - Stale Token & Attestation: Device attestation (Play Integrity) có TTL rất ngắn và challenge-bound, mở app buổi sáng vẫn phải re-attest.
  - Rủi ro lệch Network Context: Switch nick từ đêm trên IP cũ, qua đêm IP proxy/mạng xoay -> sáng dùng trên IP mới -> kích hoạt cờ nghi vấn tài khoản bị hijack.
  - **Quy trình chuẩn duy nhất:** Đến giờ ca nào -> Mở app -> Check proxy/mạng -> Switch nick -> Lướt feed 16-22 video (~28-35 phút) có Like 15% -> mới kích hoạt Follow/Upload.

## 2. Phân tích Flow GemPhoneFarm `TIKTOK-Nuôi-Tài-Khoản-Gốc` (205 nodes, 481 edges)
- **Cấu trúc lõi của anh Khoa:**
  1. Phân bổ tab tự nhiên: 60% Đề xuất (For You), 20% Đang follow (Following), 20% Bạn bè (Friends).
  2. Số lượng video: 14 - 25 video / phiên (trung bình ~20 video).
  3. Cơ chế Like (15% rate): Dừng xem video 4.4s - 16.4s trước khi like (mô phỏng thấy hay mới like). Sau khi like nghỉ 1.5s - 3.8s mới lướt tiếp.
  4. **Ad Fast-Skip:** Quét XPath `//node[@text="Được tài trợ"]` -> nếu gặp video quảng cáo thì bỏ qua ngay trong 0.5s - 1s, không like, không xem lâu.
  5. Đóng CAPTCHA nhẹ: Bắt `//node[@resource-id="verify-bar-close"]` click X đóng thanh trượt thay vì kẹt treo máy.

## 3. Các cải tiến đã triển khai trên farm 80 máy (2026-09-12)
1. **Repo `tiktok-luot nuoi acc`:**
   - **Fix 0 Like:** Prefix match `desc.lower().startswith("thích video")` + `attrib.get("clickable") == "true"`.
   - **Tăng thể tích Feed:** `FEED_SESSION_MIN_TOTAL_VIDEOS = 16`, `FEED_SESSION_MAX_TOTAL_VIDEOS = 22`, `FEED_SESSION_MAX_SWIPES = 28`.
   - **Cập nhật Cap validation:** `SESSION_MAX_SWIPES_CAP = 30` (tránh lỗi `config-error: feed-session-smoke requires 1 <= --max-swipes <= 15`).
   - **Tăng Timeout:** `DEFAULT_DEVICE_TIMEOUT_SECONDS = 3000.0` (50 phút cho 16-22 video).
   - **Ad Fast-Skip:** Hàm `_is_sponsored_xml` dùng `iter_elements` quét đệ quy case-insensitive `text` và `content-desc` tìm `"Được tài trợ"` / `"Sponsored"`.
   - **Watchdog Report:** Bổ sung `• Lướt Feed (N lượt thả tim)` vào tin nhắn Telegram của `feed_session_watchdog.py`.
2. **Repo `tiktok-follow`:**
   - **Post-Cooldown Warmup (`follow_state.py`):**
     ```python
     @property
     def is_post_cooldown_warmup(self) -> bool:
         return self.fail_streak > 0 and not self.follow_failed
     ```
     Khi tài khoản vừa mãn hạn cooldown, `session_budget()` chỉ cấp **3 - 5 follow / phiên** với `video_count >= 5`. Follow thành công sẽ reset `fail_streak = 0`.
