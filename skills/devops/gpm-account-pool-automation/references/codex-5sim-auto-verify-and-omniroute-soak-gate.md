# Codex OAuth 5sim Auto-Verification, In-Flight Retry Loop & OmniRoute Soak Gate

## 1. Bản chất cơ chế bảo vệ của OpenAI với Codex OAuth
- Khi tài khoản đăng ký ChatGPT qua Web (Direct Email + OTP), OpenAI thường **chưa hỏi số điện thoại**.
- Tuy nhiên, khi ủy quyền vào **Codex CLI (`auth.openai.com/oauth/authorize?client_id=app_EMoamEEZ73f0CkXaXp7hrann...`)**, OpenAI luôn kích hoạt chốt chặn bảo mật **`https://auth.openai.com/add-phone`** (bắt buộc xác minh số điện thoại để lấy Authorization Code).
- **CẤM TUYỆT ĐỐI GOOGLE SSO**: Bấm "Continue with Google" khi chưa liên kết sẽ kích hoạt fraud checkpoint gắt gao hơn và vi phạm trực tiếp invariant dự án (`100% Direct Email + OTP, cấm Google SSO`).

## 2. Tiêu chí chọn số thuê 5sim (Kinh nghiệm thực tế từ Farm)
- **Khoảng giá tối ưu**: Loanh quanh **$0.05 - $0.12** (tương đương 1.200đ - 3.200đ/số), tỉ lệ nhận mã $\ge 20\% - 30\%$ là chấp nhận được.
- **Thứ tự xoay tua số (Waterfall Rotation)**:
  1. `argentina / virtual62` (~$0.05, rate ~30%)
  2. `philippines / virtual58` (~$0.107, rate ~26% - nổ SMS rất nhạy)
  3. `england / virtual34` (~$0.128, rate ~39%)
  4. `thailand / virtual34` (~$0.083, rate ~17%)
  5. `vietnam / virtual47` (~$0.128, rate chập chờn)
- **Tự hủy hoàn tiền 100% (Cancel Order)**:
  - Nếu sau 90 giây không thấy SMS nổ về, **bắt buộc gọi `https://5sim.net/v1/user/cancel/{order_id}`** để hoàn lại tiền vào số dư ví ngay lập tức.
  - **KỶ LUẬT THỰC THI (KHÔNG DỪNG LẠI BÁO CÁO GIỮA CHỪNG)**: Khi hủy đơn do không về OTP, script PHẢI **tiếp tục vòng lặp thử ngay số tiếp theo** (tối đa 5-6 attempts), CẤM dừng tiến trình chỉ để báo cáo việc hủy số.

## 3. Thao tác UI trên màn hình Add Phone & Workspace Chooser
1. **Chọn quốc gia**: Click dropdown `button[aria-haspopup="listbox"]` $\rightarrow$ Chọn option tương ứng `[role="option"][data-key="{ISO}"]` hoặc gõ tên nước + Enter.
2. **Điền số**: Điền `local_num` (bỏ mã quốc tế) vào `input[type="tel"]` $\rightarrow$ Submit.
3. **Màn hình chọn Workspace sau OTP**:
   - Khi điền OTP xong, OpenAI thường hiện màn hình:
     *"Chọn một không gian làm việc (Tài khoản cá nhân / Personal)"*
   - Bắt buộc click nút **"Tiếp tục" / "Continue"** hoặc thẻ Personal để hoàn tất redirect về callback port `1455`.

## 4. Chiến lược "Tạm tắt OmniRoute để ngâm 48h an toàn"
- **Tại sao phải tạm tắt?**: Tài khoản mới reg vừa ver số xong nếu đem vào pool OmniRoute gọi API dồn dập sẽ bị OpenAI gắn cờ spam (Velocity Check) dẫn tới revoke session hoặc ban nick.
- **Thực thi O(1) sau khi lấy token**:
  ```python
  import sqlite3
  conn = sqlite3.connect(r"C:\Users\Kibe\.omniroute\storage.sqlite")
  cur = conn.cursor()
  cur.execute("UPDATE provider_connections SET is_active = 0 WHERE id = ?", (connection_id,))
  conn.commit()
  conn.close()
  ```
- **Cronjob đánh thức sau 48h**:
  - Script `cron_omni_activate_soaked_codex.py` chạy định kỳ hàng giờ (`0 * * * *`).
  - Kiểm tra `codex_oauth_at` trong state JSON, nếu $\ge 48$ tiếng thì chạy lệnh:
    `UPDATE provider_connections SET is_active = 1 WHERE id = ?`
    để tự động mở kết nối cho hệ thống sử dụng an toàn.
