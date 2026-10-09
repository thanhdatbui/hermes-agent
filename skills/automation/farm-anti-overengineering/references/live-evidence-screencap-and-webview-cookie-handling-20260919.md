# Kỷ Luật Nghiệm Thu Ảnh Hiện Trường & Xử Lý WebView/Cookie Popup (2026-09-19)

## 1. Kỷ Luật Bắt Buộc Nghiệm Thu Ảnh Hiện Trường Thật (Anti-Sleep/Black Screen & Anti-Home)
- **Hiện tượng lỗi 1 (Màn hình đen kịt / Black screen)**:
  - Khi chụp `adb exec-out screencap -p` lúc thiết bị Android đang tắt màn hình (`Display Power: OFF`), ảnh chụp ra toàn bộ pixel là `0, 0, 0` (đen kịt).
  - **Quy tắc bắt buộc**: BẮT BUỘC gửi lệnh đánh thức màn hình trước khi chụp:
    ```bash
    adb -s <SERIAL> shell input keyevent 224   # WAKEUP
    # Chụp trực tiếp vào framebuffer hoặc lưu ra sdcard rồi pull
    adb -s <SERIAL> shell screencap -p /sdcard/live_screen.png
    adb -s <SERIAL> pull /sdcard/live_screen.png <LOCAL_PATH>
    ```
- **Hiện tượng lỗi 2 (Gửi ảnh màn hình Home thay vì hiện trường app/lỗi)**:
  - Worker subagent sau khi chạy xong script thường tự động bấm phím HOME (`keyevent 3`) hoặc đóng app để dọn dẹp, sau đó mới chụp screencap nghiệm thu $\rightarrow$ Bị phạt gửi ảnh màn hình Home vô nghĩa.
  - **Quy tắc bắt buộc**: BẮT BUỘC chụp ảnh hiện trường **KHI APP / BROWSER VẪN ĐANG NẰM Ở FOREGROUND** (ngay tại thời điểm hoàn thành, lỗi hoặc dừng bước), TUYỆT ĐỐI KHÔNG bấm HOME rồi mới chụp.

---

## 2. Xử Lý WebView Mù DOM & Popup Cookie Trên Android (ChatGPT/Web Flow)
- **Nguyên nhân gốc rễ**:
  - Chrome trên Android thường hiển thị các trang web SPA (Single Page Application như `chatgpt.com`) dưới dạng đối tượng WebView nguyên khối:
    ```xml
    <node class="android.widget.FrameLayout" content-desc="Lượt xem trên web" bounds="[0,72][1080,1920]" />
    ```
  - Lệnh `uiautomator dump` không trích xuất được DOM bên trong WebView, khiến `find_node_in_xml` không tìm thấy các chuỗi văn bản như `"Chấp nhận tất cả"`, `"Cookie"`, `"Tiếp tục"`, dẫn đến kẹt timeout 120s và fail im lặng.
- **Giải pháp chuẩn**:
  - Khi nhận thấy cây UI là WebView nguyên khối hoặc sau 2-3 vòng lặp không bóc tách được node, BẮT BUỘC kích hoạt cơ chế fallback tap theo tọa độ chuẩn (chuẩn màn hình Samsung S7 1080x1920):
    - **Nút "Chấp nhận tất cả" (Accept all cookies)**: `X=540, Y=1780` (hoặc vùng `X=540, Y=1266` tùy layout dialog).
    - **Ô nhập "Email address"**: `X=540, Y=1150`.
    - **Nút "Tiếp tục" (Continue)**: `X=540, Y=1320`.
  - Kết hợp OCR WinRT (`winrt_ocr.py`) nếu cần xác định tọa độ động khi layout thay đổi.

---

## 3. Khóa Van 2FA Cho Quy Trình GPM Login & Phê Duyệt Trình Xác Thực (Google 2FA Flow)
- **Khóa van 2FA GPM Login**:
  - CẤM TUYỆT ĐỐI đưa tài khoản chưa có `2FA_Secret` vào luồng login GPM trên PC.
  - Lý do: Tài khoản chưa bật 2FA khi đăng nhập từ thiết bị lạ / proxy lạ sẽ bị Google siết `challenge/iap` (Hard Phone Verification đòi số điện thoại SMS) $\rightarrow$ Đốt hạn ngạch proxy và gây checkpoint nick.
- **Tự động bấm "Phê duyệt" (Approve) sau khi verify TOTP**:
  - Sau khi submit OTP 6 số thành công, Google Authenticator web thường hiện popup:
    > *"Phê duyệt trình xác thực này? Để đẩy nhanh quá trình này, bạn có thể phê duyệt trình xác thực mới... [Xóa] [Phê duyệt]"*
  - BẮT BUỘC script phải có bước `8b` tự động dò tìm nút `[Phê duyệt] / [Approve]` để click xác nhận ngay, tránh bị treo lơ lửng ở bước xác minh cuối cùng.
