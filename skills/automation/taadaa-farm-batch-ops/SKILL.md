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

## 3. Danh Mục Tham Khảo Chi Tiết
- Toàn bộ tài liệu quy trình cũ: [`references/historical-batch-ops-archive.md`](references/historical-batch-ops-archive.md)
- Downloader & Concurrency: [`references/dual-cluster-downloader-concurrency-and-proxy-hygiene.md`](references/dual-cluster-downloader-concurrency-and-proxy-hygiene.md)
- Video Standard 45 Clips: [`references/video-farm-standard-45-clips-and-supplementary-pipeline.md`](references/video-farm-standard-45-clips-and-supplementary-pipeline.md)
- Gái Xinh Pipeline: [`references/video-sourcing-gaixinh-two-tier-allocation.md`](references/video-sourcing-gaixinh-two-tier-allocation.md)
