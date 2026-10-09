# Quy tắc Lock 2 Chiều Cho Tác Vụ Chỉ Định (Canary / Manual) & Bẫy Backdrop Avatar TikTok

## 1. INVARIANT: BẮT BUỘC LOCK THIẾT BỊ KHI USER GIAO VIỆC (USER-ASSIGNED MANDATORY LOCK)
**Quy tắc tối cao do User chỉ thị:**
> "Kể cả khi t giao việc cho mày làm, mày cũng phải lock lại (tất nhiên là lúc đó máy rảnh) và sau đó không cron nào được chiếm."

### Lỗ hổng đã triệt tiêu:
- Trước đây một số repo (như `Tiktok-video/scripts/tiktok_workflow/machine_inventory.py`) từng bypass `_filter_locks` hoặc chạy canary không acquire lock với `user_authorized=True`.
- Hậu quả: Khi Coordinator chạy canary hoặc lệnh tay trên Máy N, các cronjob nền (`post_noon_chain_watchdog` Reg Gmail, `run_batch_live_2fa.py`, nuôi lướt TikTok) quét thư mục lock thấy rỗng, tưởng máy rảnh liền điều phối tool khác vào giành máy -> Hai tiến trình đè màn hình, văng activity, xung đột nghiêm trọng.

### Trình tự chuẩn mực BẮT BUỘC khi Coordinator nhận việc:
1. **Kiểm tra máy rảnh O(1)**:
   - Quét file lock tại `~/.codex/device-locks/machine_<N>.lock.json` và `~/AppData/Local/automation-core/device-locks/`.
   - Nếu tồn tại lock và PID còn sống (`psutil.pid_exists(pid)`): **DỪNG LẠI NGAY**, báo cáo máy đang bận, TUYỆT ĐỐI CẤM force-stop hay can thiệp.
2. **Acquire User Lock trước khi chạm vào máy**:
   - Khởi tạo file lock với `user_authorized=True`, `pinned=True`, `status="running"`.
   - Khi chạy script PowerShell / Python launcher: Truyền biến môi trường `HERMES_USER_AUTHORIZED=1` để runtime ép cứng `user_authorized=True`.
3. **Cronjob nền tuân thủ Hard-Block**:
   - Mọi watchdog / scheduler (`post_noon_chain_watchdog`, `feed_session_watchdog`, reg/2fa) quét thấy máy có lock `user_authorized=True` hoặc `status in ("active", "running", "queued")` **BẮT BUỘC PHẢI SKIP**, không được phép đưa máy vào danh sách khởi chạy.
4. **Release an toàn trong finally**:
   - Khi task hoàn tất (dù PASS hay FAIL), bắt buộc gọi `lease.finish(succeeded=...)` để giải phóng máy về trạng thái rảnh.

---

## 2. BẪY CHẠM VÀO BACKDROP LÀM ĐÓNG MENU AVATAR TIKTOK (BACKDROP TAP TRAP)

### Triệu chứng:
Log báo lỗi `[AVATAR_UPLOAD_MENU_MISSING] ENSURE_AVATAR: Không tìm thấy Tải ảnh lên` mặc dù trước đó đã tap mở avatar thành công.

### Cơ chế gây lỗi:
1. **Layout UI TikTok mới (Profile)**:
   - Avatar Circle không còn nằm ở giữa `(540, 336)` hay `(540, 400)` mà thu nhỏ và dồn sang góc trên bên phải (`[708,228][1080,564]`, tâm `894, 396`), có id `bni`, `bmh` hoặc content-desc `"Ảnh hồ sơ"`. Phía bên trái nhường chỗ cho tên nick và nút *"Thêm tiểu sử"* (`[36,633][887,717]`).
2. **Bẫy Backdrop Tap**:
   - Khi tap vào Avatar Circle, TikTok **đã mở thành công Bottom Sheet** (chứa *"Tải ảnh lên"*, *"Chụp ảnh"*, *"Xem ảnh hồ sơ"*).
   - Code cũ không kiểm tra xem menu đã mở trên `current_xml` chưa, mà lại chạy tiếp logic tap fallback vào tọa độ avatar `(894, 396)`.
   - Khi Bottom Sheet đang mở bên dưới, tọa độ `(894, 396)` nằm ở **vùng tối mờ bên ngoài (Backdrop)** -> Android hiểu là thao tác chạm hủy và **lập tức đóng Bottom Sheet lại**!
   - Sau đó script tap tiếp tọa độ mù `(540, 580)` (chạm trúng nút thống kê *"Thích"* của Profile) và tìm chữ *"Tải ảnh lên"* trên màn hình đã bị đóng -> Thất bại.

### Giải pháp cốt lõi (Check-First Pattern):
- **Inspect `current_xml` trước khi tap**:
  ```python
  # Kiểm tra trước: Nếu bottom sheet hoặc photo picker ĐÃ MỞ trên current_xml thì tap ngay
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
- **Tuyệt đối không tap lại vào tọa độ Avatar hoặc Backdrop khi menu đang mở.**
- **Bỏ hoàn toàn tap mù vào `(540, 580)`** để tránh click nhầm vào các nút chỉ số (Follow/Follower/Thích) trên trang cá nhân.
