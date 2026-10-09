# 5sim Realtime Pricing, Zero-Cost Retry & Automated Codex Phone Verification

## 1. Bản chất cơ chế tài chính 5sim (Zero-Cost Retry)
- **Hold Balance vs Charge**: Khi mua một số điện thoại kích hoạt (`/v1/user/buy/activation/{country}/{operator}/{product}`), số tiền tương ứng chỉ ở trạng thái **tạm giữ (Hold)**.
- **Hoàn tiền 100% khi Cancel**:
  - Nếu nhà cung cấp dịch vụ (OpenAI) không gửi mã SMS về trong 60s, hoặc báo lỗi số không hợp lệ, gọi ngay `GET /v1/user/cancel/{order_id}`.
  - 5sim lập tức hoàn 100% số tiền về tài khoản (`status: CANCELED`), **không mất bất kỳ khoản phí nào**.
- **Chỉ trừ tiền khi thành công**: Tiền chỉ thực sự bị trừ khi có SMS đổ về và người dùng/script gọi `GET /v1/user/finish/{order_id}` hoặc hết hạn thời gian order sau khi đã nhận SMS.

## 2. Realtime Price & Success Rate Dynamic Filtering
- Giá và tỷ lệ thành công (`rate`, `rate24`) của 5sim thay đổi liên tục theo thời gian thực dựa trên lưu lượng mua và độ nhả OTP của từng dịch vụ.
- **Top đầu số tối ưu chi phí & tỷ lệ (Thực nghiệm 2026):**
  * 🇦🇷 **Argentina (`virtual62`)**: **$0.05 (~1.270đ)** — Rẻ nhất, tỷ lệ nổ OTP ~13% (cao gấp 2.5 lần Philippines). Rẻ hơn **gấp 3.1 lần** so với mua acc tạo sẵn từ shop ngoài như SumiStore (4.000đ).
  * 🇬🇧 **England (`virtual58`)**: **$0.1815** — Tỷ lệ thành công cực cao (23.64%), sạch sẽ khi cần tốc độ cao.
  * 🇵🇭 **Philippines (`virtual58`)**: **$0.1077** — Tỷ lệ ~5%, hay bị OpenAI gắn cờ blacklist dải số.
- **Không bao giờ hardcode danh sách nhà mạng**: Trước mỗi lượt mua, gửi request nhẹ (`~0.2s`):
  `GET https://5sim.net/v1/guest/prices?product=openai`
- **Bộ lọc ngân sách linh hoạt (`max_price <= $0.10`)**:
  - Lọc các nước có `cost <= max_price` và `count >= 20` khả dụng.
  - Sắp xếp ưu tiên: `rate24` (tỷ lệ thành công 24h gần nhất) giảm dần -> `rate` hiện tại giảm dần -> `cost` rẻ nhất tăng dần.

## 3. Khắc phục bẫy OAuth Codex trên GPM Profile (`auth.openai.com/add-phone`)
- **Nguyên nhân**: Dù profile GPM đã đăng nhập sẵn ChatGPT Web (`chatgpt.com`), khi thực hiện OAuth Codex CLI với scope `offline_access`, OpenAI kích hoạt yêu cầu Phone Verification (`auth.openai.com/add-phone`).
- **Kỷ luật chống Spam & Ban Nick Oan (Anti-Brute-Force Invariants):**
  1. **Max 2 lần thử / 1 account:** Tuyệt đối không thử quá 2 số điện thoại trên cùng một tài khoản. Nếu 2 số đều bị từ chối hoặc timeout OTP, PHẢI HỦY ĐƠN HOÀN TIỀN NGAY và chuyển sang profile tiếp theo.
  2. **Giãn cách an toàn (Stagger Delay):** Nghỉ tối thiểu 6s giữa 2 lần nhập số và giữa 2 profile liên tiếp để tránh thuật toán Abuse Detection của OpenAI khóa tài khoản.
- **Tự động hóa DOM trên Playwright CDP**:
  1. **Chọn mã quốc gia**: Nút chọn quốc gia là React-Aria Listbox (`button[aria-haspopup="listbox"]`). Click nút, dùng `keyboard.type("Argentina")` rồi chọn `[role="option"]:has-text("Argentina")`.
  2. **Kênh nhận mã (SMS Radio)**: Đảm bảo radio nhận SMS được click: `input[type="radio"][value="sms"]`.
  3. **Điền số điện thoại**: Điền phần số đã cắt mã quốc gia (`+54`) vào `input[type="tel"]` với độ trễ phím tự nhiên (`delay=35`).
  4. **Bắt mã lỗi OpenAI từ chối số**: Lắng nghe `[role="alert"]` hoặc nếu URL không chuyển sang challenge OTP sau 5s, gọi `cancel` ngay để đổi số khác, không đợi timeout.
  5. **Polling SMS & Điền OTP**: Polling `GET /v1/user/check/{order_id}` mỗi 5s trong tối đa 45s. Khi nhận được OTP 6 số, điền vào các ô mã và hoàn tất.
  6. **BẮT BUỘC Xử lý màn hình hậu OTP (Post-OTP Forms):** Sau khi điền OTP, OpenAI thường chưa chuyển ngay về callback mà hiện màn hình `about-you` (yêu cầu điền Tên, Tuổi) hoặc nút `Tiếp tục / Authorize`. Bắt buộc script phải tự động điền form và click các nút này thì callback mới bắn về `http://127.0.0.1:1455`.
  7. **Đồng bộ toàn diện 4 Combos Codex:** Ngay khi tạo thành công Connection Codex:
     - Gán Proxy tĩnh 1-1 qua `PUT /api/settings/proxies/assignments`.
     - Nạp đồng thời vào cả 4 combos: `codex-terra-pool`, `codex-luna-pool`, `codex-terra`, `codex-luna` để đảm bảo tính nhất quán (Parity 100%).
