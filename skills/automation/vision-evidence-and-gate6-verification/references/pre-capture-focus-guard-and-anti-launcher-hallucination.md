# Pre-Capture Focus Guard & Anti-Launcher Hallucination Protocol

## 1. Sự Cố Hiện Trường & Bài Học Xương Máu
- **Hiện tượng:** Coordinator chạy lệnh chụp màn hình trên thiết bị Farm (Máy 61), đăng ký receipt qua `guard_media_vision_gate.py` và gửi thẻ `MEDIA:`. Tuy nhiên ảnh gửi đi lại là **Màn hình chính (Launcher/Home Screen)** của Samsung S7 (với các icon Photos, Chrome, Cài đặt, Laban Key...), trong khi tin nhắn text báo cáo khẳng định: *"Đã soi mắt kiểm tra qua vision: Màn hình Profile hiển thị nhãn chữ đỏ 'Đã ghim' và 33,3K view"*.
- **Hậu quả:** Vi phạm trực tiếp **Invariant Chống Gửi Ảnh Mù** và Gate 6; User phát hiện ngay lập tức và mất hoàn toàn niềm tin vào báo cáo của Agent.
- **Nguyên nhân gốc rễ:**
  1. Ứng dụng mục tiêu (TikTok) bị văng ngầm hoặc chưa lên foreground (đang ở `LauncherActivity` hoặc `SplashActivity`), nhưng Agent vẫn chạy `adb screencap` lấy thẳng frame buffer.
  2. Agent bị ảo giác (hallucination): do ở bước trước vừa chạy lệnh tap tọa độ nên giả định màn hình đang ở Profile, không thực sự đọc semantic tokens của ảnh vừa chụp.
  3. Lưới video bị khuất dưới nếp gấp (below-the-fold): Trên Samsung S7 ($1080 \times 1920$), phần header Profile (Avatar, Nickname, Bio, Chỉ số) chiếm trọn nửa trên màn hình, lưới video bài đăng bị che lấp nếu không cuộn lên.

---

## 2. Quy Trình Chặn Lỗi 4 Bước Bắt Buộc (Invariant)

### Bước 1: Pre-Capture Focus Verification
Trước khi chụp màn hình nghiệm thu, BẮT BUỘC kiểm tra focus hiện tại của thiết bị:
```bash
python D:/Taadaa/tools/inspect_machine.py <N>
```
- Nếu `mCurrentFocus` là `com.sec.android.app.launcher/...` (Launcher) hoặc `...SplashActivity`:
  - Kích hoạt lại app: `adb -s <serial> shell monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1`
  - Chờ 3-4 giây cho app load xong Splash.
  - Chạm vào tab đích (ví dụ tab Hồ sơ: `input tap 972 1880`).

### Bước 2: Viewport Scroll Cho Nội Dung Dưới Nếp Gấp (Below-the-fold)
- Với màn hình Profile TikTok để nghiệm thu Ghim video (Pin Top) hoặc danh sách bài đăng:
  - Header chiếm từ `y: 0` đến `y: 850`.
  - Phải thực hiện vuốt nhẹ để kéo lưới video lên vùng hiển thị chính:
    ```bash
    adb -s <serial> shell input swipe 540 1300 540 700 300
    ```
  - Chờ 1.5 giây cho hiệu ứng cuộn ổn định trước khi screencap.

### Bước 3: Post-Capture Semantic Verification (Anti-Launcher Check)
Sau khi chụp ảnh (`screencap -p` và pull về PC), BẮT BUỘC chạy WinRT OCR đối soát nội dung ảnh TRƯỚC KHI ký receipt:
```bash
python D:/Taadaa/tools/run_winrt_ocr.py "<path_to_image>"
```
- **Tiêu chuẩn kiểm duyệt âm tính (CẤM GỬI):**
  - Nếu OCR xuất hiện các icon Launcher: `Photos`, `Chrome`, `Laban Key`, `Cửa hàng Play`, `Điện thoại`, `Tin nhắn`, `Máy ảnh`, `Xóa bộ nhớ đệm` $\rightarrow$ **FAIL-CLOSED NGAY**, CẤM ký receipt, quay lại Bước 1.
  - Nếu OCR chỉ có chữ `TikTok` ở giữa màn hình $\rightarrow$ Đang kẹt SplashActivity, chờ 3s rồi tap lại.
- **Tiêu chuẩn kiểm duyệt dương tính (ĐẠT):**
  - Phải chứa username chính xác (`@<username>`), hoặc đúng Tên hiển thị, hoặc các nút đặc thù của Profile (`Sửa hồ sơ`, `Bạn bè`, nhãn `Đã ghim`).

### Bước 4: Đăng Ký Receipt & Soi Mắt Thật
- Chỉ sau khi Bước 3 xác nhận ảnh ĐÚNG màn hình đích:
  ```bash
  python D:/Taadaa/tools/guard_media_vision_gate.py --register-receipt "<path>"
  ```
- Mở ảnh qua `browser_vision` để mắt thấy tận mắt các chi tiết (nhãn đỏ Đã ghim, số view, không lỗi popup/đen màn hình).
- Soạn tin nhắn phản hồi chứa đầy đủ bằng chứng cụ thể mắt thấy được.
