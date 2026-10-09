# Quy Tắc Bảo Vệ Profile GPM & Vận Hành Sổ Cái Gmail DIE

## 1. Nguyên Tắc Bất Di Bất Dịch: CẤM XÓA PROFILE GPM KHI GMAIL DIE
- **Bối cảnh**: Nhiều profile GPM gắn với tài khoản Gmail sau khi reg tài khoản đã được nạp tiền thuê SIM (qua 5sim / SMS OTP) để kích hoạt và sử dụng **Codex / ChatGPT / OpenAI**, hoặc chứa các cookie/session quan trọng.
- **Rủi ro**: Nếu tự động xóa profile GPM khi Gmail bị Google vô hiệu hóa (DIE), toàn bộ session, cookie, token và tài khoản OpenAI/Codex đã tốn chi phí thuê SIM sẽ bị xóa sạch vĩnh viễn.
- **Quy tắc thực thi**:
  - Tuyệt đối **CẤM** gọi API `profiles/delete/{pid}` khi đối soát phát hiện Gmail DIE trong các cron sync vòng đời (như `sync_gpm_lifecycle.py`).
  - Đọc danh sách profile GPM chỉ để lấy `existing_gpm_emails` nhằm tránh tạo trùng profile cho các Gmail LIVE mới.
  - Profile của các tài khoản Gmail DIE phải được giữ nguyên vẹn trên GPM để phục vụ tiếp tục khai thác OpenAI / ChatGPT.

---

## 2. Cấu Trúc Sổ Cái Quản Lý `master_gmail_manager.xlsx`
File `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx` là Source of Truth quản lý tài khoản với 5 sheet:
1. **`Master_All`**: Chỉ chứa 100% tài khoản **LIVE** của toàn hệ thống (đã lọc sạch DIE).
2. **`Gmail_Dat`**: Danh sách Gmail thuộc kho Đạt (chỉ chứa các dòng LIVE).
3. **`Kibe_Farm_S7`**: Danh sách Gmail chạy trên dàn S7 của Kibe (chỉ chứa các dòng LIVE).
4. **`Admin_GPM_Pool`**: Danh sách Gmail cấp cho pool Admin (chỉ chứa các dòng LIVE).
5. **`Gmail_DIE_Archive`**: **Sheet lưu trữ chuyên biệt toàn bộ tài khoản DIE**
   - Lưu trữ nguyên vẹn 16 cột thông tin: `STT`, `Email`, `Password`, `Recovery_Email`, `2FA_Secret`, `SDT`, `Trạng Thái`, `ChatGPT_Reg`, `Số Máy Farm`, `Model Điện Thoại`, `Serial Thiết Bị`, `Proxy Đang Dùng`, `Tên Profile GPM`, `Nguồn`, `Ghi Chú`, `Cập Nhật`.
   - Cột **`ChatGPT_Reg`** (cột H) dùng để đánh dấu trạng thái đăng ký OpenAI/ChatGPT (`YES`, `CHATGPT_READY`, v.v.).

---

## 3. Phân Biệt Checkpoint Gmail DIE & Khả Năng Khôi Phục
Khi kiểm tra tài khoản Gmail bị đánh dấu DIE qua Playwright CDP trên GPM:
1. **ACCOUNT_NOT_FOUND ("Không tìm thấy tài khoản này")**:
   - Google đã xóa sổ tài khoản vĩnh viễn (Purged). Không thể khôi phục Gmail.
   - Tài khoản ChatGPT/Codex vẫn có thể đăng nhập độc lập tại `chatgpt.com` nếu đã tạo tài khoản trước đó bằng email/password.
2. **VERIFY_REQUIRED ("Verify it's you" / "Xác minh danh tính")**:
   - Tài khoản vẫn còn tồn tại và mật khẩu vẫn chính xác.
   - **Kịch bản A (Xác nhận số cũ)**: Google chỉ hỏi đối soát lại số điện thoại cũ (Confirm phone number). Nhập lại số điện thoại đã lưu trong cột `SDT` của `Gmail_DIE_Archive` là Google cho qua ngay không cần nhận SMS.
   - **Kịch bản B (Bắt buộc OTP SMS số mới)**: Dùng API 5sim thuê số dịch vụ `google` tại Việt Nam ($0.18) dán vào nhận OTP để mở khóa tài khoản và chuyển trạng thái về `LIVE`.

---

## 4. Pitfall Playwright CDP với Google Login
- **Cấm dùng `wait_until="networkidle"`**: Trang đăng nhập Google liên tục bắn request analytics/telemetry nền, khiến Playwright CDP bị treo vĩnh viễn (timeout).
- **Luôn dùng `wait_until="domcontentloaded"`** với `timeout=25000` ms và `page.set_default_timeout(15000)`.
