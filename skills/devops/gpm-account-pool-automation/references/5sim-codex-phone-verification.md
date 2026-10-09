# 5SIM Automated SMS Verification & Codex OAuth Protocol

## 1. Bản chất cơ chế 5sim API & Tối ưu Chi phí cho User
- **Khẩu vị User (Invariant)**: Cân bằng giữa tỷ lệ thành công và giá rẻ, ưu tiên các option có giá **$\le \$0.10$**.
- **Cơ chế Hoàn tiền 100% (Zero Risk)**:
  - 5sim chỉ "Hold" (tạm giữ) số dư khi order số (`GET /v1/user/buy/activation/{country}/{operator}/{product}`).
  - Nếu sau 60–90 giây không nhận được SMS từ OpenAI, script BẮT BUỘC gọi ngay:
    `GET /v1/user/cancel/{order_id}`
  - 5sim lập tức nhả hold và hoàn trả 100% số dư về tài khoản. Chỉ trừ tiền khi có SMS OTP thật và gọi finish.
  - Nếu số bị OpenAI báo lỗi định dạng hoặc đã tồn tại: gọi `GET /v1/user/ban/{order_id}` để đổi số khác mà không mất tiền.

## 2. Bảng Xếp hạng Quốc gia $\le \$0.10$ cho OpenAI (`product=openai`)
Dữ liệu quét trực tiếp từ 5sim API:
1. **Argentina (`argentina` / `virtual62`)**: **$0.0500** (~1.200đ) — Rate: 4.7% – 6.1%. Lựa chọn rẻ nhất.
2. **England (`england` / `virtual51`)**: **$0.0609** (~1.500đ) — Rate: 4.3% (Kho số ~80.000 số).
3. **Brazil (`brazil` / `virtual51`)**: **$0.0769** (~1.900đ) — Rate: 1.8%.
4. **Thailand (`thailand` / `virtual34`)**: **$0.0833** (~2.000đ) — Rate 24h: **17.4%** (Kho số cực lớn >270.000 số, tỷ lệ hit cao nhất phân khúc rẻ).
5. **Portugal / South Africa**: **$0.1000** — Rate: 7% – 9.4%.

## 3. Chrome CDP Profile Bền vững (`:9222`)
- Cổng remote debugging `9222` của Hermes sử dụng:
  `--user-data-dir="C:\Users\Kibe\AppData\Local\hermes\browser_profile" --profile-directory="Default"`
- Toàn bộ session đăng nhập Google, 5sim (`thanhdatbui1995@gmail.com`), Shopee... được lưu vĩnh viễn trên đĩa.
- Không cần yêu cầu user đăng nhập lại ở các phiên sau; token API được lưu tại `C:\Users\Kibe\.5sim_token`.

## 4. Quy trình Tự động hóa Auto-Retry Loop cho Codex OAuth
1. Khởi động profile GPM đã login ChatGPT Web qua CDP.
2. Điều hướng URL ủy quyền: `http://127.0.0.1:20129/api/oauth/codex/start-callback-server`.
3. Bắt màn hình `https://auth.openai.com/add-phone`.
4. Vòng lặp lấy số:
   ```python
   for target in [("argentina", "virtual62"), ("england", "virtual51"), ("thailand", "virtual34")]:
       order = buy_number(target[0], target[1], "openai")
       if not order: continue
       fill_phone_to_openai(order['phone'])
       sms_code = poll_sms(order['id'], timeout=75)
       if sms_code:
           submit_otp(sms_code)
           finish_order(order['id'])
           break
       else:
           cancel_order(order['id']) # Hoàn tiền 100%
   ```
5. Bắt callback `http://localhost:1455/auth/callback` chuyển về OmniRoute để lưu `refresh_token` vĩnh viễn vào pool Codex.
