# Quản lý Vòng đời Profile GPM & Bảo toàn Tài khoản OpenAI/Codex (Gmail DIE)

## 1. Bối cảnh & Rủi ro
- Khi tự động hóa quản lý vòng đời tài khoản (`sync_gpm_lifecycle.py`), nếu tự động xóa profile GPM khi Gmail gốc bị Google vô hiệu hóa (`DIE`, `BAN`, `SUSPENDED`), sẽ dẫn đến tổn thất tài sản nghiêm trọng.
- **Rủi ro**: Các profile GPM này thường đã được nạp tiền thuê SIM số (5sim / SMS OTP) để verify kích hoạt tài khoản **OpenAI, ChatGPT, Codex**.
- Mặc dù Gmail bị Google khóa, **tài khoản OpenAI/ChatGPT vẫn đăng nhập và hoạt động bình thường** bằng cặp Email + Mật khẩu (do không dùng Google SSO mà dùng direct credential).
- Nếu xóa profile GPM, toàn bộ session, cookies trình duyệt, token OpenAI và môi trường cấu hình proxy sẽ bị hủy vĩnh viễn.

## 2. Invariant Quy chuẩn Vận hành
1. **CẤM XÓA PROFILE GPM KHI GMAIL DIE**:
   - Tuyệt đối không gọi API `profiles/delete/{profile_id}` trong các cronjob / script dọn dẹp định kỳ đối với các tài khoản Gmail bị DIE.
   - Profile GPM được giữ nguyên trạng để lưu trữ cookie / session / token của OpenAI & Codex.
2. **Quản lý Sổ cái `master_gmail_manager.xlsx`**:
   - Toàn bộ tài khoản Gmail DIE được tách và lưu trữ an toàn trong sheet chuyên biệt: **`Gmail_DIE_Archive`**.
   - Giữ nguyên trọn vẹn 15 cột thông tin gốc: `STT`, `Email`, `Password`, `Recovery_Email`, `2FA_Secret`, `SDT` (số điện thoại thuê ver SIM), `Trạng Thái` (DIE), `Số Máy Farm`, `Model`, `Serial Thiết Bị`, `Proxy Đang Dùng`, `Tên Profile GPM`, `Nguồn`, `Ghi Chú`, `Cập Nhật`.
3. **Logic Tạo Mới Profile GPM**:
   - Script lifecycle chỉ tập trung tạo mới profile cho các Gmail `LIVE` chưa có profile.
   - Chỉ tạo profile khi thiết bị ADB tương ứng của máy farm đang ở trạng thái online.
