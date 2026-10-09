# Gmail Registration Operations, Web Live Check & 2FA Persistence Playbook

Tài liệu đúc kết từ sự cố mẻ chạy đêm 2026-09-12 và đợt kiểm chứng Canary trên Máy 39/03.

---

## I. GMAIL LIVE VERIFICATION: CHECKMAIL.LIVE VS ON-DEVICE FALSE POSITIVES

### 1. Cạm bẫy của On-Device Health Check (`check_google_account_health_from_gmail`)
- **Cơ chế ngộ nhận:** Khi tài khoản Google bị khóa ngầm (disabled/deactivated) ở máy chủ Google, ứng dụng Gmail trên Android vẫn giữ token cũ và không lập tức hiện thông báo lỗi hay CAPTCHA.
- **Hậu quả:** Hàm kiểm tra trên máy nhận định sai rằng tài khoản vẫn `LIVE`, kết luận sai rằng lỗi do TikTok không phát OTP về inbox, khiến kẹt 150s mỗi máy và fail hàng loạt (16/25 máy đêm 2026-09-12).
- **Quy tắc bất biến:**
  - **BẮT BUỘC** dùng web checklive `checkmail.live` (Playwright + mobile proxy theo repo `site ban hang clone`).
  - **CẤM TUYỆT ĐỐI** dựa vào on-device health check để kết luận trạng thái sống/chết của Gmail.

### 2. Xử lý khi phát hiện Gmail DIE
- Khi `checkmail.live` trả về `[die]`:
  1. Tự động sao lưu và xóa dòng Gmail DIE khỏi file nguồn `D:/OneDrive/TaadaaData/kibe/gmail_clean_v2.xlsx`.
  2. Ghi nhận tài khoản vào sheet `Audit Pending` trong `taikhoan_dat_v2_updated .xlsx` để cách ly.
  3. Gỡ bỏ tài khoản khỏi hệ điều hành Android (`remove_account_adb` trong `preflight_s7_rolling_cleanup.py`) để giải phóng slot máy.

---

## II. INVARIANT: LƯU TRỮ MẬT KHẨU & TÀI KHOẢN VỪA REG XONG

### 1. Lỗ hổng Skip Persistence khi thiếu `--result-dir`
- **Sự cố thực tế:** Khi chạy canary, watchdog hoặc lệnh tay (`python gmail_reg_v10.py <stt> --ss`), cờ `--result-dir` không được truyền vào.
- Hàm `persist_success_result(acc)` kích hoạt `[WORKBOOK_GUARD] Skip success persistence; use --result-dir and merge step for workbook writes` $\rightarrow$ Tài khoản tạo thành công trên máy Android nhưng **mật khẩu bị vứt bỏ, không ghi vào Excel hay bất kỳ file nào**!
- Vì mật khẩu không log plain text ra console, tài khoản bị mất vĩnh viễn mật khẩu, không thể đăng nhập bên ngoài hoặc bật 2FA.

### 2. Nguyên tắc Bắt Buộc cho Mọi Runner Tạo Tài Khoản
- **CẤM TUYỆT ĐỐI** bỏ qua việc lưu trữ khi thiếu cờ kết quả.
- Mọi hàm lưu kết quả (`persist_success_result`) **BẮT BUỘC phải có cơ chế Fallback Direct Workbook Save**:
  - Nếu có `--result-dir`: ghi file `.success.json` theo luồng chuẩn.
  - Nếu KHÔNG có `--result-dir`: tự động gọi `single_writer_workbook_update` ghi trực tiếp thông tin (`stt`, `email`, `password`, `ngay_sinh`, `ngay_tao`) vào `D:/OneDrive/TaadaaData/kibe/gmail_clean_v2.xlsx` và lưu một bản JSON dự phòng tại `runtime/success_results/`.

---

## III. THỜI ĐIỂM BẬT 2FA (2-STEP VERIFICATION) TRÊN ANDROID S7

### 1. Cơ chế xác minh danh tính của Google
- Để vào mục `Xác minh 2 bước` (2-Step Verification) trong `Quản lý Tài khoản Google -> Bảo mật`, Google **BẮT BUỘC yêu cầu nhập lại mật khẩu tài khoản** để xác nhận danh tính.
- Nếu để tài khoản ngâm vài ngày sau khi reg mới đi bật 2FA:
  - Google sẽ kích hoạt checkpoint xác minh danh tính bổ sung (Google Prompt gửi về thiết bị, nhưng do không có mail/SĐT khôi phục nên không xác minh được).
  - Xuất hiện cảnh báo `"Cảnh báo bảo mật quan trọng: Hoàn tất đăng nhập để tiếp tục. Đã xảy ra lỗi và bạn cần đăng nhập lại"`.

### 2. Quy chuẩn Bật 2FA Ngay Trong Flow Reg (In-Flow Activation)
- **BẮT BUỘC BẬT 2FA NGAY LẬP TỨC KHI VỪA TẠO XONG TÀI KHOẢN**:
  - Sau bước 13 (vừa vào Gmail Home, session đăng nhập đang còn nóng 100%):
  - Script mở ngay: `Avatar -> Quản lý tài khoản Google -> Bảo mật và đăng nhập -> Xác minh 2 bước`.
  - Điền `acc["pass"]` (đang có sẵn trong RAM) để qua bước xác minh danh tính.
  - Chọn `Ứng dụng Authenticator` $\rightarrow$ `Không thể quét mã QR`.
  - Trích xuất chuỗi Base32 Secret Key (32 ký tự).
  - Dùng `pyotp.TOTP(secret_key).now()` tạo mã OTP 6 số $\rightarrow$ nhập xác nhận.
  - Ghi Secret Key vào cột 4 (`2FA`) của `gmail_clean_v2.xlsx`.
- Tài khoản được bảo vệ bằng 2FA ngay từ phút đầu tiên sẽ chấm dứt 100% tình trạng bị Google AI quét khóa (70% die sau 3-5 ngày).

---

## IV. POLICIES VẬN HÀNH REG GMAIL (DIRECTIVE TỪ USER)

1. **CẤM ĐỔI IP TRƯỚC KHI REG:** Giữ nguyên IP proxy đang gán của thiết bị, không reset modem/recreate proxy bừa bãi.
2. **PICK 15 MÁY PROXY KHÁC NHAU:** Khi chạy batch 15 máy, hệ thống phải chọn 15 máy thuộc 15 cổng proxy duy nhất khác nhau (không chọn 2 máy chung 1 cổng proxy) để phân tán hoàn toàn địa chỉ IP.
3. **TĂNG MẠNH ENTROPY (ĐỘ NGẪU NHIÊN):** Họ tên kết hợp từ đệm, tên chính đa dạng; username thêm salt 3-5 ký tự ngẫu nhiên + đuôi từ khóa nghiệp vụ; mật khẩu kết hợp đa dạng mẫu để xóa sạch footprint bot.
4. **DỌN GMAIL DIE TRƯỚC KHI REG:** Gọi hook `preflight_s7_rolling_cleanup` kiểm tra và gỡ tài khoản Google DIE khỏi máy trước khi bắt đầu tạo tài khoản mới.
