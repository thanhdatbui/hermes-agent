---
name: taadaa-farm-batch-ops
description: "Re-run / resume farm batch jobs (TikTok upload, Tik3 render, reg, nuoi acc) using canonical commands."
version: 1.0.0
author: Hermes Agent
tags: [tiktok, farm, batch, render, upload, resume, kibe]
---

# Taadaa Farm Batch Operations

## 1. Nguyên Tắc Cốt Lõi
- **Tái sử dụng công cụ chuẩn:** Tuyệt đối không tự viết lệnh ad-hoc khi đã có script pipeline chính thống.
- **Tiến trình ngầm không mở Console:** Mọi lệnh batch kích hoạt qua cronjob hoặc background bắt buộc phải bọc ẩn cửa sổ theo `guard_cronjob_safety.py`.

## 2. Các Lệnh Canonical Batch
- **Render Video (TikN):**
  `python -m tik3_multi_batch --workbook <TikN.xlsx> --start-output <folder_đầu> --start-source <nguồn_đầu> --count <N> --min-videos 45 --parallel 1 --allow-existing-output --resume-complete --execute`
- **Upload Avatar (Lẻ <= 3 máy):**
  `python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <Tik> --machine <May>`
- **Đổi Biệt Danh Rolling:**
  `python D:/Taadaa/tools/tiktok_rename_rolling_watchdog.py`
- **Cào Tải Video Gốc Admin (40 Workers song song qua 69 Proxy MikroTik LAN):**
  `python C:/Users/Admin/run_admin_downloader_service.py` (launcher headless: `python C:/Users/Admin/launch_detached_admin_downloader.py`). Log: `D:/CodexRuntime/tiktok-video-machine2/download_admin_p10.log`.
- **Render Worker Chuẩn Mapping 8 Tik trên Admin (1 Worker tuần tự chống nghẽn GPU):**
  `python C:/Users/Admin/run_admin_render_worker.py` (launcher headless: `python C:/Users/Admin/launch_detached_admin_render.py`). Log: `C:/Users/Admin/admin_render_worker.log`.
- **Tra cứu máy N O(1) & Fastpath Batch Triage:**
  `python D:/Taadaa/tools/inspect_machine.py <N>` (tra cứu máy đơn lẻ). Khi nhận alert batch nhiều máy lỗi: BẮT BUỘC chạy `python D:/Taadaa/tools/inspect_machine.py` (không tham số) để dump snapshot attached toàn dàn <2s, đối soát nhanh thiết bị rớt USB / offline trước khi gọi inspect từng máy, chống timeout ADB daemon. Chi tiết xem [`references/dual-cluster-batch-triage-fastpath.md`](references/dual-cluster-batch-triage-fastpath.md).
- **Chẩn đoán Nhanh Admin Dừng Down / Dừng Render O(1):**
  Đọc `D:\OneDrive\TaadaaData\admin\last_render_stats.json` thay vì gọi SSH. Phân biệt: (1) Render dừng do đã vét hết nguồn $\ge 30$ clip (Tik6..Tik8 thiếu raw); (2) Downloader dừng do chạy hết pass và/hoặc bị ngắt bởi ca reboot 05:20/11:20/17:20 dừng ở Windows Lock Screen (do Task Scheduler kẹt `LogonType: Interactive` hoặc Startup VBS không kích hoạt khi chưa login console).
- **Quy Tắc Cô Lập Tác Vụ Thiết Bị vs Tác Vụ PC Media (INVARIANT: CẤM ĐỔ LỖI 2FA CHO DOWNLOAD):**
  Tác vụ thiết bị qua ADB/USB (2FA, Nuôi feed, Avatar, Rename, Reg) và tác vụ media trên PC (Cào video gốc qua 69 proxy MikroTik LAN, Render GPU/CPU) là **HOÀN TOÀN ĐỘC LẬP VÀ CHẠY SONG SONG**. CẤM TUYỆT ĐỐI liên đới, suy diễn xung đột hoặc đề xuất "chờ 2FA xong mới cào video". Khi downloader dừng, nguyên nhân luôn nằm ở ca reboot / Task Scheduler / proxy / nguồn candidate, KHÔNG BAO GIỜ do 2FA.

## 3. Cạm Bẫy Khởi Động Sau Reboot & Tải Video (Pitfalls)
- **Bẫy ghi Memory thay vì sửa Code khi User yêu cầu chỉnh tiêu chí Báo cáo Watchdog:** Khi người dùng chỉ thị thay đổi tiêu chí, bộ lọc hoặc ngưỡng cảnh báo của một bản tin watchdog (ví dụ: *"Các nick mới bị chậm 1 ca thì không cần báo trong report đâu"*), CẤM ghi đối phó vào conversation memory. Watchdog cronjob chạy nền hoàn toàn độc lập và không bao giờ đọc conversation memory. BẮT BUỘC sửa trực tiếp vào script / codebase tương ứng (ví dụ: `audit_stale_upload_accounts.py`, `cron_stale_upload_watchdog.py`), chuẩn hóa `days_threshold` $\ge 9$ ngày khớp với chu kỳ 4 ngày (96h) của farm để loại bỏ cảnh báo ảo cho các nick mới chỉ chậm 1 ca.
- **Silent Crash do nhầm Python hệ thống**: File `.vbs` trong Startup (`shell:startup`) hoặc launcher pythonw TUYỆT ĐỐI KHÔNG trỏ vào `C:\Users\Admin\AppData\Local\Programs\Python\Python311\pythonw.exe` vì môi trường này thiếu `psutil` và `openpyxl`. BẮT BUỘC dùng venv chuẩn: `D:\CodexRuntime\tiktok-video\venv-core024\Scripts\pythonw.exe`.
- **Bẫy `LogonType: Interactive` trong Task Scheduler**: Task Scheduler Windows mặc định gán `Interactive`, từ chối chạy khi máy reboot đứng ở màn hình khóa (Lock Screen) chưa ai login desktop (`LastRunTime` trống trơn). Cả file VBS trong `shell:startup` cũng bị tê liệt tương tự nếu không có interactive login. BẮT BUỘC cấu hình `/ru "SYSTEM"` cho cả 4 task Downloader và Render:
  `schtasks /Change /TN "Taadaa_Admin_Downloader_Boot" /RU "SYSTEM"`
  `schtasks /Change /TN "Taadaa_Admin_Downloader_15m" /RU "SYSTEM"`
  `schtasks /Change /TN "Taadaa_Admin_Render_Boot" /RU "SYSTEM"`
  `schtasks /Change /TN "Taadaa_Admin_Render_15m" /RU "SYSTEM"`
  (Hoặc qua PowerShell: `New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount`). Khi chạy dưới quyền `SYSTEM`, task sẽ kích hoạt ngay khi boot (`/sc onstart`) độc lập hoàn toàn với phiên desktop. Chi tiết xem [`references/admin-post-reboot-startup-and-task-scheduler-triage.md`](references/admin-post-reboot-startup-and-task-scheduler-triage.md).
- **Bẫy Môi Trường Venv Thiếu `psutil` & Fallback Watchdog:** Khi trỏ launcher sang `venv-core024`, môi trường này chưa từng cài `psutil`, khiến `watchdog_admin_downloader.py` và `watchdog_admin_render.py` chết ngầm lúc boot (văng `ModuleNotFoundError` trong 0.05s, Task Scheduler vẫn báo LastTaskResult 0). BẮT BUỘC chép/cài `psutil 7.2.2` vào `venv-core024\Lib\site-packages` và bọc `try...except ImportError` trong watchdog để fallback sang `wmic process`.
- **Bẫy Thiếu PATH `ffmpeg/ffprobe` Dưới Quyền `SYSTEM`:** Khi Task Scheduler chạy `/ru "SYSTEM"`, môi trường chỉ có System PATH, mất sạch User PATH của `Admin` (`AppData\Local\Microsoft\WinGet\Links`). Dẫn tới `download_by_niche.py` văng lỗi `Khong tim thay ffmpeg/ffprobe trong PATH` mỗi 30s. BẮT BUỘC chép `ffmpeg.exe`/`ffprobe.exe` vào `venv-core024\Scripts\` và tiêm cứng `os.environ["PATH"]` vào đầu launcher/service.
- **Bẫy `pythonw.exe` Mồ Côi Giữ File Lock Khi Restart:** `Stop-Process -Name python` chỉ diệt `python.exe`, bỏ sót `pythonw.exe`. Dịch vụ cũ tiếp tục giữ file lock qua `msvcrt.locking`, khiến instance mới không thể cào. BẮT BUỘC diệt sạch cả `pythonw.exe` bằng PID qua psutil trước khi khởi động instance mới.
- **Kỷ Luật Nghiệm Thu End-to-End Chống "Fix Nhiều Vòng Không Xong":** CẤM TUYỆT ĐỐI chỉ kiểm tra watchdog returncode 0 rồi vội vã báo xong. Bắt buộc nghiệm thu đủ 4 chặng: (1) Cú pháp `py_compile`; (2) Service chiếm lock và spawn worker; (3) File log tăng dung lượng thực tế không lỗi; (4) Watchdog Kibe nhận `is_dl: True` và `src_ge45` tăng delta clip thật. Chi tiết xem [`references/admin-task-scheduler-system-path-ffmpeg-and-multiloop-triage.md`](references/admin-task-scheduler-system-path-ffmpeg-and-multiloop-triage.md).
- **Render Worker dừng do thiếu nguồn đạt chuẩn**: Render chain tự động SKIP khi folder nguồn có $< 30$ clip. Khi Tik1..Tik5 đã đủ nhưng Tik6..Tik8 thiếu clip, render worker kết thúc bình thường (exit 0) chứ không phải bị crash. Cần kích hoạt downloader bù nguồn trước.
- **Kích hoạt Downloader 40 workers song song**: Chạy `python C:/Users/Admin/run_admin_downloader_service.py` qua đúng venv `venv-core024` kèm proxy MikroTik LAN `proxy_pool_69.txt` (UTF-8 No-BOM). Chống lỗi cấu hình proxy trỏ nhầm domain chết `test.taadaa.click:5137`.
- **Bẫy Watchdog Định Kỳ 15m Khi Chơi Game (Warcraft III / TFT) & Giải Pháp In-Flight Game Guard:** CẤM TUYỆT ĐỐI chỉ dùng Task Scheduler 15m để quét ngắt render khi người dùng chơi game. Khi watchdog kill `ffmpeg`, worker vòng lặp `for t in tasks:` cũ sẽ bắt lỗi và lập tức spawn lại `ffmpeg` mới ngay tại giây đó. BẮT BUỘC nhúng trực tiếp `is_gaming_active()` vào `run_admin_render_worker.py`: (1) Pre-check trước khi nhận task; (2) In-flight polling mỗi 2s qua `subprocess.Popen` để ngắt `ffmpeg` trong $\le 2$s ngay khi game mở; (3) Tự động Standby 0% CPU và Auto-Resume khi thoát game. Danh sách game bảo vệ: War3 (`war3.exe`, `frozen throne.exe`, `w3l.exe`), TFT (`league of legends.exe`, `tftclient.exe`); loại bỏ app chạy ngầm như `TFTAcademy.exe`. Chi tiết xem [`references/admin-render-in-flight-game-guard-and-auto-pause.md`](references/admin-render-in-flight-game-guard-and-auto-pause.md).
- **Kích hoạt Lại Toàn Diện Cào 40 Workers & Render Admin:**
  Khi cần kích hoạt cào 40 workers: `python D:/Taadaa/tools/admin_ssh.py "python C:/Users/Admin/run_admin_downloader_service.py"`.
  Khi cần kích hoạt render: `python D:/Taadaa/tools/admin_ssh.py "python C:/Users/Admin/launch_detached_admin_render.py"`.

## 4. Danh Mục Tham Khảo Chi Tiết
- Fastpath triage batch alert 2 cụm Kibe & Admin: [`references/dual-cluster-batch-triage-fastpath.md`](references/dual-cluster-batch-triage-fastpath.md)
- In-Flight Game Guard & Auto-Pause khi chơi War3/TFT trên Admin: [`references/admin-render-in-flight-game-guard-and-auto-pause.md`](references/admin-render-in-flight-game-guard-and-auto-pause.md)
- Bẫy SYSTEM Task Scheduler, thiếu PATH FFmpeg & nghiệm thu End-to-End: [`references/admin-task-scheduler-system-path-ffmpeg-and-multiloop-triage.md`](references/admin-task-scheduler-system-path-ffmpeg-and-multiloop-triage.md)
- Chuẩn hóa watchdog upload & sửa script thay vì ghi memory: [`references/stale-upload-cadence-threshold-and-script-first-discipline.md`](references/stale-upload-cadence-threshold-and-script-first-discipline.md)
- Phân tách cụm Kibe vs Admin & độc lập slot: [`references/stale-upload-watchdog-cluster-split-and-slot-triage.md`](references/stale-upload-watchdog-cluster-split-and-slot-triage.md)
- Khởi động sau reboot & Task Scheduler Admin: [`references/admin-post-reboot-startup-and-task-scheduler-triage.md`](references/admin-post-reboot-startup-and-task-scheduler-triage.md)
- Toàn bộ tài liệu quy trình cũ: [`references/historical-batch-ops-archive.md`](references/historical-batch-ops-archive.md)
- Downloader & Concurrency: [`references/dual-cluster-downloader-concurrency-and-proxy-hygiene.md`](references/dual-cluster-downloader-concurrency-and-proxy-hygiene.md)
- Video Standard 45 Clips: [`references/video-farm-standard-45-clips-and-supplementary-pipeline.md`](references/video-farm-standard-45-clips-and-supplementary-pipeline.md)
- Gái Xinh Pipeline: [`references/video-sourcing-gaixinh-two-tier-allocation.md`](references/video-sourcing-gaixinh-two-tier-allocation.md)
