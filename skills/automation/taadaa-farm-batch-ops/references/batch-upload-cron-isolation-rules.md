# TikTok Batch Upload Manual Ops & Cron Isolation

## 1. Nguyên tắc cách ly Cron Feed khi chạy Batch Upload
- Khi kích hoạt batch upload thủ công (`run_tiktok_upload_batch.ps1 -Tik <N> -Confirmation RUN`), bắt buộc phải tạm dừng cron feed:
  ```python
  cronjob(action='pause', job_id='cdd43b124363')
  ```
- **Lý do:** Cron feed kích hoạt mỗi 15 phút sẽ tranh chấp thiết bị với upload. Nếu feed nhảy vào khi upload đang ở màn hình edit CapCut/TikTok, flow feed sẽ fail `navigation target profile not found in XML` và gửi alert đỏ làm gián đoạn upload.
- Sau khi toàn bộ các worker upload kết thúc, resume cron feed:
  ```python
  cronjob(action='resume', job_id='cdd43b124363')
  ```

## 2. Kiểm tra tiến trình Upload đang chạy
- Dùng `psutil` lọc `tiktok_workflow` hoặc `run_tiktok_upload_batch.ps1`:
  ```python
  import psutil
  py_workers = [p.info['pid'] for p in psutil.process_iter(['pid', 'cmdline']) if 'tiktok_workflow' in ' '.join(p.info.get('cmdline') or [])]
  ```
