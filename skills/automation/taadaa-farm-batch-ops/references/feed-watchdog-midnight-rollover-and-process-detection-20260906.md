# Quy chuẩn Watchdog Báo cáo Phiên Nuôi Acc: Chống Chốt Non Khi Phiên Vắt Qua Nửa Đêm & Nhận Diện Tiến Trình CLI (2026-09-06)

## 1. Hiện tượng & Triệu chứng
- Kênh Telegram nhận được tin nhắn tổng kết phiên:
  `📊 [TIKTOK NUÔI ACC] Ca 3 - Phiên 3/3 (Tối - Đăng video) hoàn tất (Row 5)`
  `• Tổng máy xử lý: 2 máy` (hoặc số lượng máy rất nhỏ, 1-3 máy).
- Trong khi thực tế toàn farm đang vận hành 70–80 máy và các máy vẫn đang tiếp tục xử lý lướt feed / upload video bình thường.

## 2. Nguyên nhân cốt lõi (Root Cause)

### A. Phiên cuối ngày chạy vắt qua nửa đêm (Midnight Rollover)
- Ca 3 - Phiên 3 (21:45 - 23:59) thường kích hoạt vào khung giờ muộn (ví dụ 22:30). Với quy mô 70–80 máy chạy đồng thời lướt feed + hook upload video, tổng thời lượng thực thi kéo dài từ 40–55 phút.
- Do đó, thời điểm kết thúc thực tế của phiên rơi vào khoảng 00:05 – 00:15 của ngày hôm sau.

### B. Lỗi logic `can_report_session` khi `is_today = False`
- Khi đồng hồ chuyển sang `00:00:xx`, ngày hệ thống (`today`) chuyển sang ngày mới (ví dụ từ `2026-09-05` sang `2026-09-06`).
- Thư mục chạy của Ca 3 Phiên 3 thuộc về ngày cũ (`target_date = 2026-09-05`), dẫn đến biểu thức `is_today = (target_date == today)` trả về `False`.
- Trong code watchdog cũ:
  ```python
  def can_report_session(is_today, completed_expected_count, expected_count, now_hm, window_end_hm, runner_busy):
      if is_today:
          return (completed_expected_count >= expected_count and not runner_busy) or (now_hm >= window_end_hm)
      return True  # <-- LỖI: Ngày hôm qua luôn return True vô điều kiện!
  ```
- Việc trả về `True` vô điều kiện khiến watchdog chốt phiên ngay ở tick đầu tiên sau nửa đêm (ví dụ 00:00:33), khi mà chỉ mới có 1–2 máy chạy nhanh hoàn thành sớm và ghi `summary.txt`.

### C. Lỗi nhận diện tiến trình con trong `is_feed_runner_active()`
- Hàm kiểm tra runner hoạt động chỉ tìm chuỗi `multi_machine_feed_session` (dấu gạch dưới):
  ```python
  if "multi_machine_feed_session" in cmd or "run-feed-session.ps1" in cmd or "run_follow" in cmd:
      return True
  ```
- Tuy nhiên, lệnh chạy thực tế từ `tiktok_runner.py` / hermes cron lại sử dụng cờ CLI:
  `python.exe .\python_runner\run_tiktok.py --mode multi-machine-feed-session ...`
  (dấu gạch nối `-`, không phải gạch dưới `_`).
- Đồng thời không kiểm tra `run_tiktok.py`, `hermes_cron_runner.py` hay `tiktok_runner.py`, dẫn đến `is_feed_runner_active()` luôn trả về `False` ngay cả khi tiến trình 73 máy đang chạy ngốn 110MB+ RAM.

## 3. Quy chuẩn sửa đổi & Giải pháp kỹ thuật

### 1. Nâng cấp nhận diện tiến trình (`is_feed_runner_active`)
Bắt buộc bổ sung đầy đủ các token lệnh thực tế:
```python
def is_feed_runner_active() -> bool:
    try:
        import psutil
        for p in psutil.process_iter(['name', 'cmdline']):
            try:
                name = (p.info.get('name') or '').lower()
                if not name.startswith(('python', 'powershell', 'pwsh')):
                    continue
                cmd = " ".join(p.info.get('cmdline') or [])
                tokens = [
                    "multi_machine_feed_session",
                    "multi-machine-feed-session",
                    "run-feed-session.ps1",
                    "run_follow",
                    "run_tiktok.py",
                    "hermes_cron_runner.py",
                    "tiktok_runner.py",
                ]
                if any(t in cmd for t in tokens):
                    return True
            except Exception:
                pass
    except Exception:
        pass
    return False
```

### 2. Khóa cứng logic chốt báo cáo (`can_report_session`)
Tuyệt đối KHÔNG cho phép report nếu tiến trình runner đang hoạt động, bất kể là ngày hôm nay hay ngày hôm qua:
```python
def can_report_session(
    is_today: bool,
    completed_expected_count: int,
    expected_count: int,
    now_hm: str,
    window_end_hm: str,
    runner_busy: bool,
) -> bool:
    # BẤT DI BẤT DỊCH: Nếu runner đang bận xử lý trên máy thì cấm chốt báo cáo
    if runner_busy:
        return False
        
    if is_today:
        return (completed_expected_count >= expected_count) or (now_hm >= window_end_hm)
        
    # Đối với phiên thuộc ngày hôm trước:
    # Chỉ cho phép chốt khi runner đã dừng hẳn VÀ (đã đạt đủ máy expected HOẶC đã sang hẳn sáng ngày mới > 02:00)
    return not runner_busy
```

### 3. Quy trình khôi phục khi gặp sự cố chốt non
Khi phát hiện watchdog đã gửi tin báo cáo non (chỉ 1–2 máy):
1. Mở file `D:\Taadaa\runtime\kibe\cron-state\feed_session_reported.json`.
2. Xóa bỏ phần tử phiên bị lỗi (ví dụ `"2026-09-05_ca3_phien3"`) khỏi mảng `reported_sessions`.
3. Khi tiến trình batch trên các máy hoàn tất trọn vẹn, tick kế tiếp của watchdog sẽ tự động quét lại toàn bộ thư mục run, gom đủ 70–80 máy và bắn báo cáo đầy đủ, chuẩn xác lên Telegram.
