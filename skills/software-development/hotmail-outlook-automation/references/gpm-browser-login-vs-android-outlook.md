# GPM Web Login vs Android Outlook Flow & Hotmail Token Role

## Distinction: Android App vs GPM Browser Login
1. **Format Hotmail**: `mail|pass|refresh_token|client_id`.
2. **Trường hợp GPM Browser Login**:
   - Dùng `mail` và `pass` để đăng nhập trực tiếp trên `https://login.live.com`.
   - `refresh_token` và `client_id` **không dùng để inject phiên đăng nhập trình duyệt**. Chúng đóng vai trò phụ trợ (auxiliary): chỉ dùng để gọi Microsoft Graph API đọc mã xác minh (OTP/security code) từ hòm thư khi Microsoft yêu cầu xác minh.
   - **Tuyệt đối không chặn luồng GPM** với lý do "thiếu Microsoft OAuth browser injector".
3. **Trường hợp Android Farm**:
   - Sử dụng Outlook App (com.microsoft.office.outlook) qua ADB UI / Automation Core.
