# Codex CLI OAuth Phone Verification & 5sim / SumiStore Automation Patterns

## 1. Bản chất phân biệt giữa ChatGPT Web vs Codex CLI OAuth
- **ChatGPT Web (`chatgpt.com`):** Dùng OAuth Google thường, chỉ cần session cookie, không bắt buộc verify số điện thoại (SĐT). Tuy nhiên dễ dính lỗi **HTTP 413 Payload Too Large** khi agent gửi system prompt dài, nhiều tools schema và context code.
- **Codex CLI OAuth (`auth.openai.com/oauth/authorize`):** Cấp quyền developer với scope `offline_access`. OpenAI **bắt buộc xác minh số điện thoại (`/add-phone`)** bằng OTP SMS một lần cho tài khoản mới để phòng chống abuse API. Sau khi verify thành công, session token không bao giờ bị dính lỗi 413, chịu được payload lớn hàng trăm KB.

## 2. Kinh nghiệm thực chiến với 5sim cho dịch vụ `openai`
### Cơ chế tài chính của 5sim:
- 5sim áp dụng cơ chế **Hold Balance (tạm giữ tiền)** khi cấp số.
- Nếu không nhận được SMS sau 1–2 phút, gọi ngay `GET /v1/user/cancel/{order_id}` để **hoàn lại 100% tiền ngay lập tức**, không mất phí. Chỉ khi có SMS OTP và bấm `finish` mới bị trừ tiền.
- Polling kiểm tra SMS qua `GET /v1/user/check/{order_id}`. Nên đặt thời gian chờ tối thiểu **90s - 120s** thay vì 50s vì SMS gateway quốc tế thường chuyển tiếp chậm.

### Pitfall đầu số siêu rẻ (<= $0.10):
- Các quốc gia giá rẻ ($0.05 - $0.07) như Argentina (+54), Anh (+447), Brazil (+55)... thường xuyên bị OpenAI **Silent Drop SMS** (trên UI OpenAI báo "Đã gửi mã" nhưng gateway SMS chặn không chuyển tiếp đến nhà mạng). Tỷ lệ thành công thực tế gần như 0%.
- Nhiều kho hiển thị số lượng lớn nhưng khi gọi mua API trả về `no free phones` (ảo hoặc bị gom hết).
- Cần lọc realtime bảng giá `GET /v1/guest/prices?product=openai`, ưu tiên các quốc gia có `rate24` hoặc `rate72` thực tế > 10% (như USA virtual63 $0.148, Cambodia $0.13, Greece $0.149).

### Sự thật về cổng nạp tiền 5sim:
- 5sim đã **bỏ hoàn toàn** các cổng nạp tiền Rúp (RUB) nội địa Nga (Qiwi, YooMoney, thẻ MIR).
- Hiện chỉ còn nạp qua Crypto (USDT BEP20/TRC20, USDC) neo cứng 1 USDT = $1 USD, hoặc các ví điện tử Châu Á (Alipay, UnionPay). Người dùng thông thường không còn cách nạp RUB giá rẻ trực tiếp.

## 3. Kiến trúc Shop API bên thứ ba (Ví dụ SumiStore / Bee shop)
- **Kho hàng API (`/api/tele-products`):** Thường chỉ bán các mặt hàng tài khoản tạo sẵn (Gmail, CapCut, tài khoản ChatGPT đã ver phone sẵn, Key API). Xác thực qua header `X-Tele-API-ID`.
- **Dịch vụ Thuê SIM / OTP:** Thường là tính năng nội bộ được bot Telegram gọi thẳng sang các provider gốc (SMSPool, 5sim, ViOTP). Nếu web không mở REST API cho thuê SIM, hướng tự động hóa duy nhất là dùng **Telegram Userbot (Telethon/Pyrogram)** để bắt sự kiện tin nhắn và click nút Inline Button tự động thay cho thao tác tay.
- **Chiến lược giá:** Tài khoản "ChatGPT Free đã ver phone Codex" bán sẵn trên shop thường có giá rất rẻ (~4.000đ, chỉ chênh 200đ so với 1 SMS thuê trên 5sim), nên cân nhắc mua sẵn qua API để tiết kiệm thời gian chờ OTP.
