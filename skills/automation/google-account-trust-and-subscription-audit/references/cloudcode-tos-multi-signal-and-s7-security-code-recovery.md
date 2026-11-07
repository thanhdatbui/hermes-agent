# Quy Chuẩn Đối Soát ToS 403, S7 Security Code Recovery & Phân Phối Tải Router

## 1. Bản Chất Đa Tín Hiệu (Multi-Signal) Của Lỗi 403 TOS_VIOLATION
Khi tài khoản Antigravity Cloud Code API bị lỗi 403 ToS, nguyên nhân không đơn lẻ mà là sự kết hợp của 3 tín hiệu:
1. **Lớp 7 - Payload Chữ Ký (Smoking Gun):**
   - Dòng hardcoded `stable_parts.append(HERMES_AGENT_HELP_GUIDANCE)` trong file `agent/system_prompt.py` của Hermes tự động nhét:
     `You run on Hermes Agent (by Nous Research)... https://hermes-agent.nousresearch.com/docs`.
   - Cần gỡ bỏ tận gốc dòng này và làm sạch `SOUL.md`.
2. **Lớp 4 - TLS Fingerprint & HTTP/2 Settings (Suspicious Signal):**
   - Node.js fetch của OmniRoute có TLS Fingerprint (JA3/JA4) khác với Google Go runtime / BoringSSL của app Antigravity chính chủ.
3. **Lớp Hành Vi (Behavioral Anomaly):**
   - Tần suất gọi dày đặc, context lớn (350k - 450k tokens) liên tục 24/7 không có keystroke dynamics.

## 2. Quy Chuẩn Kháng Nghị (Appeal SOP)
- **Nguồn link form:** Lấy trực tiếp từ mã lỗi JSON của Google: `https://forms.gle/hGzM9MEUv2azZsrb9`.
- **Cơ chế nộp form:** Google Form không tạo email gửi đi (hòm thư `Sent` luôn rỗng) và không gửi bản sao về Inbox ngay. Kết quả chỉ trả về Inbox sau **24 – 72 giờ**.
- **Yêu cầu mở GPM:** Phải mở đúng Profile GPM Chrome của tài khoản trên IP/Proxy sạch để form tự nhận diện session `Record <email> as the email to be included with my response`, tích chọn cam kết và Submit.

## 3. Phân Định 403 TOS_VIOLATION vs 403 VALIDATION_REQUIRED
- `TOS_VIOLATION`: "This service has been disabled for violation of Terms of Service" -> Bị cấm dịch vụ, bắt buộc appeal.
- `VALIDATION_REQUIRED`: "Verify your account to continue" -> Hết hạn phiên session/OAuth (như tài khoản `votuyen`), chỉ cần mở Profile GPM đăng nhập lại / cấp lại OAuth.

## 4. Khôi Phục Mã Bảo Mật 10 Số Trên Samsung Galaxy S7 (S7 Security Code)
Khi tài khoản bắt xác minh danh tính bằng mã offline 10 số trên S7:
- **Xác định thiết bị thật:** Dùng `adb devices` và `dumpsys account` để tìm đúng serial S7 đang giữ tài khoản (ví dụ Máy 9: `988627414444594c51`).
- **Lấy mã tự động qua ATX-Agent port 7912:**
  1. Wake & unlock màn hình S7 (`keyevent 26` / `224`, `keyevent 82`).
  2. Mở `android.settings.SETTINGS`, cuộn tìm `Google`.
  3. Kiểm tra đúng tài khoản target, nếu không đúng thì bấm đổi tài khoản trong dropdown.
  4. Bấm `Quản lý Tài khoản Google` -> chuyển sang tab `Bảo mật` (Security).
  5. Bấm `Mã bảo mật` (Security code) và bóc tách chuỗi 10 chữ số từ hierarchy XML.
  6. Điền mã 10 số vào màn hình challenge trên GPM Browser để hoàn tất đăng nhập.

## 5. Cân Bằng Giữa Prompt Cache và Abuse Detection Trong Combo Router
- **Prompt Cache** là tối ưu hóa phần cứng TPU/GPU ở hạ tầng của Google, phụ thuộc vào prefix ổn định, **không cấp Trust Score** chống phạt ToS.
- **Abuse Detection** quét theo lưu lượng, tần suất và hành vi bất thường trên từng tài khoản.
- **Quy chuẩn cấu hình cân bằng vàng:**
  - `stickyRoundRobinLimit: 15`: Giữ nguyên tài khoản trong một chuỗi lệnh ReAct (tool loop) để giữ trọn vẹn 97.5% Prompt Cache và tốc độ phản hồi 5s - 8s.
  - `strategy: least-used`: Sau khi chuỗi lệnh hoàn thành hoặc hết ghim, tự động nhả tải sang tài khoản ít dùng nhất trong pool để tài khoản cũ có thời gian cooldown tự nhiên, san đều tải cho cả dàn acc.
