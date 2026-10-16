# Device-Lock Stall Prevention & Remote Admin Cluster Execution (2026-10-16)

## 1. Bệnh Lý Nằm Im Chờ Nhắc Khi Gặp Device Lock (Device-Lock Stall Trap)
- **User Frustration Signal**: *"Tại sao tao phải nhắc mày mới làm????"*
- **Triệu chứng**:
  - Khi Coordinator phát hiện thiết bị mục tiêu đang bị khóa bởi ca nuôi/lướt feed (`machine_<N>.lock.json` hoặc `multi-machine-feed-session`), Coordinator báo cáo lại cho User: *"Ngay khi ca nuôi chạy xong và giải phóng lock, hệ thống sẽ thực hiện..."* nhưng **KHÔNG dispatch bất kỳ tiến trình theo dõi hay cơ chế đánh thức nào**.
  - Coordinator nằm im thụ động trong trạng thái idle suốt 2-3 tiếng đồng hồ, cho đến khi User vào chất vấn mới bắt đầu kiểm tra lại.
- **Kỷ luật cưỡng chế (Proactive Lock Follow-up Invariant)**:
  - **CẤM TUYỆT ĐỐI** kết thúc turn bằng lời hứa *"sẽ làm khi lock nhả"* mà không có hành động gắn liền.
  - Khi gặp target bị `SKIPPED_LOCKED`:
    1. Kiểm tra PID và thời gian bắt đầu của lock (`psutil.pid_exists(pid)`). Các ca feed thông thường kéo dài 20–45 phút.
    2. BẮT BUỘC tạo một cơ chế theo dõi tự động:
       - Dùng `terminal(background=True, notify_on_complete=True)` chạy một probe/waiter đợi lock giải phóng rồi tự động kích hoạt task chính; HOẶC
       - Lập một one-shot cronjob (ví dụ `cronjob(action='create', schedule='every 20m', ...)` hoặc kiểm tra định kỳ) để tự động đánh thức session xử lý tiếp.
    3. Trả lời User phải nêu rõ: *"Đã thiết lập tiến trình nền tự động bám sát, ngay khi lock giải phóng sẽ tự động thi công và báo cáo, User không cần phải nhắc lại."*

---

## 2. Bẫy Routing Host Cụm Admin Remote (Admin Range >= 200)
- **Lỗi hiện trường**:
  `[DEVICE_OFFLINE] device is offline or ADB/USB disconnected for <serial>: adb.exe: device '<serial>' not found`
- **Nguyên nhân cốt lõi**:
  - Thiết bị máy trong dải `[200, 999]` (ví dụ Máy 201) cắm vật lý trực tiếp vào máy **Admin Farm (`192.168.110.119:5037`)**.
  - Launcher `run_tiktok_upload_avatar.ps1` hoặc `run_avatar_batch_3accs.py` khi chạy trực tiếp trên shell của máy local `Kibe` sẽ gọi binary `adb.exe` cục bộ (chỉ thấy các máy `[1, 80]`), không tìm thấy thiết bị của Admin và báo false `DEVICE_OFFLINE`.
- **Quy tắc điều phối bắt buộc**:
  - Đối với các máy $\ge 200$:
    - BẮT BUỘC thực thi batch launcher trên host Admin thông qua SSH:
      ```bash
      python D:/Taadaa/tools/admin_ssh.py "powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\\Taadaa\\Tiktok-video\\run_tiktok_upload_avatar.ps1 -Tik <N> -ForceAvatarMachineList <M> -MaxParallel 1"
      ```
    - HOẶC chạy Python runner trực tiếp trên host Admin:
      ```bash
      python D:/Taadaa/tools/admin_ssh.py "python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <N> --machine <M>"
      ```
  - CẤM chạy batch launcher cục bộ trên Kibe cho các máy thuộc range Admin trừ khi có ADB tunnel / port forwarding `-H 192.168.110.119 -P 5037`.
