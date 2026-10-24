# Triage Lỗi 403 VALIDATION_REQUIRED: Phân Biệt Re-OAuth vs Gỡ Cờ Device Phone Verification

## Bối Cảnh
Khi một tài khoản Google AI Pro (Antigravity pool) bị Google áp cờ `VALIDATION_REQUIRED` ở tầng API Cloud Code (`daily-cloudcode-pa.googleapis.com`), triệu chứng trên hệ thống rất dễ gây nhầm lẫn:
1. **Quota trên dashboard OmniRoute hiển thị 100% Full:** Do request bị chặn ngay tại API Gateway của Google (HTTP 403 `PERMISSION_DENIED`), 0 token được chuyển vào engine inference $\rightarrow$ Quota Google vẫn nguyên vẹn 100%.
2. **Re-OAuth báo thành công nhưng tài khoản vẫn chết:** Chạy lại luồng cấp quyền `/api/oauth/antigravity/authorize` trên GPM Profile chỉ cấp mới access/refresh token cho client Code Assist. Việc này **hoàn toàn KHÔNG gỡ bỏ được cờ chặn bảo mật** của Google upstream.

---

## Cạm Bẫy Trọng Yếu (Critical Pitfalls)
- **Cạm bẫy ngộ nhận Re-OAuth là Fix Validation:** Tuyệt đối không nhầm lẫn giữa việc re-auth lấy token và gỡ cờ Device Verification. Nếu chỉ re-OAuth, token mới sinh ra vẫn bị Google 403 ngay lượt gọi kế tiếp.
- **Cạm bẫy False Positive do Combo Fallback:** Khi test một connection bị 403 qua OmniRoute `/v1/chat/completions`, router sẽ tự động failover sang tài khoản sống khác trong pool và trả về `200 OK`. Phải dùng `isolated_chat_test` trong `vm_rescue_lib.py` (tắt toàn bộ connection khác, chỉ bật 1 connection mục tiêu) và kiểm tra `call_logs` theo đúng `connection_id`.
- **Cạm bẫy đóng GPM Profile khi đang quét QR (Broken Handshake):** Tab trình duyệt hiển thị mã QR giữ kết nối WebSocket/long-polling thời gian thực với server Google. Nếu đóng profile GPM trước hoặc trong lúc user đang dùng điện thoại quét, kết nối bị đứt, điện thoại sẽ báo lỗi và tài khoản vẫn kẹt 403.

---

## Quy Trình Xử Lý Chuẩn (GPM Live QR Handshake)

### Bước 1: Kích hoạt lỗi tươi và trích xuất `validation_url`
Bắn 1 request cô lập ép connection ID (dùng `isolated_chat_test` với model `antigravity/claude-sonnet-4-6` hoặc `gemini-3.8-flash-tiered`) để nhận phản hồi 403 tươi từ Google:
```python
# Lấy validation_url mới nhất (plt token TTL ~1-2 phút) từ log hoặc upstream body:
# "validation_url": "https://accounts.google.com/v3/signin/continue?plt=...&continue=https://developers.google.com/gemini-code-assist/auth/auth_success_gemini..."
```

### Bước 2: Khởi chạy GPM Profile chính chủ và điều hướng
1. Khởi chạy profile GPM tương ứng qua Local API `http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}?win_scale=1.0`.
2. Kết nối qua Playwright CDP (`connect_over_cdp`).
3. Set viewport lớn (`1280x900`) để đảm bảo mã QR render với độ phân giải cao và không bị méo.
4. Điều hướng vào `validation_url` (`wait_until='domcontentloaded'`), chờ 4-5s để trang "Xác minh thông tin để tiếp tục" hiển thị mã QR cùng link rút gọn `g.co/verify/...`.

### Bước 3: Soi mắt kiểm tra và bàn giao quét QR
1. Chụp ảnh full màn hình và gọi `browser_vision` mở ảnh soi mắt xác nhận:
   - Đúng email đích hiển thị trên màn hình.
   - Mã QR hiển thị rõ nét, không bị che khuất bởi popup hay lỗi render.
2. Gửi ảnh kèm thẻ `MEDIA:<path>` cho user.
3. **BẮT BUỘC GIỮ PROFILE GPM MỞ:** Không gọi `browser.close()` hay stop profile trong lúc chờ user thao tác.
4. Nhắc user dùng **Camera mặc định của điện thoại** (iPhone / Android) quét trực tiếp, **tuyệt đối CẤM dùng app Zalo** (Zalo làm hỏng session handshake).

### Bước 4: Kiểm chứng cô lập và nghiệm thu
Sau khi user xác nhận đã quét xong trên điện thoại:
1. Chờ 3-5s để server Google gỡ cờ bảo mật.
2. Chạy `isolated_chat_test(connection_id, model='antigravity/gemini-3.8-flash-tiered')`.
3. Kiểm tra kết quả trả về:
   - `status == 200` và `choices[0].message.content` trả về nội dung hợp lệ $\rightarrow$ Gỡ cờ thành công 100%.
   - Nếu gặp `model_cooldown` 429 tạm thời do OmniRoute nhớ lỗi trước đó, chờ hết `reset_seconds` rồi test lại.
4. Cập nhật `is_active = 1` trong `provider_connections` (`storage.sqlite`).
5. Đóng profile GPM qua Local API để giải phóng tài nguyên.
