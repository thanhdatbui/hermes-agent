# Quy tắc Gating Upload Hook Phiên 3 & Xử lý Screencap Artifact Glitch

## 1. Cơ chế kích hoạt Upload Hook ở Phiên 3 (Session 3)
- **Điều kiện kích hoạt:**
  1. `_effective_session_index(child_ctx.config) == 3`: Mọi máy chạy trong Phiên 3 (phiên cuối ca) đều tự động kích hoạt `_run_upload_hook` (chạy `scripts.tiktok_workflow`) khi có sẵn video kế tiếp.
  2. Không chặn upload theo `final_status` (kể cả khi phiên nuôi kết thúc ở `manual-needed` hoặc `degraded` do capture warning).
- **Phân biệt Sensitive Challenge vs Non-critical Stops:**
  - `_SENSITIVE_STOP_WORDS` chỉ bao gồm các sự cố thực sự về bảo mật tài khoản: `manual_challenge`, `captcha`, `otp`, `2fa`, `security_check`, `password_prompt`, `account_locked`, `banned`, `suspended`, `account_blocked`.
  - Tuyệt đối không dùng các từ khóa quá rộng như `"verify"` hay `"verification"` trong `_SENSITIVE_STOP_WORDS` vì sẽ bắt nhầm các bước kiểm tra nội bộ như `profile verification`, `verify_profile` làm skip upload ngoài ý muốn.

## 2. Xử lý lỗi Screencap 12 bytes trên Android (Resilient Degradation)
- **Hiện tượng:**
  - Lệnh `screencap -p` hoặc capture ADB trên một số dòng Samsung trả về file 12 bytes rỗng khi framebuffer bị secure window / surface glitch.
- **Cơ chế xử lý chuẩn:**
  - Cây phân cấp XML (`ui.xml`) vẫn được `capture_required_ui` / ATX lấy đầy đủ.
  - Khi `_profile_capture_artifact_is_complete` kiểm tra thấy `xml_text` hợp lệ và `xml_path` tồn tại nhưng `screen.png` bị lỗi (12 bytes hoặc thiếu), runner không được dừng crash phiên với `capture-artifact-incomplete`.
  - Runner tự động chuyển sang chế độ `degraded` (`capture_artifact_status = "degraded"`), ghi log cảnh báo và tiếp tục đối soát username/display name bình thường dựa trên `xml_text`.

## 3. Cơ chế Deduplication của Farm Alert
- `_feed_session_alert_key` lưu các file `.claimed` tại `alert-claims/<logical_day>-row<N>/machine_<ID>.claimed`.
- Khi một máy đã gửi alert trong cùng ca chạy hôm đó, hệ thống sẽ chặn gửi trùng lặp để tránh spam nhóm Telegram. Khi cần test lại alert, phải xóa file lock/claim tương ứng.

## 4. Đường dẫn cấu hình & Media Source
- **Media Source Root chuẩn:** `D:\TIKTOK-videonuoinick\<folder_video>\<next_video>.mp4`.
- **File Tik Mapping:** `D:\OneDrive\TaadaaData\kibe\Tik<Row>.xlsx` (Sheet `TaiKhoan`: Cột 1 = STT/Máy, Cột 2 = ViChanger ID, Cột 3 = Username/Posted, Cột 4 = Folder Video).

## 5. Idempotency Receipt Scoping trong Upload Runner (`Tiktok-video`)
- **Nguyên lý At-Most-Once:** Runner upload lưu receipt tại `idempotency/post-attempts/` để chống bấm Đăng trùng lặp khi retry/reconnect.
- **Pitfall Đa Nick / Đa Ca:**
  - File receipt BẮT BUỘC phải gắn namespace theo `target_account` (hoặc workbook + row), ví dụ `machine_{machine}_account_{account}_video_{video_number}.json`.
  - Nếu file receipt chỉ đặt theo `machine_{machine}_video_{video_number}.json`, khi máy chạy xoay tua sang nick mới ở ca khác cùng đăng `video 1`, runner sẽ đọc phải receipt cũ của nick trước đó và từ chối bấm nút `Đăng` (`Post tap already recorded for this machine/video`), làm kẹt màn hình soạn thảo và fail `VERIFY_POST`.
  - Khi kiểm tra sự cố upload không bấm nút Đăng, luôn kiểm tra thư mục `D:\CodexRuntime\tiktok-video\idempotency\post-attempts\` để phát hiện receipt cũ tồn đọng.
