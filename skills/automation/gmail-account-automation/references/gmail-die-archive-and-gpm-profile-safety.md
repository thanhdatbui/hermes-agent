# Quy Trình Quản Lý Sổ Cái Gmail DIE & Bảo Toàn Tài Khoản ChatGPT / Codex

## 1. Nguyên Tắc Bảo Vệ Profile GPM (INVARIANT)
- **Bối cảnh**: Nhiều profile GPM gắn với Gmail sau khi đăng ký đã được người dùng nạp tiền thuê SIM (qua 5sim / SMS OTP) để verify và tạo tài khoản **ChatGPT / OpenAI / Codex**.
- **CẤM TUYỆT ĐỐI XÓA PROFILE GPM KHI GMAIL DIE**:
  - Khi Gmail bị Google vô hiệu hóa hoặc dính checkpoint, tài khoản OpenAI/ChatGPT vẫn đăng nhập và hoạt động độc lập bằng email + pass (không phụ thuộc Google SSO).
  - Nếu tự động xóa profile GPM khi Gmail die -> làm mất toàn bộ cookie, session, token và tài khoản OpenAI/Codex đã tốn tiền thuê SIM.
  - Trong các cron sync vòng đời (như `sync_gpm_lifecycle.py`), BẮT BUỘC chỉ đồng bộ tạo profile mới cho Gmail LIVE, cấm gọi API delete profile đối với Gmail DIE.

---

## 2. Cấu Trúc Sổ Cái Quản Lý `master_gmail_manager.xlsx` (5 Sheets)
Đường dẫn: `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx`
- **`Master_All`**: Toàn bộ tài khoản Gmail **LIVE** (188 tài khoản), 0 dòng DIE.
- **`Gmail_Dat`**: Danh sách tài khoản thuộc kho Đạt **LIVE** (45 tài khoản).
- **`Kibe_Farm_S7`**: Danh sách tài khoản gán dàn S7 **LIVE** (168 tài khoản).
- **`Admin_GPM_Pool`**: Danh sách tài khoản cấp cho pool Admin **LIVE** (24 tài khoản).
- **`Gmail_DIE_Archive`**: **Sheet lưu trữ chuyên biệt tài khoản DIE (61 tài khoản)**:
  - Lưu đầy đủ 16 cột: `STT`, `Email`, `Password`, `Recovery_Email`, `2FA_Secret`, `SDT`, `Trạng Thái`, `ChatGPT_Reg`, `Số Máy Farm`, `Model Điện Thoại`, `Serial Thiết Bị`, `Proxy Đang Dùng`, `Tên Profile GPM`, `Nguồn`, `Ghi Chú`, `Cập Nhật`.
  - Cột `ChatGPT_Reg` (cột H) dùng để đánh dấu trạng thái tài khoản đã reg OpenAI/Codex (`YES`, `CHATGPT_READY`).

---

## 3. Chẩn Đoán & Khả Năng Khôi Phục Gmail DIE
Khi kiểm tra tài khoản Gmail DIE qua Chromium Playwright CDP:
1. **ACCOUNT_NOT_FOUND ("Không tìm thấy tài khoản này")**:
   - Google đã xoá sổ tài khoản vĩnh viễn khỏi hệ thống (Purged). Không thể cứu Gmail.
   - Tài khoản ChatGPT/Codex vẫn đăng nhập bình thường tại `chatgpt.com` nếu đã tạo trước đó.
2. **VERIFY_REQUIRED ("Verify it's you" / "Xác minh danh tính")**:
   - Tài khoản vẫn tồn tại 100% và mật khẩu trong file vẫn chính xác.
   - **Xác nhận số cũ (Confirm phone number)**: Google chỉ hỏi đối soát lại số điện thoại đã lưu. Lấy số điện thoại trong cột `SDT` của `Gmail_DIE_Archive` điền vào là Google cho qua ngay không cần nhận SMS.
   - **Bắt buộc nhận OTP SMS số mới**: Dùng API 5sim thuê số dịch vụ `google` tại Việt Nam ($0.18/số) để nhận OTP mở khóa tài khoản và chuyển trạng thái về `LIVE`.

---

## 4. Pitfall Kỹ Thuật Playwright CDP với Google Login
- **CẤM DÙNG `wait_until="networkidle"`**: Trang đăng nhập Google liên tục bắn request analytics/telemetry nền, khiến Playwright CDP bị treo vĩnh viễn (timeout).
- **LUÔN DÙNG `wait_until="domcontentloaded"`** với `timeout=25000` và `page.set_default_timeout(15000)`.
