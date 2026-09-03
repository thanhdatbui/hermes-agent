# Timeout Isolation & Lifecycle Rules for Multi-Machine Feed, Follow, and Upload Hooks (2026-08-26)

## 1. Context & Root Cause
Trong các hệ thống đa tiến trình (multi-machine feed session), nếu timeout tổng (`min_safe_hard_timeout` / outer watchdog timeout) chỉ tính riêng cho Feed session mà không cộng độc lập thời gian chạy của các sub-hook (`Follow Hook`, `Upload Hook`), các tiến trình chạy sau sẽ bị outer watchdog ngắt ngang (`hard outer watchdog timeout exceeded`), dẫn tới:
- Bị kill tiến trình khi đang follow hoặc đang render/upload video.
- Đánh dấu fail oan (`failed` / `timeout`) dù thiết bị vẫn đang thực thi bình thường.
- Nguy cơ sinh orphan process và lock thiết bị sai trạng thái.

## 2. Quy tắc phân bổ Timeout độc lập (Mandatory Multi-Tier Timeout Isolation)
Mỗi thành phần trong chu kỳ nuôi acc có một budget thời gian độc lập và bắt buộc phải được tính cộng dồn ở lớp outer watchdog:

1. **Feed Session Timeout (`DEFAULT_DEVICE_TIMEOUT_SECONDS = 2100s` - ~35 phút):**
   - Dành riêng cho việc khởi động app, xử lý popup, kiểm tra định danh tài khoản và thực hiện toàn bộ chu trình lướt 8–11 video (Fast Swipe + Deep Inspect).

2. **Follow Hook Timeout (`DEFAULT_FOLLOW_HOOK_TIMEOUT_SECONDS = 900s` - 15 phút):**
   - Subprocess độc lập chạy cross-repo (`D:\Taadaa\tiktok-follow\follow_runner\run_follow.py`).
   - Có timeout riêng 900s, không được dùng chung hay trừ vào budget của feed session.

3. **Upload Hook Timeout (`DEFAULT_UPLOAD_HOOK_TIMEOUT_SECONDS = 1200s` - 20 phút):**
   - Subprocess độc lập chạy cross-repo (`D:\CodexRuntime\tiktok-video\scripts\tiktok_workflow.py`).
   - Chạy ở phiên cuối cùng của ca (phiên 3) hoặc khi có cờ ép buộc (`force_upload_hook`).
   - Có timeout riêng 1200s cho quá trình chuẩn bị video, copy vào device và upload lên TikTok.

4. **Outer Watchdog Safe Hard Timeout Formula:**
   $$\text{worker\_hard\_timeout} = \max(\text{configured\_hard}, \text{feed\_timeout} + \text{follow\_timeout} + \text{upload\_extra\_budget} + 300\text{s buffer})$$
   - Phiên 1 & 2 (Feed + Follow): tối thiểu $2100 + 900 + 300 = 3300\text{s}$ (~55 phút).
   - Phiên 3 (Feed + Follow + Upload): tối thiểu $2100 + 900 + 1200 + 300 = 4500\text{s}$ (~75 phút).

## 3. Quy trình thực thi chuẩn trong mỗi ca
- **Mỗi phiên thường (Phiên 1, Phiên 2):** Nuôi feed $\rightarrow$ Chạy Follow hook (nếu nick $\ge 1$ video).
- **Phiên cuối cùng trong ca (Phiên 3):** Nuôi feed $\rightarrow$ Chạy Follow hook $\rightarrow$ Chạy Upload video hook.
- **Fail-closed Follow:** Nếu phát hiện bị nhả follow dù chỉ 1 lần trong ngày (`follow_failed = True`), lập tức khóa follow của riêng nick đó cả ngày hôm đó (`follow_state_<machine>_row_<row>.json`), chuyển nick sang chế độ chỉ nuôi feed để bảo vệ tài khoản.
