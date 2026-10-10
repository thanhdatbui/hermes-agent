# Opportunistic Upload & Rest-Day Decoupling Invariants (2026-10-11)

## 1. Vấn đề kiến trúc: Single Point of Failure khi chỉ mở upload ở Phiên 2

Trước đây, hệ thống từng cấu hình chỉ mở upload ở Phiên 2 (sau khi lướt feed ở Phiên 1). Tuy nhiên, khi chuyển sang lịch chạy mỏng (chu kỳ xoay tua 4 ngày: Ngày 1 lẻ, Ngày 2 chẵn, Ngày 3 R7/8+yếu, Ngày 4 dưỡng sinh, Ngày 5 random), mỗi tài khoản chỉ có rất ít cơ hội xuất hiện trong ngày:
- Nếu chỉ cho phép upload ở Phiên 2: khi Phiên 2 gặp lỗi thoáng qua (mạng 4G lag, proxy timeout, app crash, kẹt modal/popup), nick đó sẽ **mất trắng lượt đăng video trong ngày**.
- Điều này làm giãn nhịp đăng từ 2 ngày thành 4-6 ngày/video, gây trễ chỉ tiêu nuôi nick (cần $\ge 10$ video để mở khóa đi follow).

## 2. Giải pháp: Opportunistic Upload (Phiên 1 hoặc Phiên 2)

Chuyển sang cơ chế **Phiên 1 là Primary attempt, Phiên 2 là Fallback attempt**:
- **Tại `tiktok_runner.py`:** Luôn luôn truyền cờ `"-AllowUploadHook"` cho tất cả các ca và phiên:
  ```python
  # tiktok_runner.py (_spawn_feed_session)
  argv = [
      ...
      "-Row", str(row),
      "-SessionIndex", str(session_index),
      "-AllowUploadHook",
      ...
  ]
  ```
- **Tại `run-feed-session.ps1`:** Đảm bảo chuyển tiếp cờ `--allow-upload-hook` vào Python runner khi có cờ hoặc khi `SessionIndex -in 1, 2`:
  ```powershell
  if ($AllowUploadHook -or $SessionIndex -in 1, 2) {
      $arguments += "--allow-upload-hook"
      $arguments += "--session-index", "$SessionIndex"
  } else {
      $arguments += "--session-index", "$SessionIndex"
  }
  ```
- **Tại core `multi_machine_feed_session.py` (Idempotency Ledger):**
  - Quản lý qua sổ cái cấp ngày `shift_upload_history.json` kèm `_InterProcessFileLock`.
  - Phiên 1 chạy: nếu chưa upload -> thực hiện upload. Thành công -> ghi `status: success`.
  - Phiên 2 chạy: kiểm tra sổ cái thấy đã có entry `success` -> lập tức trả về `status: skipped, reason: already_uploaded_in_shift`, tuyệt đối không double-post.
  - Nếu Phiên 1 bị lỗi hoặc timeout -> sổ cái chưa có `success` -> Phiên 2 tự động đăng bù.

## 3. Tách bạch hoàn toàn Follow Cooldown / Ngày dưỡng sinh với Upload

Đây là lỗi tư duy nghiêm trọng từng xảy ra trong hệ thống: gom chung *"Dưỡng sinh = 0 Follow + 0 Upload"*:

### A. Hai bộ não thuật toán TikTok độc lập:
1. **Anti-Fraud System (Chống gian lận tương tác):** Quét tốc độ follow, tỷ lệ follow/unfollow, IP proxy, sự bất thường giữa follow và watch time. Kích hoạt cờ nhả follow hoặc checkpoint khi thấy cày follow bất thường.
2. **Recommendation Engine (Phân phối nội dung):** Đánh giá video dựa trên *retention rate, watch time, completion rate, share, comment*. Thuật toán này không quan tâm hôm nay nick có đi follow ai hay không.

### B. Quy tắc vận hành Farm:
1. **Khi nick bị nhả follow (Follow Cooldown):**
   - Chỉ tạm dừng hành vi follow (`_follow_rate = {"for_you": 0, "following": 0, "friends": 0}`).
   - **VẪN ĐƯỢC ĐĂNG 1 VIDEO/NGÀY BÌNH THƯỜNG**. Nick bị nhả follow vẫn là Creator hoạt động nội dung, gửi tín hiệu tài khoản sống thực tế cho TikTok.
2. **Khi rơi vào ngày dưỡng sinh / ca xả tải (`is_rest_day`):**
   - Bản chất là ngày xả tải follow toàn farm hoặc ca tối dưỡng sinh (Row 3 / Row 4) để rửa trust sau càn quét.
   - Thiết lập biến môi trường `TAADAA_REST_DAY_NO_FOLLOW = "1"` để tắt follow.
   - **TUYỆT ĐỐI CẤM** dùng điều kiện `if not is_rest_day` để chặn `"-AllowUploadHook"`. Kể cả trong ca xả tải, nick vẫn cần đăng 1 video/ngày nếu chưa đăng trong ngày.
