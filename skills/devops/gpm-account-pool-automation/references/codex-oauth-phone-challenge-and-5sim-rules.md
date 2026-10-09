# Codex OAuth Phone Challenge & 5sim Automation Rules

## 1. Bản chất cơ chế Add-Phone của OpenAI khi gọi Codex OAuth
- Khi một ứng dụng bên ngoài (như Codex CLI hoặc OmniRoute callback flow) gọi URL ủy quyền OAuth (`auth.openai.com/oauth/authorize?client_id=app_EMoamEEZ73f0CkXaXp7hrann...`), OpenAI áp dụng chính sách bảo mật khắt khe hơn web thông thường.
- Ngay cả khi tài khoản đã đăng nhập ChatGPT trên browser/profile, hành vi cấp quyền OAuth vào CLI cho tài khoản chưa có số điện thoại đã xác minh đều sẽ kích hoạt chốt chặn:
  `https://auth.openai.com/add-phone` (Cần có số điện thoại - Add Phone Number).
- "Ngâm 24-48h" không tự động xóa bỏ yêu cầu số điện thoại đối với client CLI. Giải pháp chuẩn là tự động hóa xác thực SMS OTP ngay khi gặp màn hình này.

## 2. Quy tắc cấm tuyệt đối Google SSO (Strict Invariant)
- **CẤM TUYỆT ĐỐI** bấm vào nút "Tiếp tục với Google" / "Continue with Google" (`[data-provider="google"]`) trong bất kỳ tình huống nào khi login OpenAI/ChatGPT hoặc Codex OAuth.
- Việc dùng Google SSO trên proxy dân cư khiến OpenAI coi đó là liên kết tài khoản mới / hành vi bot và lập tức kích hoạt checkpoint số điện thoại hoặc khóa phiên.
- Bắt buộc tuân thủ: 100% Direct Email + Password hoặc Direct Email + OTP hòm thư.

## 3. Thuật toán chọn số 5sim & Ưu tiên số Việt Nam (VN)
- Theo chỉ đạo của User, **ưu tiên số Việt Nam (+84)** với chi phí tối ưu (~0.10$ / ~2.600đ) và chấp nhận tỷ lệ nhận mã thực tế (~28-30%), thay vì các đầu số giá cao $0.14+ (Mỹ, Hy Lạp).
- Quy tắc lọc Pool thời gian thực:
  1. Lọc giá: `cost <= max_price` (mặc định trần $\le 0.14\$$).
  2. Sắp xếp ưu tiên:
     ```python
     def sort_key(x):
         is_vn = 0 if x["country"] == "vietnam" else 1
         return (is_vn, -x["rate24"], -x["rate72"], x["cost"])
     ```
  3. Chọn quốc gia trên giao diện OpenAI:
     - Click dropdown quốc gia (`button[aria-haspopup="listbox"]`).
     - Chọn option tương ứng với ISO (ví dụ: `VN` -> `[role="option"]:has-text("Việt Nam")` hoặc `+84`).
     - Điền số điện thoại đã cắt prefix quốc gia.
     - Nếu trong vòng 2 phút không có SMS, gọi API `cancel_number` để 5sim hoàn tiền 100%, sau đó thử số tiếp theo.

## 4. Chuỗi quy trình tối ưu cho Hotmail Farm
- **Combo trọn gói trong 1 lượt:**
  `GPM Profile Create -> Hotmail Login -> Reg ChatGPT (Direct Email + OTP) -> Codex OAuth -> Auto-ver SMS VN (5sim) -> Add OmniRoute Connection -> Close GPM Profile`.
- Giảm thiểu việc phân mảnh trạng thái, gom gọn tài nguyên và đưa tài khoản vào phục vụ ngay cho pool Codex.
