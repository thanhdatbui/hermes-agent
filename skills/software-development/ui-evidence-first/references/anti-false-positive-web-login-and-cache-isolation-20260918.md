# Quy Chuẩn Chống Báo Cáo Ảo Web Login & Quản Lý Cache/Session Android Farm (User Correction 2026-09-18)

## 1. Context & Sự Cố "Báo Cáo Láo" ChatGPT Guest Mode
- **Hiện tượng:** Khi điều hướng hoặc submit web auth, trang web nhảy về domain đích (`chatgpt.com`). Agent vội vã kết luận "Đã đăng nhập thành công 100%" chỉ dựa trên URL hoặc text "ChatGPT" trên màn hình.
- **Bị User bắt bài & Phản ứng:** Màn hình thực tế ở góc phải vẫn hiện nút màu đen **"Đăng nhập"** (chưa hề có avatar, profile name hay session token). Trang web chỉ đang ở chế độ **Khách vãng lai (Guest Mode)**.
- **Root Cause Kỹ Thuật:**
  1. *Form input che khuất do bàn phím ảo (IME)*: Ô tuổi bị bỏ trống khiến form không submit được, hoặc submit dính `invalid_state`.
  2. *Chưa verify Session Marker thực tế*: Chỉ nhìn URL/Title thay vì kiểm tra UI Artifact độc quyền của trạng thái đã đăng nhập.

## 2. Tiêu Chuẩn Nghiệm Thu Đăng Nhập Web Độc Quyền (Web Auth Success Gate)
Để công nhận một phiên đăng nhập web (ChatGPT, TikTok web, mạng xã hội...) là THÀNH CÔNG:
1. **NÚT ĐĂNG NHẬP BIẾN MẤT (Login Button Count == 0):**
   - Quét text/OCR màn hình: Tuyệt đối CẤM còn xuất hiện các nút mang nhãn: `Đăng nhập`, `Log in`, `Sign in`, `Chuyển sang tài khoản khác`.
2. **XUẤT HIỆN ARTIFACT PROFILE CÁ NHÂN (Positive Session Evidence):**
   - Bắt buộc phải dump XML / OCR thấy rõ ít nhất một trong các marker sau:
     - Avatar người dùng / Tên hồ sơ cá nhân (ví dụ: `Nguyen Ngan Ha`).
     - Gói tài khoản (ví dụ: `Free`, `Plus`, `Team`).
     - Nút mở menu hồ sơ (ví dụ: `radix-_r_1o_ 'Nguyen Ngan Ha Free, mở menu hồ sơ'`).
   - Mở sidebar / menu account để chụp cận cảnh thông tin tài khoản làm bằng chứng nghiệm thu GATE 6.

## 3. Bản Chất Cache Rác Chrome (`pm clear com.android.chrome`) vs Session Hotmail / Google
Khi gặp lỗi cache redirect cũ hoặc kẹt Google Credential Manager trên Chrome S7:
- **Tài khoản Hotmail trên Farm:**
  - Hoạt động bên trong **App Outlook (`com.microsoft.office.outlook`)**.
  - `pm clear com.android.chrome` **KHÔNG** làm mất session Hotmail trong Outlook.
- **Tài khoản Google trên Android:**
  - Được quản lý bởi hệ điều hành Android qua **`AccountManagerService` (`dumpsys account`)**.
  - Xóa data Chrome không làm văng tài khoản Google khỏi thiết bị S7.
- **Lưu ý:** Chỉ cookie web của các trang từng mở trên Web Chrome mới bị xóa; các app native độc lập hoàn toàn an toàn.
