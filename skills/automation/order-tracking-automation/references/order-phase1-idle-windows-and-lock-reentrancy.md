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
  * Thêm hàm kiểm tra quyền sở hữu hiện tại:
    ```python
    def _is_self_locked(serial: str) -> bool:
        lock_path = Path.home() / ".codex" / "device-locks" / f"serial_{serial}.lock.json"
        if not lock_path.is_file():
            return False
        try:
            data = json.loads(lock_path.read_text(encoding="utf-8"))
            return data.get("pid") == os.getpid()
        except Exception:
            return False
    ```
  * Trong các hàm gọi ADB/screencap: Nếu `_is_self_locked(serial)` là `True` thì thực thi trực tiếp qua `nullcontext()`, không bọc lại `operator_device_lock`.

---

## 3. Quy Trình Điều Hướng Chuẩn Khi Mở TikTok App (Feed -> Profile -> Order List)
- **Vấn đề:** Khi mở app TikTok, màn hình luôn ở tab Trang chủ / Feed video (`Trang chủ / Cửa hàng / Hộp thư / Hồ sơ`). Nhãn OCR tiếng Việt thường bị biến dạng (`Hö sd`, `Ddn häng cÖa ban`).
- **3 Checkpoint Điều hướng:**
  1. **Checkpoint 1 (Về Hồ sơ):** Nhận diện `Hö sd` hoặc tab góc dưới phải (`x ≈ 972, y ≈ 1881`), tap để vào trang cá nhân.
  2. **Checkpoint 2 (Chuyển Account nếu cần):** Tap vào tên nick ở góc trên bên trái (`y ≈ 320`), chọn đúng nick đặt hàng trên bottom sheet. Sau khi chọn, tap lại tab Hồ sơ.
  3. **Checkpoint 3 (Vào đơn hàng):** Trên trang Hồ sơ, tap vào nút `Ddn häng cÖa ban` (`y ≈ 850`), sau đó tap `Xem tất cả >` (`x ≈ 900, y ≈ 260`) để mở danh sách toàn bộ đơn và tap vào kiện hàng tương ứng để lấy mã vận đơn.
