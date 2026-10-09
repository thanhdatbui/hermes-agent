# Hotmail ➔ GPM ➔ ChatGPT ➔ Codex OAuth (SMS Verify) ➔ 48h Soak Deactivated on OmniRoute

## 1. Bản chất cơ chế OpenAI OAuth Codex & Yêu cầu xác thực Phone
- **OAuth Codex CLI luôn kích hoạt cổng xác minh số điện thoại (`/add-phone`)**: Khác với việc dùng web ChatGPT thông thường, khi ủy quyền vào client Codex, hệ thống Fraud/Risk của OpenAI luôn đòi hỏi xác minh SMS số điện thoại nếu session chưa có lịch sử tin cậy lâu dài.
- **TUYỆT ĐỐI CẤM GOOGLE SSO (PROJECT_RULES.md Invariant)**:
  - Cấm bấm nút `Continue with Google` / `Tiếp tục với Google`.
  - Nếu tài khoản được tạo dạng Direct Email/Password/OTP, bấm Google SSO sẽ khiến OpenAI coi là liên kết mới trên proxy và lập tức chặn cứng đòi số hoặc gắn cờ bot.
  - Phải ẩn nút Google SSO hoặc cấm click trong script automation.

## 2. Chiến lược Tối ưu: Ver Codex xong TẠM TẮT (Deactivate) trên OmniRoute để ngâm 48h
- **Chiến thuật**:
  1. `HOTMAIL_LOGIN` ➔ `CHATGPT_REG` (100% Direct Email + OTP).
  2. Đi OAuth Codex luôn trong cùng phiên làm việc trên đúng 1 IP Proxy dân cư đó.
  3. Tại màn hình `add-phone`, tự động thuê sim Việt Nam qua 5sim API để nhận OTP và hoàn tất cấp Authorization Code cho OmniRoute.
  4. **Quan trọng nhất**: Ngay khi OmniRoute nhận Token từ callback port 1455, script thực thi lệnh SQL cập nhật trạng thái `is_active = 0` trong database OmniRoute:
     ```python
     import sqlite3
     conn = sqlite3.connect(r"C:\Users\Kibe\.omniroute\storage.sqlite")
     cursor = conn.cursor()
     cursor.execute("UPDATE provider_connections SET is_active = 0 WHERE id = ?", (conn_id,))
     conn.commit()
     conn.close()
     ```
  5. Tài khoản nằm ngâm ở chế độ "ngủ" trong pool OmniRoute đủ 24–48h, không bị agent gọi request bào API dồn dập, giúp Fraud Score hạ xuống tự nhiên. Sau 48h, cronjob bật `is_active = 1` để đưa vào hoạt động chính thức.

## 3. Quy tắc Thuê Sim 5sim cho Codex
- **Chặn trần giá 0.14$**: Không sử dụng các đầu số quốc tế giá cao (> $0.14).
- **Ưu tiên số Việt Nam (VN)**:
  - Chọn nhà mạng `virtual34` hoặc tương đương giá ~$0.10 (~2.600đ).
  - Tỉ lệ nhận mã ~28-30% nhưng giá rẻ, phù hợp với IP Proxy Việt Nam của farm.
  - Tự động click dropdown quốc gia trên OpenAI (`button[aria-haspopup="listbox"]`), gõ `Viet` + Enter để chọn `Việt Nam (+84)` trước khi điền số.
- **Tự động hủy hoàn tiền**: Nếu sau 2-3 phút không có SMS hoặc OpenAI từ chối số, gọi ngay `https://5sim.net/v1/user/cancel/{order_id}` để 5sim hoàn 100% tiền vào balance.
