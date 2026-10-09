# Upload Subprocess Nonzero Root Cause, Error Extraction & Alert Escaping (2026-09-05)

## 1. Bối cảnh & Hiện tượng gây ức chế
- **Triệu chứng mập mờ:** Khi quy trình đăng video TikTok (`Tiktok-video` / `run_post.py`) bị lỗi hoặc chuyển trạng thái dừng (ví dụ: `MANUAL_REVIEW`, `CONNECT_DEVICE_ERROR`, timeout, kẹt popup), Telegram Farm Alert nhận được thông báo chung chung:
  `Triệu chứng: upload_subprocess_nonzero`
- **Hậu quả:** Người vận hành không thể biết máy bị lỗi cụ thể gì (lệch account, kẹt nút tạo video, hay timeout mạng) nếu không mở trực tiếp từng máy hoặc đọc thủ công từng file log run.

## 2. Nguyên nhân cốt lõi (Root Cause)
1. **Hardcode Fallback trong Hook Subprocess:**
   - Trong `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/multi_machine_feed_session.py` (`_run_upload_hook`), khi tiến trình con upload video thoát với mã khác 0 (`proc.returncode != 0`), code cũ gán cứng:
     ```python
     "reason": reason_override or ("" if is_success else ("post_verification_failed" if proc.returncode == 0 else "upload_subprocess_nonzero"))
     ```
   - Mặc dù `run_post.py` ghi nhận đầy đủ chi tiết vào `report.json` (`error`, `reason`, `last_state`, `status`) và log `stderr`/`stdout`, toàn bộ thông tin giá trị này đều bị xóa sổ và thay thế bằng chuỗi thô `upload_subprocess_nonzero`.
2. **Lỗi cú pháp Telegram HTML Entity (`can't parse entities`):**
   - Trong `automation_core/alerts.py`, các biến động như `error_reason`, `account`, `serial`, `status_text` được chèn thẳng vào template HTML mà không bọc `html.escape()`. Khi lỗi có chứa các thẻ hoặc filter như `<redacted>`, `<module>`, Telegram Bot API sẽ từ chối gửi tin nhắn.
3. **Sự cố Máy 59 & Case 83 (Camera surface false-positive trên Profile):**
   - Khi Camera mở ở chế độ LIVE, script chuyển tab Đăng/Tạo thì gặp màn hình Mẫu CapCut (`Beat 1 máy bay` / Template Hub).
   - Thao tác dismiss template đưa UI về Profile root.
   - Tại Profile root, do header Profile có icon camera shortcut (`content-desc="Camera"`) và tab video có chữ `"Đăng"`, hàm `_is_camera_surface_xml` bị nhận nhầm Profile root là Camera surface.
   - Script tính toán alternative thumbnail tại góc dưới trái `(156, 1574)` và tap trúng video tile đầu tiên trên lưới Profile -> mở trình phát video cá nhân (`sl0` / `view_entrance_text` / `bq7`). Luồng recovery không tìm thấy nút tạo (+), dẫn đến dừng phiên với `[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED]`.

## 3. Quy chuẩn khắc phục (Standard Fix)
1. **Hàm bóc tách lỗi đa tầng `_extract_upload_subprocess_error`:**
   - **Tầng 1 (Report JSON):** Đọc `report.json` của worker run. Lấy `err = rep_data.get("error") or rep_data.get("reason")`, kết hợp `[last_state]` để ra chuỗi rõ ràng (ví dụ: `[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Recaptured surface did not prove a labelled bottom-centre create control`).
   - **Tầng 2 (Stderr):** Lấy dòng lỗi cuối cùng (trừ dòng trống) nếu report không có.
   - **Tầng 3 (Stdout):** Quét tìm dòng `[ERROR]` hoặc dòng `>>> State: <state>`.
   - **Tầng 4 (Fallback):** `upload_exit_code_{returncode}`.
   - Giới hạn tối đa 250 ký tự an toàn.
2. **HTML Escape cho Alert:**
   - Luôn gọi `html.escape(str(val))` cho tất cả các trường động trước khi đưa vào template HTML gửi Telegram.
3. **Phân biệt Profile Root vs Camera Surface (Case 83):**
   - `_is_camera_surface_xml` bắt buộc loại trừ Profile root markers (`sửa hồ sơ`, `edit profile`, `chia sẻ hồ sơ`, `ny0`), loại trừ Bottom Navigation Bar (khi có cả 2 tab `Trang chủ` và `Hồ sơ`), và loại trừ Feed root (`long_press_layout`).
   - Bổ sung `_is_profile_video_playback_surface` và `_recover_profile_video_playback_surface` tự động tìm bấm `bq7` quay lại an toàn.
4. **Idempotency Ledger Clearing:**
   - Trước khi retry chạy lại video cho máy bị ngắt quãng, bắt buộc kiểm tra và xóa file reservation kẹt tại `D:\CodexRuntime\tiktok-video\idempotency\media-fingerprints\<hash>.json` để tránh bị dừng ở gate `MEDIA_FINGERPRINT_PENDING`.
