# Codex OpenAI Phone Verification & Proxy 1-1 Pairing Playbook

## 1. Bản chất cơ chế Phone Verification của OpenAI (Single-SIM Invariant)
- **Cơ chế Server-side Cooldown:**
  - OpenAI áp đặt rate-limit / cooldown nghiêm ngặt trên từng số điện thoại.
  - Sau khi 1 số SIM nhận OTP và xác thực thành công cho Profile 1, nếu lập tức nhập cùng số đó vào Profile 2:
    1. Form có thể tự động ép chuyển kênh sang WhatsApp: *"We couldn't send a text message to this phone number, so we switched to WhatsApp."*
    2. Nếu can thiệp gửi được SMS thứ 2 về (5sim nhận được 2 SMS trên 1 order), khi submit mã OTP 2 vào Profile 2, OpenAI sẽ chặn đứng ở backend với lỗi:
       > **"Số điện thoại này vừa được dùng gần đây. Vui lòng thử lại sau."** *(This phone number was used recently. Please try again later.)*
  - **Quy tắc bất biến:** Mỗi SIM mua từ 5sim chỉ dùng để kích hoạt cho **DUY NHẤT 1 tài khoản OpenAI / Codex**. Tuyệt đối không cố tái sử dụng liên tiếp để tránh mất thời gian và kẹt form.

## 2. Kỹ thuật bắn tỉa (Sniper) SIM Philippines Smart TNT trên 5sim
- **Dải số hợp lệ:** Chỉ các đầu số SIM vật lý Smart TNT: `0970`, `0930`, `0907`, `0919`, `0920`, `0928`, `0929` (giá `$0.1077`, `virtual58`).
- **Đầu số bị từ chối/ép WhatsApp:** Globe (`0927`, `0936`, `0945`, `0955`, `0975`, `0935`), DITO (`0960`, `0997`).
- **Chiến thuật bảo toàn vốn 100%:**
  - Mua SIM qua API `GET https://5sim.net/v1/user/buy/activation/philippines/virtual58/openai`.
  - Kiểm tra 3 chữ số đầu (`phone[3:6]`). Nếu không thuộc danh sách Smart TNT -> `GET https://5sim.net/v1/user/cancel/{order_id}` lập tức (< 0.5s) để được hoàn tiền 100%.
  - Khi điền vào form `https://auth.openai.com/add-phone`:
    - Nếu OpenAI báo lỗi đỏ hoặc không chuyển URL sang `phone-verification` -> Hủy hoàn tiền ngay.
    - Nếu chuyển sang `phone-verification`: Poll OTP trong tối đa 40s. Nếu không có SMS -> Hủy hoàn tiền.
    - Chỉ bấm `finish` đơn hàng khi đã nhận OTP và hoàn tất xác minh thành công.

## 3. Quy trình gán Proxy 1-1 cho Codex Connection trên OmniRoute
- **Vấn đề cốt lõi:** Khi thêm connection Codex mới qua luồng OAuth callback, OmniRoute mặc định gán kết nối ở chế độ `DIRECT` (`proxy: None`). Nếu không gán proxy, các request gọi GPT-5.6 / Codex sẽ thoát ra bằng IP trực tiếp của máy chủ thay vì IP proxy của profile GPM, dẫn đến rủi ro lệch footprint và bị ban acc.
- **Quy trình gán Proxy bắt buộc sau khi nạp connection:**
  1. Trích xuất proxy đã cấu hình trong GPM profile (`raw_proxy` hoặc `JsonData.Proxy`).
  2. Tra cứu `proxyId` tương ứng trong bảng registry của OmniRoute qua `GET http://127.0.0.1:20129/api/settings/proxies`.
  3. Gán proxy cho connection bằng API:
     ```http
     PUT /api/settings/proxies/assignments
     Content-Type: application/json

     {
       "scope": "account",
       "scopeId": "<codex_connection_id>",
       "proxyId": "<matched_proxy_id>"
     }
     ```
  4. Xác minh lại bằng endpoint resolve:
     ```http
     GET /api/settings/proxy?resolve=<codex_connection_id>
     ```
     Phải trả về `level: "account"` kèm thông tin host/port của proxy.
