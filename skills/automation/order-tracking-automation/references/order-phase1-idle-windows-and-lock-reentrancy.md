# Order Lifecycle Fixed Idle Windows & Device Lock Re-Entrancy

## 1. Cố Định Khung Giờ Máy Rảnh (Eliminating Dynamic Cooldown Drift)
- **Sai lầm:** Sử dụng `time.time() - last_run_timestamp >= 5.5h` (dynamic cooldown).
  * Hậu quả: Khi một lần chạy bị dời (ví dụ chạy lúc 22:47), mốc 5.5h tiếp theo rơi vào 04:17. Nếu cron chỉ chạy từ 06:00 đến 22:00, mốc chạy sẽ bị nhảy cóc sang tận 06:00 sáng hoặc bỏ qua hoàn toàn các khung nghỉ trưa/chiều giữa các ca nuôi feed.
- **Quy chuẩn bất biến (Fixed Idle Windows):**
  * Phase 1 (bóc mã trên app S7) **CHỈ ĐƯỢC CHẠY** vào 4 khung giờ máy rảnh chuẩn của Farm:
    1. `04:30 – 05:00` (Sau dọn cache cuối ngày, trước Ca 1).
    2. `10:30 – 11:00` (Sau Ca 1, trước Ca 2).
    3. `16:30 – 17:00` (Sau chuỗi ca trưa, trước Ca 3).
    4. `22:30 – 23:00` (Sau Ca 3, trước Ca 4).
  * **Idempotency theo Slot:** Ghi nhận `last_run_slot = f"{YYYYMMDD}_{HH}"` vào state file. Trong mỗi khung rảnh 30 phút (khi cron watchdog kích hoạt mỗi 15 phút), Phase 1 chỉ chạy đúng 1 lần duy nhất, sau đó nhả máy ngay cho các ca sau.

---

## 2. Bẫy Tự Khóa Chính Mình (Device Lock Re-Entrancy Deadlock)
- **Triệu chứng:** Worker bóc mã bị treo timeout (60s – 180s) mặc dù máy hoàn toàn rảnh, không có tiến trình nào khác giữ máy.
- **Nguyên nhân gốc rễ:**
  * Runner ngoài (`order_lifecycle.py`) đã bọc `with operator_device_lock(serial=serial, timeout=10.0):`.
  * Khi gọi vào `tiktok_app_order_sync.py`, các hàm con (`_adb_run`, `_adb_screencap`) lại tiếp tục gọi `with operator_device_lock(serial=serial, timeout=20.0):`.
  * Do cơ chế `operator_device_lock` kiểm tra file `serial_<serial>.lock.json` và chặn trùng lặp, tiến trình con tự chờ chính mình nhả khóa cho đến khi timeout.
- **Giải pháp:**
  * Thêm hàm kiểm tra quyền sở hữu hiện tại (hỗ trợ cả trường hợp chạy lồng qua `with_device_lock.py` CLI wrapper):
    ```python
    def _is_self_locked(serial: str) -> bool:
        lock_path = Path.home() / ".codex" / "device-locks" / f"serial_{serial}.lock.json"
        if not lock_path.is_file():
            return False
        try:
            data = json.loads(lock_path.read_text(encoding="utf-8"))
            lock_pid = data.get("pid")
            return lock_pid == os.getpid() or (hasattr(os, "getppid") and lock_pid == os.getppid())
        except Exception:
            return False
    ```
  * Trong các hàm gọi ADB/screencap: Nếu `_is_self_locked(serial)` là `True` thì thực thi trực tiếp qua `nullcontext()`, không bọc lại `operator_device_lock`.

---

## 3. Quy Trình Điều Hướng Chuẩn Khi Mở TikTok App (Feed -> Profile -> Order List)
- **Vấn đề:** Khi mở app TikTok, màn hình luôn ở tab Trang chủ / Feed video (`Trang chủ / Cửa hàng / Hộp thư / Hồ sơ`). Nhãn OCR tiếng Việt thường bị biến dạng (`Hö sd`, `Ddn häng cÖa ban`).
- **3 Checkpoint Điều hướng & 4 Bẫy Chết Người:**
  1. **Bẫy Phòng LIVE (Ẩn Bottom Bar):** Khi mở TikTok rơi vào một phòng LIVE (`Dang LIVE`, `Tin nhan`, video stream), thanh điều hướng đáy biến mất hoàn toàn. Tapping đáy màn hình vô tác dụng. BẮT BUỘC phát hiện `Dang LIVE` / `nhan dd xem live` và gửi `input keyevent 4` (phím BACK) hoặc tap nút `X` để thoát khỏi phòng LIVE về Feed trước.
  2. **Checkpoint 1 (Về Hồ sơ & Bẫy Chấm Đỏ):** Nhận diện `Hö sd` hoặc tab góc dưới phải (`x ≈ 972, y ≈ 1881`). **Lưu ý:** Khi có chấm đỏ thông báo mới, WinRT OCR thường đọc thành `•1-16 sd` hoặc `-1-16 sd` làm hỏng match text; BẮT BUỘC fallback tap tọa độ cứng `(int(width * 0.9), int(height * 0.98))` để chuyển sang Profile.
  3. **Checkpoint 2 (Chuyển Account nếu cần & Bẫy Keyevent 4):** Tap vào tên nick ở góc trên bên trái (`y ≈ 320`), chọn đúng nick đặt hàng trên bottom sheet.
     * ⚠️ **BẪY TỬ HUYỆT:** Sau khi tap vào tên nick trên Switcher, TikTok tự động chuyển nick và đóng sheet. **TUYỆT ĐỐI CẤM GỬI LỆNH `keyevent 4`** sau khi tap, vì lệnh BACK này sẽ làm văng app ra Launcher hoặc đẩy ngược về Feed!
     * Sau khi chọn nick, TikTok reload về Feed, lúc này chỉ cần tap lại tab Hồ sơ `(972, 1881)` là vào thẳng Profile nick đích.
  4. **Checkpoint 3 (Vào Đơn Hàng & Bẫy Hub Tĩnh):** Trên trang Profile, tap `Ddn häng cia bqn` (`y ≈ 850`).
     * Màn hình mở ra là Hub Đơn Hàng (`m9_hub.png`) chứa banner và voucher, **CHƯA PHẢI** danh sách đơn.
     * BẮT BUỘC phải tap nút **`Xem tất cả >`** tại tọa độ `(923, 263)` (vùng `y < 400`, x: 816-1030) để vào danh sách đơn thực tế (`m8_order_list.png`), sau đó tap vào kiện hàng (`Kien hang cua ban da duoc giao`) để lấy mã vận đơn.
