# Video Playback Options Bottom Sheet Handling & Swipe Duration Tuning (Case 66)

## 1. Hiện tượng lỗi & Anti-Pattern
- **Hiện tượng:** Máy nuôi acc dừng phiên với cảnh báo `unknown TikTok state; swipe recovery (2 swipes) still stuck` và trạng thái `GIỮ HIỆN TRƯỜNG ĐỂ HERMES AGENT XỬ LÝ`.
- **Nguyên nhân gốc rễ:**
  1. Khi lướt video feed, thao tác vuốt với thời gian kéo dài (cũ: 550ms–750ms) vô tình vượt qua ngưỡng long-press mặc định của Android (`ViewConfiguration.getLongPressTimeout() = 400ms..500ms`).
  2. TikTok nhận diện thành cử chỉ nhấn giữ trên video và mở menu bottom sheet cài đặt phát video (*Loại bỏ các yếu tố trên màn hình, Cuộn tự động, Phụ đề và dịch thuật, Chiếu, Ảnh trong ảnh, Âm thanh nền, Lý do bạn thấy* / EN: *Clear display, Auto scroll, Picture-in-picture, Background audio, Why you're seeing this*).
  3. Menu che phủ 50-60% nửa dưới màn hình khiến detector feed không nhận diện được màn hình FYP thông thường.
  4. Luồng `swipe_recovery_on_stuck` cố gắng vuốt 2 lần để giải phóng màn hình, nhưng thao tác swipe chỉ cuộn nội dung bên trong menu bottom sheet chứ không đóng được modal dialog, dẫn tới fail-closed và khóa máy giữ hiện trường.

---

## 2. Giải pháp Chuẩn Hóa (Case 66)

### A. Đăng ký Benign Popup Handler (Priority 83)
- Đăng ký `video_playback_options_overlay` trong `flows/benign_popup_registry.py` và `core/benign_popup.py`.
- **Bounded Modal Container & Multi-marker Matching:** Yêu cầu tối thiểu 2 nhóm danh mục tùy chọn độc lập xuất hiện trong cùng một bounded modal container (`c_bounds[1] >= 250` và không phải root full-screen `[0,0,W,H]`), tránh match nhầm các nhãn phân tán rải rác trên màn hình feed.
- **Pure OCR Disabled:** Tắt hoàn toàn fallback OCR đơn thuần đối với popup này để chống false-positive kích hoạt BACK nhầm lên caption/content video feed.
- **Negative Exclusions nghiêm ngặt:** Loại trừ ngay nếu màn hình thuộc Profile actions (`Sửa hồ sơ`, `Edit profile`, `Thêm tiểu sử`), Login, OTP, Captcha, hoặc từ khóa nằm trong subtree caption/comment/author (`desc`, `caption`, `title`, `author`). Không loại trừ nhãn tab "Following" / "Đang theo dõi" của feed nằm ẩn phía sau bottom sheet.

### B. Cơ chế Đóng & Xác thực An toàn
1. **Pre-action Re-validation:** Xác thực dump hierarchy trước khi gửi lệnh, kiểm tra popup còn tồn tại và đang ở foreground TikTok (fail-closed nếu dump lỗi hoặc focus ngoài TikTok).
2. **Primary Dismiss:** Gửi phím `BACK` (`KEYCODE_BACK` / 4) đơn lẻ với kiểm tra kiểu trả về nghiêm ngặt (`type(res.ok) is bool and res.ok is True` hoặc `type(res.returncode) is int and res.returncode == 0`). Không dùng tap tọa độ mù và không gửi lặp BACK mù.
3. **Verification Polling:** Recapture hierarchy, kiểm tra foreground app vẫn là TikTok, không bị văng sang System UI / Launcher / Dialog quyền (`com.android.systemui`, `com.google.android.gms`, `com.sec.android.app.launcher`...), không chuyển hướng sang màn hình nhạy cảm (Captcha/OTP/Login), và xác nhận modal options sheet đã biến mất hoàn toàn (`detect_video_playback_options_overlay(after_root) is None`).

### C. Tối ưu hóa Swipe Duration Phòng Ngừa Chủ Động
- Hạ dải thời gian vuốt mặc định trong `feed_swipe_smoke.py` và `config.example.yaml`:
  - Cũ: `min_swipe_duration_ms = 550`, `max_swipe_duration_ms = 750` (trung bình 650ms).
  - **Mới: `min_swipe_duration_ms = 300`, `max_swipe_duration_ms = 450` (trung bình 350ms)**.
- Lệnh vuốt feed chuẩn: `input swipe 450 1380 450 480 350`.
- Tốc độ vuốt 350ms nằm hoàn toàn dưới ngưỡng long-press 500ms của Android, loại bỏ tận gốc nguyên nhân kích hoạt menu bottom sheet trong khi vẫn đảm bảo chuyển video mượt mà.
