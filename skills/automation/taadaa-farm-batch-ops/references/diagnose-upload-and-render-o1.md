# Quy trình chẩn đoán O(1) khi không đăng video / nghi vấn chưa render (2026-09-17)

## Bối cảnh & Vấn đề thực tế
Khi user đặt câu hỏi: *"Chưa render video hay sao mà không đăng video vậy?"*, *"sao ca này không thấy đăng video"*, *"đăng video lỗi lắm"*:
- Không được suy đoán mò mẫm hay tự viết script quét toàn bộ thư mục `D:\TIKTOK-videonuoinick` hoặc `D:\video goc`.
- **Nguy cơ nghẽn đĩa I/O (HDD Saturation Timeout >180s):** Khi hệ thống đang chạy `download_by_niche.py` (tải video gốc song song 20 worker) hoặc chạy ffmpeg render ngầm ghi đĩa D:, việc gọi `os.scandir` / `os.listdir` qua 640 folder để đếm file sẽ làm nghẽn đĩa nghiêm trọng và command bị kill sau 180s.

---

## 2 Bước chẩn đoán O(1) chuẩn xác

### Bước 1: Tra cứu nhanh qua Global Shift Upload Ledger (<5ms)
Đọc file JSON đã được hệ thống ghi nhận tập trung:
`C:\ProgramData\Taadaa\tiktok-upload-concurrency-v1\shift_upload_history.json`

```python
import json

with open(r'C:\ProgramData\Taadaa\tiktok-upload-concurrency-v1\shift_upload_history.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

# Thống kê nhanh theo ngày và ca (row 1..8)
for row in range(1, 9):
    entries = [v for k, v in d.items() if '2026-09-17' in k and v.get('row') == row]
    success = sum(1 for v in entries if v.get('status') == 'success')
    launched = sum(1 for v in entries if v.get('status') == 'launched')
    failed = sum(1 for v in entries if v.get('status') == 'failed')
    print(f'Row {row} (Tik{row}): success={success} | launched={launched} | failed={failed}')
```

### Bước 2: Phân loại nguyên nhân qua `upload_result.json` của ca hiện tại
Đọc trực tiếp các file kết quả từng máy trong phiên:
`D:\Taadaa\runtime\kibe\live\<today>\<shift_dir>\machines\machine_<N>\<shift_dir>\upload_result.json`

Thống kê theo các nhóm nguyên nhân thực tế:
1. **`missing_account_id` / `Missing required fields: ID TikTok`**: File `TikN.xlsx` của ca đó chưa nạp đủ nick / đang để trống nick (rất phổ biến ở các ca Tik5..Tik8 mới lập).
2. **`organic-rest-day-no-upload`**: Trúng lịch nghỉ an toàn 1/3 ngày tự nhiên của tài khoản (không phải lỗi).
3. **`account_cooling_period_until_<date>`**: Nick mới tạo chưa đủ 10 ngày cooldown theo Gate 4c.
4. **`video_not_rendered`**: Thiếu video đã render trong `D:\TIKTOK-videonuoinick\<folder>`.
5. **`ACCOUNT_SWITCHER_FAILED` / `post_verification_failed`**: Lỗi giao diện TikTok hoặc máy bị văng session cần login/recovery.

---

## Kiểm tra trạng thái Render & Video Gốc O(1)
- **Tiến trình render đang chạy:** Kiểm tra tiến trình `random_batch_render.py` và `ffmpeg.exe` qua `psutil`.
- **Tiến độ tải video gốc:** Đọc bảng `folders` trong SQLite `C:\CodexRuntime\tiktok-video\state.db` (thời gian truy vấn <10ms, không đụng đến HDD I/O).
