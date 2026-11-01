---
name: tiktok-account-security-automation
description: "Use when automating TikTok email change, 2FA, or security."
---
# TikTok Account Security & Credential Automation

Quy chuẩn và cơ chế an toàn khi tự động hóa thay đổi email, mật khẩu, và bảo mật trên app TikTok điện thoại thật Android (S7/S8) qua ATX/ADB.

## 1. Anti-Deletion Invariant (Cấm Click Tọa Độ Cứng Trên Menu Cài Đặt)
- **Sự cố & Bẫy nguy hiểm:**
  - Trên app TikTok Android, trong menu *Cài đặt và quyền riêng tư* -> *Tài khoản*: dòng cuối cùng sát đáy màn hình (`y >= 1750`) chính là mục **`Hủy kích hoạt hoặc xóa tài khoản`** (`Deactivate or delete account`).
  - Nếu click theo tọa độ pixel cứng (ví dụ `[540, 1810]`), app có thể mở thẳng vào trang nguy hiểm: *"Xóa hoặc hủy kích hoạt? (Hủy kích hoạt tài khoản / Xóa tài khoản vĩnh viễn)"*.
- **Kỷ luật bắt buộc:**
  1. **XML-First Text Anchoring:** TUYỆT ĐỐI CẤM dùng tọa độ pixel cứng. Bắt buộc parse `dumpWindowHierarchy` XML, định vị đúng node theo text:
     - `text="Thông tin tài khoản"` (hoặc `desc="Thông tin tài khoản"`)
     - `text="Email"`
     - `text="Thay đổi email"`
     Click chính xác vào tâm bounds: `((bounds[0] + bounds[2]) // 2, (bounds[1] + bounds[3]) // 2)`.
  2. **Fail-Closed Tránh Xóa Tài Khoản:** Nếu dump XML phát hiện bất kỳ node nào chứa cụm từ nhạy cảm (`"Xóa hoặc hủy kích hoạt"`, `"Xóa tài khoản vĩnh viễn"`, `"Hủy kích hoạt tài khoản"`):
     - DỪNG NGAY LẬP TỨC mọi thao tác click tiếp theo!
     - Bấm ngay nút `Back` hoặc `Home` (`input keyevent 4` hoặc `3`) để đưa app về trạng thái an toàn.
     - Đánh dấu task `FAILED_SAFETY` và chụp ảnh báo cáo.

## 2. Quy Tắc Captcha Puzzle Khi Đổi Email / Đăng Ký (Popup Dismiss Trap)
- **Bẫy hủy request:**
  - Khi điền email mới và bấm *"Tiếp tục"*, TikTok có thể bật popup WebView **"Xác minh để tiếp tục:" (Puzzle Slider)**.
  - **CẤM BẤM NÚT ĐÓNG `X` (`verify-bar-close`):** Bấm nút `X` để tắt popup đồng nghĩa với việc User hủy thao tác trên backend TikTok -> TikTok sẽ **KHÔNG BAO GIỜ gửi mã OTP về hòm thư**!
  - Nếu bot bấm đóng popup rồi tiếp tục vòng lặp chờ OTP (polling 30s-60s), bot sẽ luôn bị lỗi giả *"Failed to receive OTP within timeout"*.
- **Xử lý chuẩn:**
  - Khi phát hiện Captcha Puzzle: Giữ nguyên hiện trường, giải captcha (nếu có solver kéo trượt) hoặc báo `CAPTCHA_CHALLENGE` và chụp ảnh bằng chứng gửi User. Tuyệt đối không bấm nút `X` đóng popup rồi chờ OTP mù.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
