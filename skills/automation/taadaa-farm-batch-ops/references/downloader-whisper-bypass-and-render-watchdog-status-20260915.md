# Triage & Chuẩn Hóa Downloader Bị Treo Khởi Động Do Torch/Whisper, Bổ Sung Render Status Cho Watchdog & Triệt Tiêu Cron Spam

## 1. Hiện Tượng Thực Tế (15/09/2026)
- Báo cáo cron định kỳ `farm-render-download-watchdog` lúc 04:00 gửi về nhóm Farm Alert hiển thị:
  - `Trạng thái download: ⚪ Đang dừng`
  - Đạt ≥ 30 video: `532/640 folder` (còn 108 folder từ 481..640 chưa đủ video).
  - Mục Render chỉ liệt kê số folder / clip của từng Tik mà **hoàn toàn không hiển thị trạng thái Render đang chạy hay đang dừng**.
- Người vận hành thắc mắc: *"Có đang download và render mới k v? Download cho tao đủ folder >30 video hết 640 folder chứ. Kiểm tra render có đang tăng k"*.
- Ngay sau đó, cronjob `post-morning-gmail-2fa-watchdog` liên tục spam tin nhắn rỗng vào group mỗi 5 phút:
  `[BÁO CÁO 2FA GMAIL SAU CA SÁNG] - Tổng máy đủ điều kiện: 0 - Success: [] - Fail: []`.

## 2. Nguyên Nhân Cốt Lõi (Root Causes)

### A. Sự Cố Downloader Bị Treo Khởi Động (Hanging Torch/Whisper Import)
- Khi gọi launcher download (`run_download_kibe_full.bat` hoặc `run_download_kibe.py`) sử dụng Python venv `D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe`:
  - Trong `download_by_niche.py`, mặc định `args.language_mode` là `"vietnamese"`.
  - Dòng 1645-1647 kích hoạt `import faster_whisper`, kéo theo `import torch`.
  - Trên môi trường Windows này, tiến trình `import torch` trong venv bị deadlock/kẹt vô hạn (CPU = 0, Memory kẹt ở ~4MB), khiến tiến trình Python bị đứng im ngay tại khởi động mà không bao giờ ghi được byte nào vào `download_run.log`.
  - Do các nguồn trong `sources.qualified30.json` đã được qualify từ trước, cờ `--all-languages` cho phép bỏ qua bước import và kiểm tra Whisper audio gate, giúp downloader khởi động tức thì trong < 1 giây.

### B. Thiếu Trạng Thái Render Trong Watchdog (`farm_render_download_watchdog.py`)
- Script `farm_render_download_watchdog.py` chỉ định nghĩa hàm `is_download_running()` mà thiếu hoàn toàn hàm kiểm tra render `is_render_running()`.
- Do đó, dù tiến trình render (`run_kibe_slot7_slot8_render.ps1`, `random_batch_render.py`, `ffmpeg`) đang chạy cật lực và encode liên tục, watchdog vẫn không hiển thị trạng thái render khiến người vận hành lầm tưởng hệ thống đang dừng toàn bộ.

### C. Gửi Lặp Tin Nhắn Do Cron `no_agent=True` Trong `post_evening_avatar_watchdog.py`
- Khi cấu hình cron Hermes `no_agent: true` với `deliver: telegram:-5373649734`, Scheduler tự động bắt toàn bộ output từ `stdout` (`print`) để gửi tin nhắn.
- Trong `report_final_summary()`, script vừa tự gọi `send_farm_alert(report_msg)` trực tiếp tới Telegram Bot API, vừa gọi `print(report_msg)`, dẫn đến tin nhắn bị bắn kép 2 lần liên tiếp.

### D. Bẫy Spam Của Watchdog 2FA Gmail Ca Sáng (`post-morning-gmail-2fa-watchdog`)
- Cronjob chạy mỗi 5 phút ở chế độ `no_agent=True`. Khi đến bước báo cáo, dù danh sách máy đủ điều kiện là `0`, script vẫn `print` template rỗng ra stdout làm scheduler tự động bắt và bắn tin nhắn rác vào Telegram mỗi 5 phút.

## 3. Giải Pháp Kỹ Thuật Chuẩn Đã Áp Dụng

### A. Kích Hoạt Downloader Phủ Đủ 640 Folders
- Bổ sung `--all-languages` vào `run_download_kibe_full.bat` để bypass module torch/whisper bị treo.
- Cấu hình chuẩn chạy ngầm:
  ```bat
  "D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe" -u scripts/download_by_niche.py ^
    --total-folders 640 ^
    --start-folder 481 ^
    --sources "D:/OneDrive/SharedData/tiktok-video/sources.qualified30.json" ^
    --state-db "C:/CodexRuntime/tiktok-video/state.db" ^
    --runtime "C:/CodexRuntime/tiktok-video" ^
    --output-root "D:/video goc" ^
    --niche-mode strict ^
    --all-languages ^
    --min-videos 30 ^
    --target-videos 45 ^
    --max-videos 65 ^
    --max-folders-per-channel 2 ^
    --parallel 20 ^
    --continue-on-insufficient ^
    --proxy-pool "D:/Taadaa/Tiktok-video/proxy_pool_67.txt" ^
    --cookies-dir "D:/CodexRuntime/tiktok-video" ^
    --global-ledger-dir "D:/OneDrive/SharedData/tiktok-video/global-ledger" ^
    --ledger-machine-id Kibe
  ```

### B. Nâng Cấp Watchdog Bổ Sung Trạng Thái Render
- Thêm `is_render_running()` vào `farm_render_download_watchdog.py`:
  ```python
  def is_render_running():
      if not psutil:
          return False
      for p in psutil.process_iter(["name", "cmdline"]):
          try:
              cmd = " ".join(p.info["cmdline"] or []).lower()
              if "random_batch_render.py" in cmd or "ffmpeg" in cmd:
                  return True
          except Exception:
              pass
      return False
  ```
- Hiển thị trực quan trong báo cáo Telegram:
  ```
  🎬 2. Tiến độ Render Tik1..Tik8 (D:\TIKTOK-videonuoinick):
  • Trạng thái render: 🟢 Đang chạy
  ```
- Đồng bộ file đã sửa sang:
  - `C:\Users\Kibe\AppData\Local\hermes\scripts\farm_render_download_watchdog.py`
  - `D:\Taadaa\Hermes\deploy\hermes-home\scripts\farm_render_download_watchdog.py`
  - `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\farm_render_download_watchdog.py`

### C. Triệt Tiêu Tin Báo Đúp Trong Watchdog Avatar
- Gỡ bỏ `send_farm_alert(report_msg)` trong `report_final_summary()` của `post_evening_avatar_watchdog.py`, chỉ giữ lại `print(report_msg)` để scheduler Hermes chịu trách nhiệm deliver duy nhất 1 lần vào Farm Alert.

### D. Xử Lý Triệt Để Spam Watchdog no_agent=True
- Loại bỏ vĩnh viễn job `post-morning-gmail-2fa-watchdog` (`cronjob remove`) và dọn sạch khỏi `jobs.json` ở Git deploy và OneDrive sync.
- Quy chuẩn bất biến cho mọi watchdog script `no_agent=True`: Khi không có hành động hoặc số lượng máy = 0, script BẮT BUỘC im lặng hoàn toàn (exit 0, stdout rỗng).
