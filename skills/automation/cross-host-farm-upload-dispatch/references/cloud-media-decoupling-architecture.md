# Cloud Media Decoupling Architecture for Phone Farms

## 1. Vấn đề cốt lõi: Cạnh tranh tài nguyên trên Host điều khiển Farm
- Các tác vụ media: Cào video (yt-dlp luồng lớn), transcode ffmpeg (encode H.264/AAC, resize, crop), bóc transcript, dịch thuật, render template... là các tác vụ **Stateless, CPU-bound & Bandwidth-bound**.
- Khi chạy trực tiếp các batch này trên PC Host Kibe / Admin (đang cắm 80 thiết bị Android):
  * CPU spikes 100% làm nghẽn bus USB.
  * ADB daemon rớt kết nối (`device offline`, `ADB server not responding`).
  * ATX-agent timeout (gây lỗi đọc màn hình XML và nhận diện sai nút).

## 2. Mô hình Decoupled Cloud Runner
Tách rời hoàn toàn vòng đời Media khỏi Farm Host:
```text
[ CLOUD WORKER / VPS / GROK BOT ]
  - Chạy scraper (yt-dlp, Douyin crawler)
  - Chạy ffmpeg render độc lập
  - Đẩy video thành phẩm lên Cloud Storage (OneDrive / S3)
                │
                ▼ (Sync tự động / Rclone ngầm)
[ ON-PREMISE FARM HOST (Kibe / Admin) ]
  - Chỉ kéo video thành phẩm về folder đích
  - Dành 100% CPU/RAM/USB cho điều khiển ADB & farm runner
```

## 3. Tiêu chuẩn đóng gói Standalone Runner
1. **Zero-Windows Hardcode:** Không dùng đường dẫn cứng `D:/Taadaa/...`. Tất cả path cấu hình qua file `.env` hoặc tham số dòng lệnh.
2. **Containerized / Headless:** Đóng gói kèm `Dockerfile` hoặc `setup_runner.sh` (Python 3.11+, ffmpeg, yt-dlp).
3. **Write-Through Status:** Cập nhật trạng thái video vào SQLite hoặc JSON ledger trước khi đồng bộ về host, đảm bảo tính idempotent (chạy lại không trùng lặp).
