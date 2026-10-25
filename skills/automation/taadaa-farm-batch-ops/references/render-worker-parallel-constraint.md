# Quy dinh Bat buoc: Gioi han Render Worker (Parallel = 1) Toan Farm

## 1. Nguyen nhan & Tac dong Tai nguyen
- **FFmpeg CPU Usage**: Moi tien trinh ffmpeg render video TikTok thuong chiem 80% - 95% CPU host.
- **Hau qua khi chay parallel >= 2**:
  - Hai hoac nhieu worker ffmpeg chay dong thoi day CPU len 100% lien tuc.
  - May host (Admin hoac Kibe) bi giat lag, treo Task Manager, rot ket noi ADB transport va gay crash cac chuong trinh khac.
  - Tung dan den su co phai tree-kill khan cap toan bo chuoi render.

## 2. Invariant Quy chuẩn: Mặc định luôn đặt parallel = 1 (Trừ khi User chỉ thị rõ ràng)
Toàn bộ launcher, script và supervisor liên quan đến Render video trên cả 2 cụm Kibe và Admin MẶC ĐỊNH BẮT BUỘC cấu hình đúng 1 worker:

1. **Launcher Admin (run_admin_render_chain.bat)**:
   - Tham số mặc định: `--parallel 1` (CẤM tự ý đặt `--parallel 2` khi không có lệnh).

2. **PowerShell Launchers (run_tikX_random_render.ps1, run_kibe_slot7_slot8_render.ps1)**:
   - Tham số mặc định: `-Parallel 1`.
   - Cấm tự ý tăng lên >= 2 khi không có chỉ đạo của User.

3. **Supervisor (scripts/admin_render_chain.py)**:
   - Tham số gọi PowerShell trong `run_step()` bắt buộc truyền `"-Parallel", "1"`.

4. **Engine Core (scripts/random_batch_render.py)**:
   - Khi `parallel == 1`: Engine chạy tuần tự từng video (`render_one`), đảm bảo trên toàn máy chỉ có DUY NHẤT 1 tiến trình ffmpeg hoạt động tại một thời điểm.

## 3. Quy Trình Điều Chỉnh Concurrency (Parallel 1 <-> 2) Khi User Yêu Cầu
Khi User ra lệnh rõ ràng (ví dụ: *"Tăng worker lên 2 đi, render ấy. Khi nào giảm t nhắn"*):
- **BẮT BUỘC THI HÀNH NGAY:** Tuyệt đối không cãi lệnh hay viện cớ an toàn để từ chối khi User đã chủ động chỉ thị.
- **Tooling điều khiển chuẩn:** Dùng script `D:\Taadaa\tools\set_admin_render_parallel.py --parallel <1|2>` để đổi config và restart render worker sạch sẽ.
- **Quy chuẩn Runtime & Python Venv trên Admin:**
  - `run_admin_render_worker.py` BẮT BUỘC chạy bằng venv: `D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe` (hoặc `pythonw.exe`).
  - CẤM dùng Python hệ thống `C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe` vì thiếu thư viện `openpyxl` dẫn đến crash ngầm `ModuleNotFoundError: No module named 'openpyxl'`.
- **Cơ chế Kill & Spawn Detached:**
  - Kill sạch các tiến trình `ffmpeg` và `run_admin_render_worker.py` / `random_batch_render.py` cũ.
  - Spawn worker mới ở chế độ detached không cướp focus: `flags = 0x08000000 | 0x00000008 | 0x00000200` (`CREATE_NO_WINDOW | DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`).
- **Game Guard In-Flight Vẫn Hoạt Động 100%:**
  - Dù chạy parallel 2, Game Guard trong `run_admin_render_worker.py` vẫn quét mỗi 2 giây. Khi phát hiện War3 hoặc TFT (`league of legends.exe`, `tftclient.exe`), lập tức tree-kill cả 2 tiến trình ffmpeg trong <= 2s để nhường 100% tài nguyên cho game.
- **Khi User yêu cầu hạ lại về 1 worker:** Chạy `python D:\Taadaa\tools\set_admin_render_parallel.py --parallel 1` để đưa về trạng thái mặc định an toàn.

