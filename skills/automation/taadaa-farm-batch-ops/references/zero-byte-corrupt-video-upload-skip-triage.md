# Zero-Byte Corrupt Video Files & Upload Preflight Skip Triage

## 1. Hiện tượng & Triệu chứng nhận diện
- Báo cáo đối soát stale upload (`cron_stale_upload_watchdog.py`) cảnh báo tài khoản bị đóng băng nhiều ngày dù kho video báo đủ 45 clips.
- File log upload `upload_result.json` ghi nhận:
  ```json
  {
    "status": "skipped",
    "reason": "video_not_rendered",
    "expected_video": "D:\\TIKTOK-videonuoinick\\<folder>\\<N>.mp4"
  }
  ```
- Kiểm tra thư mục trên đĩa `D:/TIKTOK-videonuoinick/<folder>/`: có đủ các file từ `1.mp4` đến `45.mp4`, nhưng file số `<N>.mp4` (và một số file liền kề) có kích thước đúng **0 bytes** (`size == 0`).

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Lỗi ngắt quãng render cũ:**
   Trong các đợt render trước, nếu tiến trình FFmpeg bị kill cưỡng bức, host reboot đột ngột hoặc ổ đĩa bị lag tạm thời, các file `.mp4` đích đang ghi dở có thể bị bỏ lại dưới dạng file rỗng 0-byte.
2. **Cơ chế Preflight Fail-Safe của Farm:**
   `upload_preflight.py` kiểm tra nghiêm ngặt `os.path.getsize(expected_video) > 0`. Khi gặp file 0-byte, hệ thống nhận định video chưa được render hoàn tất và từ chối upload để chống đăng clip rác / đen màn hình lên kênh.

## 3. Quy trình xử lý O(1) Bù Video Nhanh Chóng

### Bước 1: Quét và dọn sạch file 0-byte
Xóa triệt để các file 0-byte trong folder đích:
```python
from pathlib import Path
target_dir = Path("D:/TIKTOK-videonuoinick/<folder>")
for p in target_dir.glob("*.mp4"):
    if p.stat().st_size == 0:
        p.unlink()
```

### Bước 2: Kích hoạt `batch_render.py` bù clip khuyết (Không render lại từ đầu)
Chạy lệnh `batch_render.py` với cờ `--name-format "{stem}"` và **KHÔNG** truyền cờ `--overwrite`:
```bash
python D:/Taadaa/Tiktok-video/scripts/batch_render.py \
  --input-dir "D:/video goc/<source_folder>" \
  --output-dir "D:/TIKTOK-videonuoinick/<target_folder>" \
  --preset "D:/Taadaa/Tiktok-video/presets/preset_a_capcut_vignette.json" \
  --run-id "repair_<target_folder>" \
  --name-format "{stem}" \
  --parallel 1
```
- **Cơ chế tự động bỏ qua (Skip existing):** `batch_render.py` tự động kiểm tra `if task.output.exists() and not overwrite: return skipped`. Toàn bộ 35-40 clip hợp lệ đã có sẵn sẽ được bỏ qua trong 0.1 giây.
- **Tiết kiệm tài nguyên:** Hệ thống chỉ render riêng các clip 0-byte vừa bị xóa, hoàn thành chỉ sau 30-60 giây thay vì phải đợi 20 phút render lại cả folder.
