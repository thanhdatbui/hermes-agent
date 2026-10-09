# GPM Hotmail Security Change-Info Pipeline (Playwright CDP)

## 1. Mục đích & Bối cảnh
- Tận dụng GPMLogin trên PC để đổi mật khẩu và Sign out everywhere cho Hotmail/Outlook của farm thay vì dùng điện thoại Samsung S7.
- Không tranh chấp DeviceLock với các ca nuôi feed TikTok.
- Không lo Samsung S7 bị OOM, crash Chrome hoặc timeout ADB khi tải trang bảo mật Microsoft.

## 2. Ánh xạ Profile & Proxy Đồng nhất
- Map profile GPM theo số máy farm: `f"{machine:02d} - "` hoặc `f"M{machine:02d} - "`.
- Profile GPM đã được cấu hình proxy 4G tương ứng của máy đó (Mobi hoặc Singbox port `20000+N`).
- Điều này đảm bảo Hotmail được đăng nhập và đổi mật khẩu trên cùng IP/Geo của thiết bị.

## 3. Các bẫy UI Microsoft và Giải pháp Playwright CDP
1. **Entry Point**: Điều hướng trực tiếp tới `https://account.live.com/password/change`.
2. **Switch to Password**:
   - Nếu Microsoft đề xuất gửi mã xác minh thay vì ô nhập mật khẩu:
   - Click `#idA_PWD_SwitchToPassword` hoặc `a:has-text('Sử dụng mật khẩu của bạn')`.
3. **Terms Update & KMSI**:
   - Màn hình *"Chúng tôi đang cập nhật các điều khoản"*: click nút `#iNext` / `button:has-text('Tiếp theo')`.
   - Màn hình *"Duy trì đăng nhập?"*: click `#idBtn_Back` ("Không").
4. **Locators cho Form đổi mật khẩu**:
   - Ô mật khẩu hiện tại (nếu có): `#currentPassword`.
   - Ô mật khẩu mới & Nhập lại:
     `page.locator('#iPassword, #newPassword, input[name="Password"]').first`
     `page.locator('#iRetypePassword, #confirmPassword, input[name="RetypePassword"]').first`
5. **Readback Guard (Tối quan trọng)**:
   - Sau khi bấm "Lưu", nếu Microsoft báo:
     *"Tạm thời có lỗi với dịch vụ. Xin vui lòng thử lại..."* (do rate limit hoặc cooldown tài khoản).
   - **BẮT BUỘC KHÔNG ĐƯỢC GHI ĐÈ MẬT KHẨU MỚI VÀO EXCEL (CỘT G)**. Giữ nguyên mật khẩu cũ để không làm mất thông tin đăng nhập.
