# Xử Lý Lỗi Network / Retry Overlay ("Chạm để thử lại" / "Không có kết nối Internet")

## 1. Hiện tượng & Triệu chứng
- **Alert**: `[FARM ALERT: MÁY N] DỪNG PHIÊN`
- **Triệu chứng**: `network/error/retry marker detected; swipe recovery (2 swipes) still stuck`
- **Màn hình**: TikTok hiển thị overlay "Không có kết nối Internet. Chạm để thử lại" / "Đã xảy ra lỗi / Thử lại" / "Tap to retry" / "No internet connection".

## 2. Nguyên nhân gốc (Root Cause)
- Khi TikTok gặp lag mạng hoặc proxy phản hồi chậm lúc tải feed, màn hình chuyển sang trạng thái lỗi kết nối.
- `classifier.py` gán nhãn `manual-needed:network`.
- Khi vào `_swipe_recovery_on_stuck`, cơ chế phục hồi tìm handler qua `find_matching_handler` trong `flows/benign_popup_registry.py`. Nếu handler `network_error_retry_overlay` chưa được đăng ký, nó sẽ fallback sang lệnh vuốt màn hình `input swipe 540 1400 540 400 300`.
- Trên TikTok, thao tác vuốt cuộn không kích hoạt reload dữ liệu của màn hình lỗi mạng, mà bắt buộc phải tap vào nút "Thử lại" / "Chạm để thử lại" ("Tap to retry") hoặc reload feed.
- Do đó, sau 2 lần swipe, màn hình vẫn còn nguyên lỗi mạng và script dừng phiên với lý do `swipe recovery (2 swipes) still stuck`.

## 3. Quy trình khắc phục chuẩn
1. **Đăng ký handler trong `python_runner/flows/benign_popup_registry.py`**:
   - Hàm `_detect_network_error_retry(xml_content, ocr_text)`:
     - Negative exclusions: Tuyệt đối không match nếu XML/OCR chứa các từ khóa nhạy cảm (Login, Password, Captcha, OTP, Security check).
     - Positive match: Bắt các cụm từ "không có kết nối internet", "đã xảy ra lỗi", "lỗi mạng", "chạm để thử lại", "thử lại", "tap to retry", "retry".
   - Hàm `_dismiss_network_error_retry(ctx)`:
     - Duyệt cây UI XML tìm node có text/desc hoặc resource-id chứa "thử lại", "chạm để thử lại", "tap to retry", "retry", "reload".
     - Tap chính xác vào tâm của node đó; nếu không tìm thấy node cụ thể, fallback tap vào vùng nút retry trung tâm (540, 1000 hoặc 540, 1550).
   - Đăng ký vào `BENIGN_POPUP_REGISTRY`:
     `register_popup_handler(RegistryEntry("network_error_retry_overlay", 71, _detect_network_error_retry, _dismiss_network_error_retry, True, "manual"))`
2. **Cập nhật `feed_swipe_smoke.py`**:
   - Trong `_capture_step` khi gặp `NETWORK_RETRY_SCREENS`, gọi `find_matching_handler` để tự động tap reload trước khi fallback sang force-stop.
3. **Kiểm thử Unit Test**:
   - Thêm test trong `python_runner/tests/test_benign_popup_registry.py` kiểm tra positive match, negative exclusions (Login/Captcha) và dismiss tap logic.
4. **Chạy Canary Test thực tế**:
   - `powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <ID> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run`
   - Bắt buộc xác nhận `final_status: success` với đủ số swipe hoàn thành.
