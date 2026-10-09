# Quy tắc Lướt Feed Ngẫu Nhiên & Dọn Dẹp Close App Về Home (Tiktok_Reg)

Áp dụng cho `D:/Taadaa/Tiktok_Reg/social_reg_v1.py` và các script registration trên hệ thống Taadaa Phone Farm.

---

## 1. Random số video lướt feed (`run_warmup_feed`)
- **Mục tiêu:** Tạo telemetry và dwell time tự nhiên cho nick mới đăng ký thành công, tránh footprint hành vi rập khuôn (cùng số video hoặc cùng thời gian) giữa các máy trong dàn farm.
- **Hàm `run_warmup_feed(device_id, stt=None, account_handle=None, num_videos=None)`:**
  - `num_videos`: Nếu là `None` hoặc `<= 0`, tự động gán ngẫu nhiên trong khoảng `random.randint(4, 8)`.
  - Mỗi video được xem ngẫu nhiên `random.uniform(5.0, 9.0)` giây.
  - Tuyệt đối không like, comment hay follow.
  - Tọa độ vuốt được jitter ngẫu nhiên để chống bot detection.
- **Tùy chọn CLI `--feed-swipes`:**
  - Trong `ensure_profile_completed_and_track(...)`: Nếu người dùng không chỉ định cờ `--feed-swipes`, mặc định gán `feed_swipes = random.randint(4, 8)`.

---

## 2. Luôn đóng app về Home khi fail / kết thúc script (`_post_reg_cleanup`)
- **Quy tắc cốt lõi:** Tuyệt đối KHÔNG được để ứng dụng TikTok treo lơ lửng trên màn hình máy S7 khi script kết thúc hoặc gặp lỗi giữa chừng (fail, timeout, pending, exception).
- **Hàm `_post_reg_cleanup(device_id, stt=None)`:**
  ```python
  shell(device_id, "am", "force-stop", APP_PACKAGE)
  keyevent(device_id, 3, wait=0.5)  # KEYCODE_HOME
  ```
- **Các vị trí bắt buộc thực thi:**
  1. `ensure_profile_completed_and_track`: Bọc phần gọi `run_warmup_feed` trong khối `try ... finally:` để dù lướt feed xong hay lỗi thì `_post_reg_cleanup(device_id, stt=stt)` luôn luôn được gọi trước khi return.
  2. `register(device_id, acc, ...)`: Trong khối `finally: if not reg_success:`, bắt buộc gọi `_post_reg_cleanup(device_id, stt=stt)` để bất kỳ nhánh dừng hay exception nào cũng đảm bảo đóng app về Home.
  3. `_do_register`: Trong nhánh `else:` khi `wait_login_success` trả về `False` (pending/thất bại), sau khi lưu ảnh hiện trường và gửi Telegram alert phải lập tức gọi `_post_reg_cleanup(device_id, stt=stt)`.
  4. Nhánh `--resume` trong `__main__`: Trong khối `finally: if not resume_success:`, bắt buộc gọi `_post_reg_cleanup(device, stt=stt)`.
