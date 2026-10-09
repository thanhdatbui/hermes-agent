# Gmail DIE Recovery & Anti-Deletion Guidelines

## 1. INVARIANT TỐI CAO: CẤM TỰ ĐỘNG XÓA PROFILE GPM KHI GMAIL DIE
- **Nguyên nhân**: Khi tài khoản Gmail bị Google vô hiệu hóa hoặc bắt checkpoint, các profile GPM gắn với tài khoản đó thường đã được nạp tiền thuê SIM (qua 5sim/SMS OTP) để verify số điện thoại tạo tài khoản OpenAI / ChatGPT / Codex.
- **Hậu quả nếu xóa**: Xóa profile GPM sẽ làm mất trắng cookie, session, token và toàn bộ tài khoản OpenAI/Codex đã tốn tiền verify.
- **Quy tắc bắt buộc**:
  - Mọi script lifecycle/watchdog (như `sync_gpm_lifecycle.py`) **TUYỆT ĐỐI KHÔNG ĐƯỢC GỬI LỆNH XÓA PROFILE GPM** khi Gmail mang trạng thái `DIE`, `BAN`, hoặc `SUSPENDED`.
  - Chỉ duy trì việc đối soát danh sách profile để tránh tạo trùng cho Gmail `LIVE`.
  - Cột `deleted_count = 0` hardcoded và log ghi nhận an toàn thay vì thực thi delete.

## 2. QUẢN LÝ DỮ LIỆU EXCEL TÁCH BIỆT (MASTER_GMAIL_MANAGER.XLSX)
- File Sổ cái Master: `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx`
- **Sheet `Gmail_DIE_Archive`**:
  - Dành riêng để lưu trữ toàn bộ các tài khoản mang trạng thái `DIE`.
  - Giữ nguyên toàn bộ 16 cột thông tin: `STT`, `Email`, `Password`, `Recovery_Email`, `2FA_Secret`, `SDT`, `Trạng Thái`, `ChatGPT_Reg`, `Số Máy Farm`, `Model Điện Thoại`, `Serial Thiết Bị`, `Proxy Đang Dùng`, `Tên Profile GPM`, `Nguồn`, `Ghi Chú`, `Cập Nhật`.
- **Các sheet vận hành LIVE (`Master_All`, `Gmail_Dat`, `Kibe_Farm_S7`, `Admin_GPM_Pool`)**:
  - Đã dọn sạch 100% tài khoản DIE sang `Gmail_DIE_Archive`.
  - Chỉ chứa tài khoản `LIVE` để tránh việc các script batch gán nhầm tài khoản hỏng.
- **Cột chuẩn hóa `ChatGPT_Reg`**:
  - Được bổ sung ở tất cả các sheet (ngay sau cột `Trạng Thái`).
  - Dùng để đánh dấu rõ ràng tài khoản đã tạo OpenAI/Codex (`YES` / `CHATGPT_READY`).
  - CHATGPT_READY cũng được ghi vào cột `trạng thái` của `gmail_clean_v2.xlsx`.

## 3. PHÂN LOẠI CHECKPOINT & PHƯƠNG PHÁP CỨU GMAIL DIE QUA GPM + PLAYWRIGHT CDP

Khi tài khoản Gmail bị đánh dấu DIE trong quá trình checklive/login, chia làm 3 nhóm:

### Nhóm 1: ACCOUNT_NOT_FOUND (Đã xóa sổ vĩnh viễn)
- Google phản hồi: *"Không tìm thấy tài khoản này"* (`Couldn't find your Google account`).
- **Xử lý**: Không thể cứu Gmail. Tuy nhiên nếu tài khoản đã đăng ký OpenAI/ChatGPT bằng Email + Password riêng (không dùng Google SSO), tài khoản ChatGPT/Codex **vẫn hoạt động bình thường**.

### Nhóm 2: CONFIRM_RECOVERY_PHONE (Chỉ hỏi xác nhận số cũ)
- Màn hình Google: *"Chọn cách bạn muốn đăng nhập"* → tùy chọn *"Xác nhận số điện thoại khôi phục của bạn"*.
- Google **KHÔNG gửi SMS**, chỉ so khớp số điện thoại người dùng nhập với số đã lưu trong hồ sơ bảo mật.
- **CẢNH BÁO — Bẫy dữ liệu Excel**: Số điện thoại lưu trong cột `SDT` của file Excel CÓ THỂ SAI so với số thực tế user từng thêm vào Google Account (ví dụ số sim rác cũ so với số thật của user). Bao giờ cũng nhìn 2 số cuối Google gợi ý trên màn hình (ví dụ `•••• ••• •41`) để đối chiếu trước khi điền. Phải hỏi user xem SĐT đuôi mấy trước rồi mới cập nhật Excel.
- **Cách cứu**: Điền đúng số vào ô xác nhận ➡️ Google cho qua bước tiếp theo.

### Nhóm 3: MANDATORY_PHONE_SMS (Google Phone Checkpoint / IAP)
- Google phản hồi: *"Nhập số điện thoại để nhận tin nhắn văn bản cùng mã xác minh."*
- Bắt buộc nhập một số điện thoại BẤT KỲ để nhận mã SMS OTP chống bot.
- **Cách cứu bằng 5sim**:
  - 5sim có sản phẩm `google` (dùng cho Google, Gmail, YouTube).
  - Giá thuê số Việt Nam: **$0.18** (~4.500 VNĐ), kho sim >200.000 số.
  - Endpoint lấy số: `GET https://5sim.net/v1/user/buy/activation/vietnam/any/google`.
  - Nếu 120s không OTP, 5sim tự hủy và hoàn tiền 100%.

## 4. KỸ THUẬT PLAYWRIGHT CDP CHỐNG TIMEOUT & GIỮ BROWSER MỞ

### Bẫy `wait_until="networkidle"` — LUÔN BỊ TREO
- Trang đăng nhập Google (`accounts.google.com`) liên tục gửi requests telemetry/analytics nền.
- Dùng `networkidle` sẽ khiến Playwright bị kẹt vĩnh viễn và timeout (> 600s).
- **Bắt buộc dùng**: `page.goto(url, wait_until="domcontentloaded", timeout=25000)`.
- Kết hợp `page.set_default_timeout(15000)` cho toàn bộ actions.

### reCAPTCHA Audio Solver — Frame Detach Pattern
- reCAPTCHA audio solver (`solve_recaptcha_audio`) thường fail với `Frame was detached`.
- **Nhưng** sau khi thoát exception, Google vẫn tự chấp nhận (checkbox tự tick) và chuyển sang bước password.
- **Pattern đúng**: Gọi solver, bắt exception, chờ 2s, kiểm tra Next button và click tiếp — KHÔNG abort toàn bộ luồng khi solver fail.

### Giữ Profile Mở Cho User Nhập Mã — KHÔNG ĐÓNG BROWSER
- Khi script navigate đến màn hình nhập mã OTP / chờ SMS:
- **TUYỆT ĐỐI CẤM** gọi `browser.close()` hay API `/profiles/close` / `/profiles/delete`.
- Đặt tên profile rõ ràng để user nhận biết: ví dụ `CUU_ACC_30_dianavmoorepdqu9`.
- Chỉ ngắt kết nối CDP (không đóng browser) — cửa sổ Chrome vẫn hiện trên desktop.
- In rõ: `"BROWSER VẪN MỞ TRÊN MÀN HÌNH! Bạn vào nhập mã bình thường."`.
