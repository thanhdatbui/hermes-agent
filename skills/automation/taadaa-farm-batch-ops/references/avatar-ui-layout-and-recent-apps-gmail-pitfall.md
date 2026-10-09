# Avatar Batch UI Recovery & Recent-Apps Teardown Pitfalls

## 1. Hiện tượng: Chạy up avatar tự động làm văng/bật màn hình Gmail
### Triệu chứng:
Khi chạy batch upload avatar (hoặc canary avatar) trên máy Android farm (như Samsung S7), màn hình ứng dụng Gmail (`com.google.android.gm`) bất ngờ xuất hiện đè lên giao diện, thường là các màn hình checkpoint tài khoản Google (ví dụ: *"Quay video selfie để có thêm cách đăng nhập"* hoặc yêu cầu nhập passkey/xác thực bảo mật).

### Nguyên nhân kỹ thuật:
1. **Lệch layout Avatar Circle**:
   - Ở giao diện TikTok cũ: Avatar circle nằm **chính giữa màn hình** (`X = 540, Y = 336` hoặc `400`).
   - Ở giao diện TikTok mới: Username nằm bên trái (`X: 36 -> 720`), còn Avatar circle bị dồn sang **góc trên bên phải** (`[708,228][1080,564]`, center `(894, 396)`, node có `content-desc="Ảnh hồ sơ"`, `resource-id="bni"` / `"bmh"`).
   - Thao tác tap mù fallback `(540, 336)` hay `(540, 400)` bấm vào khoảng trống giữa username và avatar -> Không mở được bottom sheet chọn ảnh -> Script kết luận lỗi `[AVATAR_UPLOAD_MENU_MISSING]` hoặc `[AVATAR_EDIT_OPEN_FAILED]`.
2. **Kích hoạt Teardown `_close_recent_apps` khi failure**:
   - Khi workflow thất bại chưa đạt `DONE`, script kích hoạt dọn dẹp khẩn cấp qua `automation_core.startup.close_all_recent_apps`.
   - Hàm này gửi phím cứng **Recent Apps (keyevent 187)** để hiển thị ngăn xếp ứng dụng gần đây.
   - Nếu trong máy đã có sẵn một task Gmail đang chờ xác minh từ các ca trước (trong Recent task list), việc gửi keyevent 187 kèm phím Home (keyevent 3) hoặc tap trượt nút "Xóa tất cả" sẽ lôi cửa sổ task Gmail đó ra foreground, gây hiểu lầm là tool tự ý mở Gmail hoặc có tiến trình reg Gmail chạy ngầm.

---

## 2. Quy tắc xử lý và phòng tránh
1. **Định vị Avatar Circle trên UI mới qua XML trước khi tap mù**:
   - Tìm node `content-desc="Ảnh hồ sơ"` hoặc `resource-id` chứa `bni`, `bmh`, `bm2`.
   - Toạ độ center chuẩn trên màn 1080x1920: `X ~ 894, Y ~ 396`.
   - Tuyệt đối không hardcode tap `(540, 336)` khi XML dump đã có node avatar ở góc phải.
2. **Nhận diện Photo Picker Bypass**:
   - Một số phiên bản TikTok nhảy thẳng vào Photo Picker / DocumentsUI (`com.android.documentsui`, resource `o_9`, text `Gần đây`, `Recent`, `Recents`) thay vì mở bottom sheet menu "Tải ảnh lên" / "Chụp ảnh".
   - Phải kiểm tra cờ `already_at_picker` để bypass bước tìm menu, tránh throw ngoại lệ `AVATAR_UPLOAD_MENU_MISSING` oan.
3. **Phân biệt hiện tượng Gmail nhảy ra**:
   - Kiểm tra `dumpsys account`: nếu tài khoản Gmail đã có sẵn trong Accounts của Android, đây là task hệ thống của OS, không phải bot reg đang chạy.
   - Kiểm tra lock và tiến trình (`device-locks`, `psutil`): nếu không có lock hay worker nào đang chạy thì chỉ là task nền trong Recent apps bị trigger bởi teardown keyevent 187.
