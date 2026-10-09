# TikTok Avatar UI Layout Mismatch, Backdrop Tap Trap & Mandatory Device Lock

## 1. Sự cố đụng độ tiến trình (Cron Reg Gmail vs Canary Upload Avatar)
### Hiện tượng:
Màn hình "Tạo mật khẩu mạnh" hoặc xác minh Gmail (`do.thuan.05xbjk546@gmail.com`) bất ngờ xuất hiện đè lên giao diện khi đang chạy Canary up avatar.

### Nguyên nhân gốc rễ (Root Cause):
1. **Lỗ hổng Bypass Lock trong launcher upload**:
   - Trong `Tiktok-video/scripts/tiktok_workflow/machine_inventory.py`, hàm `_filter_locks` từng bị bypass (`return entries`), và `state_machine.py` không gọi `acquire_device_lock`.
   - Khi Coordinator chạy canary trên Máy 13, thiết bị không được ghi nhận lock trong `~/.codex/device-locks/`.
2. **Cronjob `post_noon_chain_watchdog` quét thấy máy rảnh**:
   - Cronjob chạy lúc 15:32 kiểm tra thư mục lock thấy rỗng, lập tức đẩy tiến trình `run_parallel.ps1` (Reg Gmail) vào Máy 13.
   - Tiến trình reg Gmail chạy ngầm từ 15:38 đến 16:06, gọi `pm clear com.google.android.gm` và đẩy app Gmail vào flow xác minh mật khẩu/checkpoint.
   - Khi script TikTok upload chạy song song, 2 tiến trình đè activity và tranh chấp input của nhau.

### Quy tắc Invariant bắt buộc (User Rule):
> "Kể cả khi tao giao việc cho mày làm, mày cũng phải lock lại (tất nhiên là lúc đó máy rảnh) và sau đó không cron nào được chiếm."
- **Preflight Check**: Trước khi chạy bất kỳ canary hay manual task nào, kiểm tra lock và PID owner. Nếu máy bận -> Dừng ngay.
- **Mandatory User Lock**: BẮT BUỘC acquire lock với `user_authorized=True`, `pinned=True`, `project="tiktok-upload"` (hoặc qua biến môi trường `HERMES_USER_AUTHORIZED=1`).
- **Cronjob Hard-Block**: Tất cả cronjob (reg Gmail, 2FA, feed session) khi thấy file lock `user_authorized=True` hoặc `status in ("active", "running", "queued")` BẮT BUỘC PHẢI SKIP thiết bị đó.

---

## 2. Lệch Layout UI Profile Mới & Bẫy Chạm Backdrop (Backdrop Tap Trap)

### Layout UI Profile TikTok mới:
- **Bản cũ**: Avatar circle to nằm chính giữa màn hình (`X = 540, Y = 336` hoặc `400`).
- **Bản mới**: Avatar circle thu nhỏ dồn sang góc trên bên phải (`[708,228][1080,564]`, center `894, 396`), node có `resource-id="bni"` / `"bmh"` hoặc `content-desc="Ảnh hồ sơ"`. Phía bên trái nhường chỗ cho username và nút *"Thêm tiểu sử"* (`[36,633][887,717]`).

### Cơ chế "Bẫy Chạm Backdrop" (Backdrop Tap Trap):
1. **Mở Bottom Sheet thành công**: Khi tap trúng Avatar circle `(894, 396)`, TikTok đã mở thành công Bottom Sheet chứa các lựa chọn: *"Tải ảnh lên"*, *"Chụp ảnh"*, *"Xem ảnh hồ sơ"*.
2. **Cú tap mù đóng menu**: Code cũ không kiểm tra xem menu đã mở trên `current_xml` chưa, mà lại tiếp tục tap vào tọa độ avatar `(894, 396)`. Khi Bottom Sheet đang mở bên dưới, tọa độ `(894, 396)` nằm ở **vùng tối mờ bên ngoài (Backdrop)** -> Android lập tức **đóng cụt Bottom Sheet lại**!
3. **Tap trượt nút thống kê**: Sau khi tự tay đóng mất menu, script tap tiếp tọa độ mù `(540, 580)` (chạm trúng nút thống kê *"Thích"* của Profile), rồi quét màn hình không thấy chữ *"Tải ảnh lên"* đâu nữa -> Văng lỗi `AVATAR_UPLOAD_MENU_MISSING`.

---

## 3. Quy tắc Check-First Invariant trong `ENSURE_AVATAR`
1. **Kiểm tra trước khi Tap (Check-First)**:
   Nếu Bottom Sheet hoặc Photo Picker đã xuất hiện trên `current_xml`, tap chọn ngay mục upload, TUYỆT ĐỐI KHÔNG tap lại vào tọa độ avatar hay vùng backdrop:
   ```python
   already_at_picker = (
       "com.android.documentsui" in (current_xml or "")
       or any(k in (current_xml or "") for k in ("Gần đây", "Recent", "Recents", "Pictures", "Albums"))
       or bool(adapter._find_ui_element(current_xml, resource_id="o_9"))
   )
   tapped_upload = already_at_picker or (
       adapter._tap_if_found(current_xml, text="Tải ảnh lên")
       or adapter._tap_if_found(current_xml, text="Upload photo")
       or adapter._tap_if_found(current_xml, text_contains="Upload photo")
       or adapter._tap_if_found(current_xml, text_contains="Tải ảnh")
       or adapter._tap_if_found(current_xml, text_contains="Thư viện")
       or adapter._tap_if_found(current_xml, text_contains="Bộ sưu tập")
       or adapter._tap_if_found(current_xml, text_contains="Gallery")
       or adapter._tap_if_found(current_xml, resource_id="g9u")
   )
   ```
2. **Khử hoàn toàn các cú tap mù**:
   - Không tap `(540, 336)` hay `(540, 400)` khi node avatar ở góc phải (`bni`/`bmh`).
   - Xóa bỏ hoàn toàn cú tap `(540, 580)` để không vô tình bấm nút "Thích".
