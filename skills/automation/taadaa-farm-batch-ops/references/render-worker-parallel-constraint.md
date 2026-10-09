# Quy dinh Bat buoc: Gioi han Render Worker (Parallel = 1) Toan Farm

## 1. Nguyen nhan & Tac dong Tai nguyen
- **FFmpeg CPU Usage**: Moi tien trinh ffmpeg render video TikTok thuong chiem 80% - 95% CPU host.
- **Hau qua khi chay parallel >= 2**:
  - Hai hoac nhieu worker ffmpeg chay dong thoi day CPU len 100% lien tuc.
  - May host (Admin hoac Kibe) bi giat lag, treo Task Manager, rot ket noi ADB transport va gay crash cac chuong trinh khac.
  - Tung dan den su co phai tree-kill khan cap toan bo chuoi render.

## 2. Invariant Quy chuan: Luon dat parallel = 1
Toan bo launcher, script va supervisor lien quan den Render video tren ca 2 cum Kibe va Admin BAT BUOC cau hinh dung 1 worker:

1. **Launcher Admin (run_admin_render_chain.bat)**:
   - Tham so bat buoc: `--parallel 1` (CAM dat `--parallel 2`).

2. **PowerShell Launchers (run_tikX_random_render.ps1, run_kibe_slot7_slot8_render.ps1)**:
   - Tham so mac dinh: `-Parallel 1`.
   - Cam tu y tang len >= 2.

3. **Supervisor (scripts/admin_render_chain.py)**:
   - Tham so goi PowerShell trong `run_step()` bat buoc truyen `"-Parallel", "1"`.

4. **Engine Core (scripts/random_batch_render.py)**:
   - Khi `parallel == 1`: Engine chay tuan tu tung video (`render_one`), dam bao tren toan may chi co DUY NHAT 1 tien trinh ffmpeg hoat dong tai mot thoi diem.
