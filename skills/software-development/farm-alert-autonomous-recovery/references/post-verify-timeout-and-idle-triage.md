# Delayed Post Verification Timeout & Device Idle State Triage

## Bối cảnh & Hiện tượng
- Khi nhận batch alert diện rộng kèm lỗi `UploadHook: Post verification inconclusive/failed: TIMEOUT` trên các máy Farm Admin (M201-M280) hoặc Kibe:
  * Nguồn gốc log: `Tiktok-video/scripts/tiktok_workflow/state_machine.py:14020` (`_verify_post_step()`).
  * Gốc rễ: Sau khi tap Submit video (`POST`), `PostVerifier.verify_post()` chờ tối đa 120s để bắt các marker xác nhận bài đăng (`post_success`, `upload_done`, `video_published`) hoặc kiểm tra tile profile increment. Nếu TikTok xử lý mã hóa/duyệt chậm hoặc mạng trễ quá 120s, verifier trả về `TIMEOUT`.
  * Sau `TIMEOUT`, cơ chế `_recheck_ambiguous_post()` kiểm tra an toàn (profile compare). Nếu không chứng minh được, workflow kết thúc fail-closed để tránh double-posting và đưa thiết bị về Launcher / Idle.

## Quy trình Triage Hiện trường O(1)
1. **Kiểm tra trạng thái thiết bị**:
   - Chạy `python D:/Taadaa/tools/inspect_machine.py <M>`
   - Nếu màn hình `Sleep/Dozing` (OFF) và current focus là `LauncherActivity`: Thiết bị đã kết thúc phiên làm việc trước bình thường, không còn process treo.
2. **Kiểm tra Black Screen Screencap**:
   - Khi thiết bị đang sleep/dozing, lệnh `screencap -p` xuất ra ảnh frame đen (`RGBA (0,0,0,255)`, file size ~12.5 KB).
   - **BẮT BUỘC INVARIANT**: Tuyệt đối KHÔNG gửi đính kèm `MEDIA:<path>` ảnh đen này lên Telegram cho User (vi phạm invariant gửi ảnh mù / gửi đối phó). Chỉ báo cáo bằng chứng text/metrics rõ ràng.
3. **Kiểm tra Proxy Liveness trên máy Admin Remote**:
   - Cụm Admin chạy proxy map qua gateway `192.168.110.2:<port>`.
   - Test connectivity proxy từ host bằng Python `urllib.request` qua `http://192.168.110.2:<port>` đến `http://httpbin.org/ip`.
   - Nếu proxy alive, ping gateway thông suốt, thiết bị pin tốt và đang sạc: Xác nhận sự cố là **TRANSIENT** (do server TikTok chậm), không cần patch code, không can thiệp ADB bấm tay.
4. **Dọn dẹp tệp ảnh tạm**:
   - Dùng `python D:/Taadaa/tools/safe_recycle.py <files...>` để dọn ảnh test/canary pull về, tuân thủ guard bảo vệ dữ liệu.
