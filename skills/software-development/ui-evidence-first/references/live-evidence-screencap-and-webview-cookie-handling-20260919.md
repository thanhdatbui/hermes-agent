# Kỷ Luật Nghiệm Thu Ảnh Hiện Trường & Xử Lý WebView/Cookie Popup (2026-09-19)

## 1. Kỷ Luật Bắt Buộc Nghiệm Thu Ảnh Hiện Trường Thật (Anti-Sleep/Black Screen & Anti-Home)
- **Hiện tượng lỗi 1 (Màn hình đen kịt / Black screen)**:
  - Khi chụp `adb exec-out screencap -p` lúc thiết bị Android đang tắt màn hình (`Display Power: OFF`), ảnh chụp ra toàn bộ pixel là `0, 0, 0` (đen kịt).
  - **Quy tắc bắt buộc**: BẮT BUỘC gửi lệnh đánh thức màn hình trước khi chụp:
    ```bash
    adb -s <SERIAL> shell input keyevent 224   # KEYCODE_WAKEUP
    adb -s <SERIAL> shell screencap -p /sdcard/live_screen.png
    adb -s <SERIAL> pull /sdcard/live_screen.png <LOCAL_PATH>
    ```
- **Hiện tượng lỗi 2 (Gửi ảnh màn hình Home thay vì hiện trường app/lỗi)**:
  - Worker subagent sau khi chạy xong script thường tự động bấm phím HOME (`keyevent 3`) hoặc đóng app để dọn dẹp, sau đó mới chụp screencap nghiệm thu $\rightarrow$ Bị phạt gửi ảnh màn hình Home vô nghĩa.
  - **Quy tắc bắt buộc**: BẮT BUỘC chụp ảnh hiện trường **KHI APP / BROWSER VẪN ĐANG NẰM Ở FOREGROUND** (ngay tại thời điểm hoàn thành, lỗi hoặc dừng bước), TUYỆT ĐỐI KHÔNG bấm HOME rồi mới chụp.
- **Khóa góc xoay màn hình (Orientation Lock)**: Tránh trường hợp thiết bị tự xoay ngang (`mCurrentRotation=1`) làm lệch toàn bộ tọa độ tap. Phải đảm bảo `user_rotation = 0` và `accelerometer_rotation = 0` (Portrait 1080x1920).

---

## 2. Xử Lý WebView Mù DOM & Popup Cookie Trên Android (ChatGPT/Web Flow)
- **Nguyên nhân gốc rễ**:
  - Chrome trên Android thường hiển thị các trang web SPA (như `chatgpt.com`) dưới dạng đối tượng WebView nguyên khối:
    ```xml
    <node class="android.widget.FrameLayout" content-desc="Lượt xem trên web" bounds="[0,72][1080,1920]" />
    ```
  - Lệnh `uiautomator dump` không trích xuất được DOM bên trong WebView, khiến `find_node_in_xml` không tìm thấy các chuỗi văn bản như `"Chấp nhận tất cả"`, `"Cookie"`, dẫn đến kẹt timeout 120s và fail im lặng.
- **Giải pháp chuẩn hóa đã kiểm chứng**:
  - Khi nhận thấy cây UI là WebView nguyên khối hoặc sau 2-3 vòng lặp không bóc tách được node, BẮT BUỘC kích hoạt cơ chế fallback tap theo tọa độ chuẩn (chuẩn màn hình Samsung S7 1080x1920):
    - **Nút "Chấp nhận tất cả" (Accept all cookies)**: Tọa độ `X=540, Y=1780`.
    - **Ô nhập "Email address"**: Tọa độ `X=540, Y=1315` (hoặc `X=540, Y=1150`).
    - **Nút "Tiếp tục" (Continue)**: Tọa độ `X=540, Y=1485`.
  - Kết hợp OCR WinRT (`winrt_ocr.py`) nếu cần xác định tọa độ động khi layout thay đổi.

---

## 3. Khóa Van 2FA Cho Quy Trình GPM Login & Phê Duyệt Trình Xác Thực (Google 2FA Flow)
- **Khóa van 2FA GPM Login**:
  - CẤM TUYỆT ĐỐI đưa tài khoản chưa có `2FA_Secret` vào luồng login GPM trên PC để tránh bị Google siết checkpoint SĐT SMS (`challenge/iap`).
- **Tự động bấm "Phê duyệt" (Approve) sau khi verify TOTP**:
  - Sau khi submit OTP 6 số thành công, Google Authenticator web hiện popup *"Phê duyệt trình xác thực này? ... [Xóa] [Phê duyệt]"*.
  - **Quy luật Google**: Popup này chỉ xuất hiện 1 lần duy nhất lúc vừa add Authenticator. Nếu đóng tab mà không bấm, Google sẽ đưa vào trạng thái chờ ngâm bảo mật.
  - BẮT BUỘC script phải có bước `8b` tự động dò tìm nút `[Phê duyệt] / [Approve]` để click xác nhận ngay, tránh bị treo lơ lửng ở bước xác minh cuối cùng.

---

## 4. Giới Hạn Của App Gmail Trên Samsung S7 (Android 8 - Oreo) & Bẫy Đồng Bộ Hóa
- **Nguyên nhân kẹt màn hình "Tài khoản chưa được đồng bộ hóa"**:
  - Toàn bộ farm Samsung S7 chạy Android 8.0 (Oreo). Google đã ngừng hỗ trợ giao thức đồng bộ (push sync) cho app Gmail phiên bản cũ trên Android 8 (`OsVersionNudgeActivity` - *"Hãy cập nhật thiết bị để đảm bảo an toàn"*).
  - Do đó, dù tài khoản Gmail hoàn toàn LIVE 100% trong OS Settings, app Gmail native trên Android 8 vẫn bị chặn kéo thư mới về hộp thư đến cục bộ. Script vuốt làm mới trong app Gmail sẽ luôn dẫn đến `OTP_FETCH_TIMEOUT`.
- **Phân biệt dữ liệu Excel**:
  - `gmail_clean_v2.xlsx`: CHỈ chứa tài khoản sạch, đã bật 2FA, mail khôi phục chuẩn (`thanhdatbui1995@gmail.com`), tuyệt đối không chứa mail dính `khoalee`.
  - `master_gmail_manager.xlsx`: Bảng tổng quản trị chứa cả nick đang ngâm, nick dính khoalee, nick DIE.
- **Hướng xử lý tối ưu**: Đối với các tác vụ đòi hỏi đọc OTP hoặc OAuth token, ưu tiên thực hiện trên PC thông qua GPM Chrome đời mới qua Proxy của máy để bypass hoàn toàn giới hạn Android 8.
