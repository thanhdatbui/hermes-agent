# Kỷ Luật Canh Nhả Lock, Cấm Tự Tiện Pause Cron & Safe-Point Return Cho Add Account (2026-10-21)

## 1. Bẫy Tự Tiện Pause Cron / Stop Watchdog (User Correction 2026-10-21)
- **Hiện tượng**:
  Khi Coordinator khởi chạy `tiktok_login_v1.py` để nạp bù nick thiếu, script gặp device lock đang active từ tiến trình khác:
  ```text
  [device-lock] NEEDS_USER_DECISION: device lock active: path=C:\Users\Kibe\.codex\device-locks\machine_24.lock.json pid=... project=tiktok-rename
  ```
  Coordinator tự tiện gọi `cronjob pause` đối với `tiktok-rolling-rename-watchdog` để tránh bị chiếm lock.
- **Quy tắc & Kỷ luật nghiêm cấm**:
  - **CẤM TUYỆT ĐỐI** Coordinator tự ý pause, stop, disable các cronjob hay watchdog đang chạy trên hệ thống của User.
  - User chốt kỷ luật: *"Mày canh nó làm xong thì mày vào làm. Tự tiện vc."*
  - **Quy trình chuẩn**:
    1. Kiểm tra tiến trình đang giữ lock bằng `tasklist /FI "PID eq <PID>"`.
    2. Chờ tiến trình đó kết thúc tự nhiên (ví dụ `tiktok-rename` sẽ tự thoát sau khi kiểm tra không thấy nick mục tiêu).
    3. Nếu PID đã chết nhưng lock file vẫn còn lưu trên đĩa (dead-owner lock do tiến trình crash hoặc exit bất ngờ), **BẮT BUỘC** chạy script dọn lock chuẩn của farm:
       ```bash
       python "D:/Taadaa/tiktok-luot nuoi acc/scripts/reap-dead-owner-locks.py"
       ```
    4. Xác nhận file lock `machine_<N>.lock.json` đã biến mất rồi mới tiếp tục chạy lệnh nạp bù.

---

## 2. Safe-Point Tap & Return Ngay Lập Tức Trong `tap_add_account`
- **Hiện tượng**:
  Trong `tap_add_account` (`social_reg_v1.py`), sau khi tap điểm an toàn Safe-Point (`540, 1832`), code cũ có đoạn kiểm tra:
  ```python
  tap(device_id, safe_x, safe_y, wait=D_MEDIUM)
  time.sleep(1.5)
  chk_xml = get_ui_xml(device_id)
  if _tiktok_login_modal_present(chk_xml) or has_text_loose(chk_xml, ...):
      return
  log("   [add-account] modal chưa mở sau tap, thử lại...")
  continue
  ```
- **Hậu quả**:
  1. Trên máy thật Samsung S7, hiệu ứng mở modal login mất 1.5s - 2.5s. Kiểm tra ngay lập tức khiến `chk_xml` vẫn đọc màn cũ, dẫn đến việc script hiểu nhầm là tap chưa ăn và tiếp tục lặp lại 3 lần rồi văng lỗi `RuntimeError: Không tìm thấy: Thêm tài khoản`.
  2. Gãy unit test `test_tap_add_account_safe_point.py` vì mock trả về XML cũ, khiến test kỳ vọng 1 tap nhưng thực tế bị tap 3 lần rồi crash.
- **Giải pháp chuẩn**:
  - Áp dụng công thức Safe-Point:
    ```python
    safe_x = (x1 + x2) // 2
    safe_y = min(y1 + max(1, (y2 - y1) // 3), 1835)
    tap(device_id, safe_x, safe_y, wait=D_MEDIUM)
    return
    ```
  - Bấm nút xong là `return` ngay lập tức để luồng cha chuyển sang bước tiếp theo (`tap_add_another` hoặc chờ modal xuất hiện).
  - Đảm bảo unit test `test_tap_add_account_safe_point.py` đạt **2/2 PASSED**.
