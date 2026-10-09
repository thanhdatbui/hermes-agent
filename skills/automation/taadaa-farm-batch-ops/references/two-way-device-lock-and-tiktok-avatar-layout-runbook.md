# Two-Way Device Lock & TikTok Avatar UI Migration Runbook

## 1. Sự Cố Xung Đột Tiến Trình Do Hổng Lock 2 Chiều (Cross-Project Collision)
### Hiện tượng
- Đang chạy batch hoặc canary upload avatar / video TikTok trên một máy (ví dụ: Máy 13), đột nhiên màn hình máy nhảy sang ứng dụng khác (ví dụ: Gmail hiển thị checkpoint đăng nhập / selfie, hoặc Google Play Services).
- Quản trị viên/User dễ lầm tưởng là có cron ngầm tự ý can thiệp phá kịch bản.

### Nguyên nhân gốc rễ
1. **Hổng cơ chế Lock 2 chiều:**
   - Trong repo `Tiktok-video`, file `machine_inventory.py` từng có đoạn code bỏ qua lock:
     ```python
     def _filter_locks(entries, skipped, lock_root):
         # "bỏ hết cơ chế lock" -> return entries trực tiếp
         return entries
     ```
   - Khi chạy qua PowerShell launcher hoặc runner không ghi lock file ra thư mục tập trung (`~/.codex/device-locks` hoặc `~/AppData/Local/automation-core/device-locks`).
2. **Cronjob watchdog bên ngoài quét máy rảnh:**
   - Các watchdog như `post_noon_chain_watchdog` (chạy chuỗi Reg Gmail -> Add 2FA TikTok sau ca trưa) kiểm tra điều kiện kích hoạt bằng `has_active_device_locks()` trong thư mục lock chung.
   - Thấy không có file lock nào cho máy đang chạy upload, watchdog kết luận "farm đang idle" và kích hoạt batch `run_all.ps1` (Reg Gmail) hoặc `run_batch_live_2fa.py`.
   - Cả 2 tiến trình ADB cùng nã lệnh vào 1 thiết bị, gây giật cướp focus và làm vỡ quy trình của nhau.

### Quy tắc Bất biến (Hard Invariant)
- **TẤT CẢ các repo và kịch bản can thiệp máy farm** (`Tiktok-video`, `register gmail`, `tiktok-add-bao-mat-f2a`, `tiktok-luot`, tool tay):
  - **BẮT BUỘC** gọi `acquire_device_lock` trước khi gửi lệnh ADB.
  - **BẮT BUỘC** ghi file lock JSON với đầy đủ `machine`, `serial`, `project`, `pid`, `status="running"`.
  - **CẤM TUYỆT ĐỐI** comment out hoặc bypass hàm `_filter_locks()` trong `machine_inventory.py`.
  - Khi kết thúc lượt chạy (dù thành công hay thất bại), bắt buộc giải phóng lock an toàn.

---

## 2. Lệch Layout Avatar Trên TikTok Bản Mới & Khắc Phục
### Hiện tượng
- Kịch bản chạy đến bước `ENSURE_AVATAR` thì ném lỗi `[AVATAR_UPLOAD_MENU_MISSING] Không tìm thấy Tải ảnh lên`.
- Nhưng thực tế trên máy đã ở màn hình Profile cá nhân.

### Cơ chế lỗi
- **Layout TikTok cũ:**
  - Avatar circle nằm chính giữa màn hình: `(540, 336)` hoặc `(540, 400)`.
  - Nút "Sửa hồ sơ" có chữ rõ ràng hoặc icon bút chì bên cạnh.
- **Layout TikTok mới:**
  - Avatar circle bị dời hẳn sang **góc trên bên phải**: Bounds `[708, 228][1080, 564]`, tâm tap `(894, 396)`.
  - Node thường là Button bao ngoài: `resource-id="com.ss.android.ugc.trill:id/bni"`, `id="bmh"`, hoặc `content-desc="Ảnh hồ sơ"`.
  - Phía bên trái là Username, Handle, Follower.
  - Khi script cũ không tìm thấy nút sửa, nó fallback tap mù vào `(540, 336)` hoặc `(540, 400)` -> rơi đúng vào **khoảng trống giữa username và avatar**.
  - Kết quả: Avatar bottom sheet không bao giờ mở lên, script dump XML không thấy menu và ném lỗi oan `AVATAR_UPLOAD_MENU_MISSING`.

### Giải pháp kỹ thuật chuẩn
1. **Mở rộng nhận diện Avatar Node:**
   ```python
   avatar_node = (
       adapter._find_ui_element(current_xml, resource_id="bm2")
       or adapter._find_ui_element(current_xml, resource_id="bni")
       or adapter._find_ui_element(current_xml, resource_id="bmh")
       or adapter._find_ui_element(current_xml, content_desc="Ảnh hồ sơ")
       or adapter._find_ui_element(current_xml, text="Thêm ảnh")
   )
   ```
2. **Fallback tap có điều kiện:**
   Nếu không trúng node cụ thể, kiểm tra xem màn hình có dấu hiệu layout mới (`trill:id/bni` hoặc `trill:id/bmh`) để tap `(894, 396)`, chỉ tap `(540, 400)` trên layout cũ.
3. **Photo Picker Bypass:**
   Một số tài khoản khi tap avatar sẽ nhảy thẳng vào Photo Picker (`com.android.documentsui`, `resource_id="o_9"`, hoặc chứa text `"Gần đây"`, `"Recent"`) thay vì hiện bottom sheet "Tải ảnh lên / Chụp ảnh". Script phải coi đây là hợp lệ (`already_at_picker = True`) và chuyển thẳng sang bước chọn ảnh thay vì ném lỗi thiếu menu.

---

## 3. Cẩn Trọng Với Teardown Recent Apps
- Trong `close_all_recent_apps()`, việc gửi `keyevent 187` (phím Recent Task) sẽ mở màn hình chuyển đổi ứng dụng. Nếu thao tác tìm nút "Xóa tất cả" bị chậm hoặc trượt, Android có thể focus lại vào ứng dụng nền trước đó (như Gmail).
- Đảm bảo gửi `keyevent 3` (HOME) ngay sau khi dọn dẹp để đảm bảo thiết bị trở về màn hình chính Launcher sạch sẽ trước khi nhả lock.
