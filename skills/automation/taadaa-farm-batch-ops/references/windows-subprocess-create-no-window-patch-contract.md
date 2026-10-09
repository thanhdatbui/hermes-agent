# Windows Subprocess CREATE_NO_WINDOW Patch Contract (Tiktok-video)

## Bối cảnh & Hiện tượng
Khi các batch runner (render video ngẫu nhiên, tải video theo niche, bóc tách avatar, probe ffprobe) chạy ngầm trên Windows, mỗi lệnh gọi `subprocess.run` / `subprocess.Popen` đối với `ffmpeg`, `ffprobe` hoặc CLI ngoài mà thiếu cờ `CREATE_NO_WINDOW` sẽ khiến:
- Cửa sổ console đen (cmd/conhost) liên tục nhấp nháy trên màn hình.
- Icon nhấp nháy trên taskbar, làm gián đoạn trải nghiệm người dùng trên máy farm/desktop dùng chung.

## Chuẩn Patch Contract đa nền tảng
Để đảm bảo an toàn tuyệt đối, không gây lỗi cú pháp hoặc `AttributeError` trên các hệ điều hành khác, sử dụng idiom chuẩn sau:

```python
kwargs = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if sys.platform == "win32" else {}
result = subprocess.run(..., **kwargs)
```

## Các vị trí cần bảo vệ trong `D:\Taadaa\Tiktok-video`
1. `scripts/random_batch_render.py`:
   - Hàm `run_ffmpeg`: chèn `**kwargs` vào `subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, text=True, **kwargs)`.
2. `scripts/media_probe.py`:
   - **BẪY QUAN TRỌNG:** `scripts/media_probe.py` ban đầu **CHƯA `import sys`**. Bắt buộc thêm `import sys` ở đầu file trước khi kiểm tra `sys.platform == "win32"`, tránh dính `NameError: name 'sys' is not defined`.
   - Hàm `probe_media`: chèn `**kwargs` vào `subprocess.run(cmd, capture_output=True, text=True, **kwargs)`.
3. `scripts/download_by_niche.py`:
   - Hàm `probe_duration`: chèn `**kwargs` vào `subprocess.run`.
   - Vòng lặp cắt mẫu audio test tiếng Việt: chèn `**kwargs` vào `subprocess.run` gọi `args.ffmpeg`.
   - Hàm `video_hashes`: chèn `**kwargs` vào `subprocess.run` trích xuất frame.
   - Hàm fallback tạo avatar (`avatar_fallback_frame.jpg`): chèn `**kwargs` vào `subprocess.run` gọi `args.ffmpeg`.
4. `scripts/pipeline_common.py`:
   - Hàm `make_avatar_fallback` (cắt frame avatar).
   - Hàm `make_person_avatar` (trích xuất frame nhận diện khuôn mặt).
   - Hàm `strip_metadata` (cả bước `-c copy` và re-encode `-c:v libx264`).
   - Hàm `verify_clean_mp4` (gọi `ffprobe`).

## Quy chuẩn kiểm thử sau vá
Chạy test hồi quy:
```bash
pytest tests/test_vietnamese_pipeline.py -q
```
Đảm bảo 29/29 tests pass trước khi nghiệm thu.
