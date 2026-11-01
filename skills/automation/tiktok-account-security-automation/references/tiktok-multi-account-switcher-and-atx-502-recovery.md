# Multi-Account Switcher & Fast Account Focus Recovery (TikTok Android Farm)

## 1. Vấn Đề Lạc Focus Tài Khoản Trên Dàn 8-Nick
- Trên các máy farm Samsung Galaxy S7 (chứa 8 slot tài khoản TikTok), sau khi mở app, app thường giữ nguyên tài khoản được dùng gần nhất (ví dụ slot 1 thay vì slot 2 cần đổi thông tin).
- Nếu bot đi thẳng vào *Cài đặt và quyền riêng tư* -> *Tài khoản* mà không kiểm tra username hiện tại, bot sẽ đổi nhầm email cho nick khác hoặc báo cáo sai tài khoản.

## 2. Kỹ Thuật Bung Account Switcher Ổn Định Nhất (Top Name Tap)
Có 2 cách bung switcher:
1. **Cách 1 (Cuộn đáy Cài đặt):** Dễ bị chạm nhầm nút đăng xuất hoặc cuộn quá tay.
2. **Cách 2 (Bung trực tiếp từ Profile - KHUYÊN DÙNG):**
   - Từ màn hình Profile cá nhân, tap thẳng vào tọa độ vùng tên hiển thị / username trên đỉnh màn hình: `[200, 300]`.
   - App sẽ lập tức bung tấm Bottom Sheet `Chuyển đổi tài khoản` với danh sách toàn bộ các tài khoản đang login.
   - Quét dump XML tìm node chứa username cần switch (ví dụ `text="hollybsulliv33"` tại `[252, 786][577, 846]`), click trực tiếp vào tâm node.
   - Chờ 5 giây và xác nhận banner popup: `"Đã đổi sang [Tên Nick]"` trước khi thực hiện các bước thay đổi credential tiếp theo.

## 3. Quy Trình Khắc Phục Lỗi ATX-Agent HTTP 502 Bad Gateway
- **Bản chất 502:** Khi gọi RPC JSON (`/jsonrpc/0`) hoặc `/dumpUI` gặp `urllib.error.HTTPError: HTTP Error 502: Bad Gateway`:
  - Bản thân daemon `atx-agent` (port 7912) **VẪN HOẠT ĐỘNG BÌNH THƯỜNG** (`/version` trả về 200 OK `0.10.1`).
  - Lỗi 502 xảy ra do service stub nội bộ `com.github.uiautomator` (chạy trên port nội bộ `9008`) bị Linux kernel kill (OOM SIGKILL 137 khi app TikTok ngốn nhiều RAM) hoặc chưa được khởi động.
- **Cơ chế phục hồi chuẩn 3 bước:**
  1. **Bước 1 (Đánh thức stub qua API ATX):**
     Gửi request POST rỗng tới endpoint `/uiautomator`:
     ```python
     import urllib.request
     req = urllib.request.Request('http://127.0.0.1:<forward_port>/uiautomator', data=b'{}', headers={'Content-Type':'application/json'})
     # Trả về: "Successfully started"
     ```
  2. **Bước 2 (Khởi động lại toàn diện nếu Bước 1 không phản hồi):**
     ```bash
     python D:/Taadaa/tools/with_device_lock.py --machine <N> -- adb -s <serial> shell \
       "am force-stop com.github.uiautomator; am force-stop com.github.uiautomator.test; /data/local/tmp/atx-agent server --stop; sleep 1; /data/local/tmp/atx-agent server -d"
     ```
     *Lưu ý gói AndroidJUnitRunner trên Samsung S7 Android 8:* Gói kiểm thử thực tế là `androidx.test.runner.AndroidJUnitRunner` (không phải `android.support.test.runner.AndroidJUnitRunner`).
  3. **Bước 3 (Fallback Visual + WinRT OCR khi DOM quá nặng):**
     Nếu TikTok DOM quá sâu khiến uiautomator liên tục bị OOM/SIGKILL khi dump XML:
     - Không cố dump XML để tránh crash máy.
     - Dùng ngay luồng thị giác: Chụp ảnh qua ADB `adb -s <serial> exec-out screencap -p > screen.png` và dùng WinRT OCR (`automation_core.ui_extract.ocr_screen_boxes`) để xác định tọa độ các nút/ô input rồi click theo tâm bounds.
