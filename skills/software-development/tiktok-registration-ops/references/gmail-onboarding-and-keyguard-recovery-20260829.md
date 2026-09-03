# Gmail Onboarding Update Trap & Samsung Keyguard Recovery (2026-08-29)

## 1. Gmail App Update / First-Launch Onboarding Trap
- **Hiện tượng**: Khi App Gmail được update hoặc thêm account mới vào máy, app tự động hiện chuỗi 3 màn hình Onboarding (Setup Tour):
  1. *Welcome Tour*: "Mới có trong Gmail" (`welcome_tour_title`) / "OK" (`welcome_tour_got_it`).
  2. *Setup Addresses*: "Bạn có thể sử dụng ứng dụng này với tất cả địa chỉ email..." / "ĐƯA TÔI TỚI GMAIL" (`action_done`).
  3. *Meet Onboarding*: "Google Meet hiện đã có trong Gmail" (`dialog_wrapper`, `onboarding_title`) / "Đã hiểu" (`next_button`).
- **Hệ quả**: Chuỗi màn hình này che kín hòm thư và menu avatar, khiến hàm đọc OTP Gmail (`_try_get_otp_gmail_app`) và kiểm tra Google health báo `target_account_not_verified` / `fail_otp_not_found`.
- **Giải pháp**:
  - Tích hợp vòng lặp tự động phát hiện và dismiss toàn bộ chuỗi onboarding (`welcome_tour_got_it` -> `action_done` -> `next_button`) ngay trong `_try_get_otp_gmail_app` và `dismiss_gmail_startup_popup`.
  - Hỗ trợ cả resource-id mới `dialog_wrapper` bên cạnh `dialog_layout` cũ.

## 2. Samsung Keyguard Lockscreen Recovery (`fail_02_profile_tab`)
- **Hiện tượng**: Màn hình thiết bị Android Samsung bị khóa (`com.android.systemui`, text "Vuốt màn hình để mở khóa" / `emergency_call_button`). Phím Home (`keyevent 3`) không thể mở khóa Keyguard.
- **Hệ quả**: TikTok mở lên dưới lớp Keyguard, bấm vào tab "Hồ sơ / Profile" bị chặn -> văng lỗi `RuntimeError: [02_profile] Khong vao duoc tab Ho so/Profile`.
- **Giải pháp**:
  - Luôn gọi `prepare_android_for_automation(client)` ngay đầu `open_app()` để đánh thức và vuốt mở khóa màn hình.
  - Trong `go_to_profile()`, kiểm tra nếu XML chứa marker Keyguard (`vuot man hinh de mo khoa`, `cuoc goi khan cap`, `emergency_call`), lập tức gửi `keyevent 224` (WAKEUP) và vuốt mở khóa (`input swipe 540 1500 540 300 300`).

## 3. ATX Session Dump Resilience & Bounded Timeout
- **Hiện tượng**: Gọi qua `capture_ui_xml` cũ với timeout dài làm socket bị nghẽn, cạn tổng timeout (`UI_XML_TOTAL_TIMEOUT`) trước khi kịp kích hoạt `reset_atx_agent`.
- **Giải pháp**: Gọi trực tiếp `capture_atx_session_ui()` với timeout giới hạn 20s/lần. Sau 3 lần fail -> lập tức gọi `reset_atx_agent(client, timeout=15)` rồi retry 1 lần qua `capture_atx_session_ui()`.

## 4. CloneFBIG API Token Truncation vs Web UI Scraping
- **Hiện tượng**: Gọi API `api/buy_product` trên CloneFBIG trả về Token OAuth2 bị cắt ngắn (101 ký tự thay vì 457–500 ký tự chuẩn Microsoft MSA Artifacts) do lỗi JSON format của API shop.
- **Giải pháp**: Khi mua qua CloneFBIG, trích xuất dữ liệu trực tiếp từ trường `data-checkbox` trong bảng lịch sử đơn hàng trên Web UI (`https://clonefbig.com/product-orders`) qua CDP để nhận chuỗi Token đầy đủ 100%.
