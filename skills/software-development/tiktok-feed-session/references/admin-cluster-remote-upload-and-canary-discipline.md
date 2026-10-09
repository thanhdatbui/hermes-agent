# Admin Cluster Remote Upload Hook & Canary Execution Discipline

## 1. Bản Chất Lỗi False-Positive "Hết Video / Cần Cào" Trên Cụm Admin (Remote PC)
- **Hiện tượng:**
  Watchdog `feed_session_watchdog.py` báo hàng loạt máy cụm Admin (M201-M280) bị `Hết video/Cần cào (<N>)` sau các phiên Feed + Upload (Phiên 2). Tuy nhiên, khi SSH vào host `admin-farm` kiểm tra thực tế, 100% video mục tiêu đều tồn tại đầy đủ trong `D:\TIKTOK-videonuoinick-admin\<folder>\<video_id>.mp4`.
- **Root Cause (Local Path Checking Trap):**
  - Hệ thống Taadaa Phone Farm sử dụng mô hình **1-Controller** (máy Kibe điều phối tập trung).
  - Cronjob `tiktok_runner.py` chạy trên CPU máy Kibe. Khi tiến trình con xử lý upload hook (`_run_upload_hook()` trong `python_runner/flows/multi_machine_feed_session.py`), Gate 5 kiểm tra sự tồn tại của file video bằng `Path.is_file()`:
    ```python
    media_root = Path(ctx.config.get("media_source_root") or host_paths["media_source_root"])
    video_file = media_root / folder_video / f"{next_video}.mp4"
    if not video_file.is_file():
        return {"status": "skipped", "reason": "video_not_rendered"}
    ```
  - Với máy Admin (`machine >= 200`), `media_source_root` được cấu hình là `D:\TIKTOK-videonuoinick-admin`. Nhưng câu lệnh `video_file.is_file()` lại chạy trên filesystem local của **Kibe** (nơi thư mục này không tồn tại) $\rightarrow$ luôn trả về `False` $\rightarrow$ gán nhãn `video_not_rendered` gây báo động giả toàn cụm.
  - Sau đó, nếu tiếp tục chạy subprocess local trên Kibe thì lệnh cũng fail vì Kibe không có kho video của Admin và bị nhầm ADB daemon.

## 2. Kỷ Luật Kiến Trúc: CẤM Đề Xuất Share Thư Mục / SMB Giữa Các PC Farm
- **Bẫy Over-Engineering:** Khi phát hiện Kibe không thấy file của Admin, Coordinator tuyệt đối **CẤM đề xuất mount SMB, share folder Windows mạng LAN, hoặc copy file qua lại**.
  - Việc mount ổ mạng giữa các máy farm làm tăng rủi ro split-brain, tắc nghẽn I/O khi nhiều worker cùng đọc qua mạng LAN, và làm phức tạp hạ tầng không cần thiết.
- **Giải Pháp Chuẩn Hóa (Remote Host Execution via SSH):**
  - Phân nhánh rõ ràng theo target machine:
    * Máy Kibe (`machine 1-80`): Kiểm tra và chạy subprocess local trên Kibe như bình thường.
    * Máy Admin (`machine >= 200` hoặc `host_id == 'admin'`):
      1. Bỏ qua kiểm tra `Path.is_file()` local trên Kibe; không gán `video_not_rendered` dựa trên ổ đĩa Kibe.
      2. Chuyển đổi command upload sang chạy remote qua SSH alias `admin-farm`:
         ```python
         remote_command = (
             "cd /d D:/Taadaa/Tiktok-video && "
             "D:/Taadaa/python-envs/automation/Scripts/python.exe -m scripts.tiktok_workflow "
             "--config D:/Taadaa/Tiktok-video/config-admin.yaml "
             f"--workflow-workbook D:/OneDrive/TaadaaData/admin/{workbook_path.name} "
             f"--single-device {account.serial} --video-number {next_video} "
             "--video-source-root D:/TIKTOK-videonuoinick-admin "
             "--allow-device-reboot-recovery --no-dry-run"
         )
         command = ["ssh", "admin-farm", remote_command]
         ```
      3. Tuyệt đối không truyền biến `ADB_SERVER_SOCKET` của Kibe sang tiến trình Admin vì host Admin tự kết nối ADB daemon local `localhost:5037` của chính nó.
      4. Downstream report verification giữ nguyên cơ chế fail-closed (yêu cầu stdout có marker thành công hoặc report JSON hợp lệ).

## 3. Kỷ Luật Thực Thi Canary Trên Thiết Bị Thật (Anti-Paralysis Invariant)
- **Hiện tượng thoái thác:** Khi User trực tiếp yêu cầu "chạy canary", Coordinator inspect thấy thiết bị báo `Màn hình: OFF (Sleep/Dozing)` liền kết luận *"máy đang ngủ nên chưa thể chạy canary an toàn"* và dừng lại không chạy.
- **Quy tắc cưỡng chế:**
  - Điện thoại trong phone farm rơi vào trạng thái Sleep/Dozing sau khi hoàn tất phiên nuôi acc là trạng thái hoàn toàn bình thường để tiết kiệm pin và làm mát màn hình.
  - **CẤM TUYỆT ĐỐI** lấy lý do máy đang sleep/màn hình tắt để từ chối chạy canary khi User đã ra lệnh.
  - **Quy trình chuẩn bị Canary 3 bước trước khi launch:**
    1. **Đánh thức màn hình (Safe Wakeup):** Chạy `adb -s <serial> shell input keyevent KEYCODE_WAKEUP` (hoặc `svc power stayon true`). Đối soát qua `adb shell dumpsys power` để xác nhận `mWakefulness=Awake` và `Display Power: state=ON`.
    2. **Chụp ảnh Checkpoint 1 (Pre-Action):** Chụp ảnh màn hình thật trước khi chạy (`screencap -p`). Xác nhận dung lượng ảnh `> 100KB` (chống ảnh đen 12KB) và gửi ngay cho User `MEDIA:<path_anh>`.
    3. **Khởi chạy Event-Driven:** Khởi chạy tiến trình upload canary bằng `terminal(background=True, notify_on_complete=True, timeout=...)`. Khi tiến trình hoàn tất, lấy ảnh Checkpoint 2 (Post-Action) nghiệm thu trên app thật trước khi kết luận.
