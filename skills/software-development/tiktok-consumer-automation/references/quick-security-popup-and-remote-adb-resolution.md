# Case Study: Quick Security Bottom-Sheet Popup & Remote Fleet ADB Resolution

## 1. Quick Security Tip Modal ("Hãy cùng kiểm tra bảo mật nhanh nhé")

### Hiện tượng
Trong quá trình chuyển đổi tài khoản (account switcher) hoặc mở Profile preflight trên TikTok Android, ứng dụng hiển thị popup dạng bottom sheet:
- **Tiêu đề:** `"Hãy cùng kiểm tra bảo mật nhanh nhé"` (res-id: `com.ss.android.ugc.trill:id/zdv`)
- **Nội dung:** `"Hoàn thành một số mẹo bảo mật cá nhân hóa để tăng cường tính bảo mật cho tài khoản của bạn."`
- **Nút hành động:** `"Tiếp tục"` (Button tím/hồng ở dưới cùng, res-id: `com.ss.android.ugc.trill:id/omz`)
- **Nút đóng (X):** `android.widget.Button` ở góc trên bên phải của modal dialog (`bounds="[936,866][1056,998]"` trên màn hình 1080x1920) nhưng **hoàn toàn không có text và không có content-desc** (`text=""`, `content-desc=""`).

### Pitfall
Hàm nhận diện benign popup `detect_quick_security_popup()` trong `automation_core` trước đây bắt buộc phải tìm thấy element có content-desc hoặc text là `"Đóng"`. Khi nút X bị TikTok bỏ trống thuộc tính văn bản, hàm nhận diện thất bại và trả về `None`. Flow feed session coi đây là `verify-dialog` chưa được dismiss, dừng máy an toàn và báo lỗi `verify dialog not dismissed`, dẫn đến hàng chục máy fail oan hàng loạt (ví dụ: 22/80 máy trong Ca 1).

### Giải pháp chuẩn
Khi phát hiện tiêu đề `Hãy cùng kiểm tra bảo mật nhanh nhé`, nếu không tìm thấy element có nhãn `"Đóng"`, tìm fallback:
- Element là `android.widget.Button` (hoặc `clickable="true"`), nằm ở góc trên bên phải của modal (y nằm trong khoảng trên của dialog bounds, x >= 80% chiều rộng màn hình).
- Đóng popup bằng cách tap vào tọa độ center của nút đóng X này thay vì fail-closed sang `manual-needed`.

---

## 2. Remote ADB Fleet PATH Resolution (`ATX_SESSION_UNAVAILABLE` cụm Admin)

### Hiện tượng
Khi điều phối chạy remote cluster (ví dụ cụm Admin 201-280 qua `192.168.110.119:5037`):
- Lệnh ADB từ shell vẫn kết nối tốt (`59 devices attached`).
- Toàn bộ 80 máy dừng ngay tại bước `close_all_apps_start` với `ui_dump_error: ATX_SESSION_UNAVAILABLE`.

### Nguyên nhân gốc rễ
Tiến trình con chạy cron/powershell không có `adb.exe` trong biến môi trường `PATH` hệ thống (hoặc `sh.exe` của MSYS/git-bash không thấy `adb` mặc định mà `adb` nằm tại `C:\Program Files (x86)\xiaowei\tools\adb.exe`). Khi `automation_core.adb` probe capability, nó văng `ADBError: adb executable not found: adb`, khiến toàn bộ pipeline ATX session dump và dynamic port-forwarding sụp đổ trên toàn cụm remote.

### Quy tắc điều phối
1. Đảm bảo path của `adb` được inject rõ ràng vào child environment hoặc fallback cấu hình `adb_path` chuẩn (`C:\Program Files (x86)\xiaowei\tools\adb.exe`) khi khởi chạy worker/runner cụm remote.
2. Kiểm tra capability `AdbClient` bằng probe đơn lẻ O(1) trước khi dispatch batch lớn trên dàn máy remote.
