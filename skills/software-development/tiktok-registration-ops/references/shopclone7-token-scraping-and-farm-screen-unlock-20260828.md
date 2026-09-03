# Quy Tắc Mua Mail OAuth2, Giới Hạn 6 Acc/Máy và Mở Khóa Màn Hình (2026-08-28)

## 1. Chính Sách Target Kép và Giới Hạn 6 Acc/Máy (Farm 80 Máy = 480 Acc)
- **Giới hạn cứng:** Mỗi máy tối đa 6 tài khoản TikTok. Quét cột TikTok ID trong workbook tracking (`taikhoan_dat_v2_updated .xlsx`), nếu máy đã có $\ge 6$ TikTok ID thì LOẠI VĨNH VIỄN khỏi detector/manifest.
- **Điều kiện kép:** Chỉ cấp máy vào batch reg khi thỏa mãn đồng thời:
  1. `machine_account_count < 6`.
  2. Còn mail nguồn hợp lệ trong `gmail_clean_v2.xlsx` chưa từng xuất hiện trong tracking.
- **Quy mô ca đêm:** Chạy tối đa 30 targets/ca, cuốn chiếu 6 workers song song giãn cách 2-8s để tránh bị TikTok gắn cờ rate-limit / captcha.

## 2. Pitfall Trích Xuất Token OAuth2 Graph API từ ShopClone7 (CloneFBIG / BoxTaiKhoan)
- **Lỗi cắt cụt qua API:** Khi gọi qua endpoint JSON `api/buy_product`, chuỗi refresh token dài ~457 ký tự của Microsoft MSA Artifacts có thể bị API cắt ngắn còn ~101 ký tự do giới hạn trường JSON/DB của bên bán -> gọi Microsoft OAuth2 báo `AADSTS70000: The provided value for 'refresh_token' is not valid`.
- **Giải pháp trích xuất chuẩn:** Truy cập trực tiếp Web UI đơn hàng (`/product-order/<trans_id>`) qua Chrome CDP (port 9222), đọc giá trị đầy đủ từ thuộc tính `data-checkbox` / input ẩn trong bảng.
- **Xác thực trước khi nạp:** Bắt buộc chạy `exchange_refresh_token(refresh_token, client_id)` kiểm tra với `https://login.microsoftonline.com/common/oauth2/v2.0/token` đạt Access Token (len ~1,400-1,500 bytes) trước khi nạp vào `gmail_clean_v2.xlsx`.

## 3. Mở Khóa Màn Hình Samsung Keyguard Trước Khi Mở App
- **Triệu chứng:** Máy 78 bị fail ở bước vào Tab Profile do màn hình rơi vào Keyguard Samsung (`Vuốt màn hình để mở khóa` / `com.android.systemui:id/emergency_call_button`).
- **Nguyên nhân:** Lệnh Home (`input keyevent 3`) không thể tự mở khóa màn hình Samsung Keyguard khi máy đang khóa màn hình.
- **Khắc phục:**
  - Tích hợp `prepare_android_for_automation(client)` hoặc `_wake_and_unlock` ngay đầu `open_app()`.
  - Trong `go_to_profile()`, nếu phát hiện XML chứa từ khóa Keyguard / CUỘC GỌI KHẨN CẤP, lập tức gửi `keyevent 82` (MENU) hoặc `input keyevent 224` (WAKEUP) + `input swipe 540 1500 540 300 300` để vuốt mở khóa ngay lập tức.

## 4. Giới Hạn Timeout Bounded Cho ATX Dump & Tự Động Reset
- **Nguyên nhân treo ATX:** Gọi `_atx_capture_ui_xml` với timeout 40s làm socket bị nghẽn và hết sạch 60s `UI_XML_TOTAL_TIMEOUT` trước khi kịp gọi `reset_atx_agent`.
- **Khắc phục:** Giới hạn mỗi lần thử ATX tối đa 15-20s qua `capture_atx_session_ui(client, timeout=20)`. Sau 3 lần thử fail, kích hoạt `reset_atx_agent(client, timeout=15)` để restart stub qua monkey và active polling tìm PID mới trước khi kết thúc.
