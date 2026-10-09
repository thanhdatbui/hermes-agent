# Session Teardown and Unit Testing Guidelines

## 1. Session Teardown Home Contract (`_force_stop_tiktok_and_home`)

Khi kết thúc một session (trong `multi_machine_feed_session.py` hoặc các session flow tương tự), dù kết quả là `success`, `failed` hay gặp exception ngoài ý muốn:
- **Nguyên tắc:** Thiết bị sau khi nhả lease tuyệt đối không được để treo ở màn hình TikTok (feed video, profile, gallery, comment popup, v.v.).
- **Vị trí thực thi:** Luôn đặt trong khối `finally:` teardown trước khi release lock/lease.
- **Quy trình đóng:**
  1. **Force-stop TikTok:** Gửi lệnh `am force-stop <package>` (mặc định `com.ss.android.ugc.trill`, hoặc lấy từ `child_ctx.config["tiktok_package"]`).
  2. **Về HOME screen:** Gửi lệnh `input keyevent 3` để đưa thiết bị về màn hình chính của Android.
- **Cơ chế gọi:**
  - Ưu tiên: Gọi qua `child_ctx.adb.shell(...)` nếu đối tượng ADB client tồn tại.
  - Fallback: Nếu không có `child_ctx.adb`, fallback gọi trực tiếp qua `subprocess.run` với serial của máy (`account.serial`) và adb executable path (mặc định Xiaowei tools). Bọc trong khối try-except để không chặn flow teardown.

## 2. Quy chuẩn chạy Pytest trong `tiktok-luot nuoi acc`

Khi viết và chạy focused test (unit test) trong thư mục `D:/Taadaa/tiktok-luot nuoi acc/python_runner`:
- Repo cấu trúc các module nghiệp vụ nằm trực tiếp dưới `python_runner/flows/`, `python_runner/core/`, v.v.
- Khi gọi `pytest`, nếu không chỉ định `PYTHONPATH`, python sẽ không tìm thấy `flows` và báo lỗi `ModuleNotFoundError: No module named 'flows'`.
- **Lệnh chạy chuẩn:**
  ```bash
  PYTHONPATH="D:/Taadaa/tiktok-luot nuoi acc/python_runner" pytest "D:/Taadaa/tiktok-luot nuoi acc/python_runner/tests/test_session_teardown_home.py" -q
  ```
