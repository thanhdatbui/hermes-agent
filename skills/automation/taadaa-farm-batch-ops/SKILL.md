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
- **Tra cứu máy N O(1):**
  `python D:/Taadaa/tools/inspect_machine.py <N>`
- **Chẩn đoán Nhanh Admin Dừng Down / Dừng Render O(1):**
  Đọc `D:\OneDrive\TaadaaData\admin\last_render_stats.json` thay vì gọi SSH. Phân biệt: (1) Render dừng do đã vét hết nguồn $\ge 30$ clip (Tik6..Tik8 thiếu raw); (2) Downloader dừng do chạy hết pass và/hoặc bị ngắt bởi ca reboot 05:20/11:20/17:20 dừng ở Windows Lock Screen.

## 3. Cạm Bẫy Khởi Động Sau Reboot & Tải Video (Pitfalls)
- **Bẫy ghi Memory thay vì sửa Code khi User yêu cầu chỉnh tiêu chí Báo cáo Watchdog:** Khi người dùng chỉ thị thay đổi tiêu chí, bộ lọc hoặc ngưỡng cảnh báo của một bản tin watchdog (ví dụ: *"Các nick mới bị chậm 1 ca thì không cần báo trong report đâu"*), CẤM ghi đối phó vào conversation memory. Watchdog cronjob chạy nền hoàn toàn độc lập và không bao giờ đọc conversation memory. BẮT BUỘC sửa trực tiếp vào script / codebase tương ứng (ví dụ: `audit_stale_upload_accounts.py`, `cron_stale_upload_watchdog.py`), chuẩn hóa `days_threshold` $\ge 9$ ngày khớp với chu kỳ 4 ngày (96h) của farm để loại bỏ cảnh báo ảo cho các nick mới chỉ chậm 1 ca.
- **Silent Crash do nhầm Python hệ thống**: File `.vbs` trong Startup (`shell:startup`) hoặc launcher pythonw TUYỆT ĐỐI KHÔNG trỏ vào `C:\Users\Admin\AppData\Local\Programs\Python\Python311\pythonw.exe` vì môi trường này thiếu `psutil` và `openpyxl`. BẮT BUỘC dùng venv chuẩn: `D:\CodexRuntime\tiktok-video\venv-core024\Scripts\pythonw.exe`.
- **Bẫy `LogonType: Interactive` trong Task Scheduler**: Task Scheduler Windows mặc định gán `Interactive`, từ chối chạy khi máy reboot đứng ở màn hình khóa (Lock Screen) chưa ai login desktop. BẮT BUỘC cấu hình `/ru SYSTEM` hoặc gán ServiceAccount để task boot (`/sc onstart`) kích hoạt độc lập với GUI session.
- **Render Worker dừng do thiếu nguồn đạt chuẩn**: Render chain tự động SKIP khi folder nguồn có $< 30$ clip. Khi Tik1..Tik5 đã đủ nhưng Tik6..Tik8 thiếu clip, render worker kết thúc bình thường (exit 0) chứ không phải bị crash. Cần kích hoạt downloader bù nguồn trước.
- **Kích hoạt Downloader 40 workers song song**: Chạy `python C:/Users/Admin/run_admin_downloader_service.py` qua đúng venv `venv-core024` kèm proxy MikroTik LAN `proxy_pool_69.txt` (UTF-8 No-BOM). Chống lỗi cấu hình proxy trỏ nhầm domain chết `test.taadaa.click:5137`.
- **Kích hoạt Lại Toàn Diện Cào 40 Workers & Render Admin:**
  Khi cần kích hoạt cào 40 workers: `python D:/Taadaa/tools/admin_ssh.py "python C:/Users/Admin/run_admin_downloader_service.py"`.
  Khi cần kích hoạt render: `python D:/Taadaa/tools/admin_ssh.py "python C:/Users/Admin/launch_detached_admin_render.py"`.

## 4. Danh Mục Tham Khảo Chi Tiết
- Chuẩn hóa watchdog upload & sửa script thay vì ghi memory: [`references/stale-upload-cadence-threshold-and-script-first-discipline.md`](references/stale-upload-cadence-threshold-and-script-first-discipline.md)
- Phân tách cụm Kibe vs Admin & độc lập slot: [`references/stale-upload-watchdog-cluster-split-and-slot-triage.md`](references/stale-upload-watchdog-cluster-split-and-slot-triage.md)
- Khởi động sau reboot & Task Scheduler Admin: [`references/admin-post-reboot-startup-and-task-scheduler-triage.md`](references/admin-post-reboot-startup-and-task-scheduler-triage.md)
- Toàn bộ tài liệu quy trình cũ: [`references/historical-batch-ops-archive.md`](references/historical-batch-ops-archive.md)
- Downloader & Concurrency: [`references/dual-cluster-downloader-concurrency-and-proxy-hygiene.md`](references/dual-cluster-downloader-concurrency-and-proxy-hygiene.md)
- Video Standard 45 Clips: [`references/video-farm-standard-45-clips-and-supplementary-pipeline.md`](references/video-farm-standard-45-clips-and-supplementary-pipeline.md)
- Gái Xinh Pipeline: [`references/video-sourcing-gaixinh-two-tier-allocation.md`](references/video-sourcing-gaixinh-two-tier-allocation.md)
