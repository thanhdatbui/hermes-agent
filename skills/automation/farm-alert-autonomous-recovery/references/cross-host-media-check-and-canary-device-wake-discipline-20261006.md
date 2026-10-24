# Cross-Host Media Check & Canary Device Wake Discipline (2026-10-06)

## 1. Báo Động Giả "Hết Video" (41 Máy Admin 201–280) Do Kiểm Tra Chéo Host
- **Kiến trúc Farm:** Kibe làm controller điều phối chính (quản lý máy 1–80), Admin-PC (`admin-farm`, 192.168.110.119) quản lý máy 201–280. Kho video render của Admin nằm tại `D:\TIKTOK-videonuoinick-admin` trên ổ đĩa máy Admin-PC (>27.000 clip).
- **Lỗi gốc rễ:** Script `_run_upload_hook()` trong `multi_machine_feed_session.py` chạy trên CPU của máy Kibe nhưng lại gọi `Path(r"D:\TIKTOK-videonuoinick-admin").is_file()` cục bộ trên ổ cứng Kibe. Do ổ D của Kibe không có thư mục này, code fail-closed trả về `video_not_rendered` và watchdog bắn alert giả `Hết video/Cần cào` cho 41 máy.
- **Quy tắc bất biến:** TUYỆT ĐỐI KHÔNG chia sẻ thư mục SMB, mount ổ mạng hay copy file video giữa 2 máy.
- **Giải pháp chuẩn:**
  - Đối với máy Admin (`machine >= 200`): Bỏ qua kiểm tra `is_file()` cục bộ trên Kibe. Bắn lệnh dispatch qua SSH sang Admin:
    ```bash
    ssh admin-farm "powershell -Command \"cd D:/Taadaa/Tiktok-video; & 'D:/Taadaa/python-envs/automation/Scripts/python.exe' -m scripts.tiktok_workflow --config D:/Taadaa/Tiktok-video/config-admin.yaml --workflow-workbook D:/OneDrive/TaadaaData/admin/Tik<slot>.xlsx --single-device <serial> --video-number <N> --video-source-root D:/TIKTOK-videonuoinick-admin --allow-device-reboot-recovery --no-dry-run\""
    ```
  - Không truyền `ADB_SERVER_SOCKET` của Kibe sang tiến trình Admin.
  - Máy Kibe (1–80) giữ nguyên nhánh chạy local.

## 2. Kỷ Luật Canary: Chống Viện Cớ Màn Hình Tắt / Ngủ (Device Sleep Trap)
- **Hành vi sai lầm (Paralysis):** Coordinator từ chối chạy Canary khi User yêu cầu với lý do: *"Màn hình: OFF (Sleep/Dozing)... nên chưa thể chạy canary... Tao không dùng ADB input tap/keyevent bấm mò"*.
- **Phân định rạch ròi:**
  - **CẤM BẤM TAY ADB:** Là cấm dùng `input tap / keyevent` để bấm mò qua màn hình lỗi/popup thay cho việc viết code xử lý tự động trong runner.
  - **ĐÁNH THỨC MÁY HỢP LỆ:** Điện thoại ở trạng thái `Sleep/Dozing` là trạng thái nhàn rỗi bình thường. Các runner automation chuẩn luôn có bước đánh thức thiết bị tự động (`svc power wakeup`, `input keyevent KEYCODE_WAKEUP` tại `[ANDROID_STARTUP] wake_screen: success`).
  - **Quy tắc:** CẤM TUYỆT ĐỐI viện cớ thiết bị đang sleep/dozing để từ chối chạy canary hoặc đùn đẩy trách nhiệm cho User. Khi nhận lệnh chạy canary, thiết bị rảnh thì kích hoạt đánh thức và chạy ngay.

## 3. Khai Thác Artifacts & Execution Log Sau Khi Canary Hoàn Tất
- **Hành vi sai lầm:** Runner upload chạy xong tự động dọn dẹp và đưa máy về Launcher. Coordinator chỉ chụp màn hình sau khi teardown rồi báo *"chưa có ảnh Profile"*, không kiểm tra log/report có sẵn.
- **Quy chuẩn nghiệm thu Canary:**
  1. **Trích xuất Run Directory:** Mọi run upload đều sinh thư mục run trên máy thực thi (ví dụ: `D:\CodexRuntime\tiktok-video\runs\run_<serial>_<timestamp>\`).
  2. **Đọc `execution.log` & `report.json`:**
     - Kiểm tra `State: VERIFY_POST`, `Profile video tiles: N (baseline=N-1)`, `Workflow completed successfully`.
     - Kiểm tra `report.json` có `status = "SUCCESS"`, `post_verified = true`, `post_submission_state = "ACCEPTED"`.
  3. **Lấy ảnh kiểm chứng Verify Post:** Runner đã lưu các ảnh chụp trước khi teardown ngay trong run dir (`post-published-surface.png`, `profile-grid-verify_post-*.png`). Dùng `scp` kéo về để gửi `MEDIA:<path_anh>` cho User.
  4. **Đối soát số liệu:** Cập nhật số `Video Đã Đăng` trong workbook tương ứng (`Tik<N>.xlsx` và `taikhoan_run_safe.xlsx`) từ baseline lên video vừa đăng.

## 4. Bẫy Dual-Namespace Mock Trong Pytest (Dual-Import Seam)
- Khi code production hỗ trợ import linh hoạt theo 2 đường dẫn (ví dụ `python_runner.flows.upload_preflight` vs `flows.upload_preflight`), việc `patch("flows.upload_preflight...")` trong unit test sẽ bị trượt nếu module caller đã nạp từ `python_runner.flows...`.
- **Khắc phục:** Sử dụng dynamic dispatch qua `sys.modules`:
  ```python
  cooldown_fn = getattr(
      sys.modules.get("flows.upload_preflight") or sys.modules.get("python_runner.flows.upload_preflight"),
      "check_upload_cooldown_eligibility",
      check_upload_cooldown_eligibility
  )
  ```
  Cách này đảm bảo dù runner hay test nạp module dưới namespace nào, hàm mock của unit test vẫn bắt đúng mục tiêu.
