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
- **Tra cứu máy N O(1):**
  `python D:/Taadaa/tools/inspect_machine.py <N>`

## 3. Danh Mục Tham Khảo Chi Tiết
- Toàn bộ tài liệu quy trình cũ: [`references/historical-batch-ops-archive.md`](references/historical-batch-ops-archive.md)
- Downloader & Concurrency: [`references/dual-cluster-downloader-concurrency-and-proxy-hygiene.md`](references/dual-cluster-downloader-concurrency-and-proxy-hygiene.md)
- Video Standard 45 Clips: [`references/video-farm-standard-45-clips-and-supplementary-pipeline.md`](references/video-farm-standard-45-clips-and-supplementary-pipeline.md)
- Gái Xinh Pipeline: [`references/video-sourcing-gaixinh-two-tier-allocation.md`](references/video-sourcing-gaixinh-two-tier-allocation.md)
