# GPM Concurrency Guard & Orphan Browser Cleanup

## 1. Bản chất sự cố tích tụ Chrome mồ côi (Orphan Browser Leaks)
Khi chạy các cronjob / watchdog tự động hóa GPM (ví dụ: `post_morning_gmail_2fa_watchdog.py`, `batch_dual_oauth_5workers.py`, `cron_gpm_gmail_nurture.py`):
- **API Stop không đảm bảo kill process**: Gọi `GET /api/v3/profiles/stop/{id}` chỉ là tín hiệu mềm gửi tới GPMLogin core. Nếu trình duyệt bị đơ (hang), kẹt modal popup, mất kết nối CDP, hoặc GPMLogin server bị quá tải, lệnh stop có thể timeout (10-15s) hoặc trả về success giả trong khi tiến trình `chrome.exe` (`gpm_browser`) vẫn tiếp tục sống.
- **Tích tụ qua các chu kỳ cron**: Khi cron chạy lặp lại mỗi 5-15 phút, mỗi chu kỳ bỏ quên 1-3 tiến trình Chrome. Sau vài giờ đến vài ngày, hàng chục profile Chrome mồ côi kẹt trên thanh Taskbar / RAM, gây sụt giảm hiệu năng máy trạm và làm nghẽn toàn bộ cổng proxy 4G.
- **Bùng nổ đồng thời (Concurrency Storm)**: Đặt `MAX_WORKERS` quá lớn (ví dụ 30 workers) mà không có stagger khởi động sẽ nã hàng chục request mở profile cùng một giây vào port 19995. GPM API bị nghẽn dẫn đến crash hoặc mở browser nhưng script client timeout và bỏ rơi tiến trình.

---

## 2. Kỷ luật vận hành: CẤM PAUSE CRONJOB khi lỗi
User invariant:
- **Tuyệt đối CẤM dùng `cronjob(action='pause')`** khi phát hiện cronjob gây spam tiến trình hoặc gặp lỗi.
- **Quy trình xử lý đúng**:
  1. Kill sạch hiện trường ngay lập tức bằng lệnh PowerShell.
  2. Sửa trực tiếp mã nguồn (hot-fix code) để khắc phục tận gốc logic đóng tiến trình và kiểm soát luồng.
  3. Để cronjob tiếp tục chạy tự nhiên ở các chu kỳ tiếp theo với code đã vá.

---

## 3. Lệnh khẩn cấp dọn sạch Chrome GPM (Emergency Mass Cleanup)
Khi phát hiện hàng chục tiến trình Chrome GPM mồ côi kẹt trên máy:
```powershell
# Kill toàn bộ chrome.exe thuộc gpm_browser ngay lập tức:
Get-Process chrome -ErrorAction SilentlyContinue | Where-Object { $_.Path -match 'gpm_browser' } | Stop-Process -Force

# Xác nhận số lượng còn lại = 0:
(Get-Process chrome -ErrorAction SilentlyContinue | Where-Object { $_.Path -match 'gpm_browser' }).Count
```

---

## 4. Chuẩn mực Concurrency & Stagger
- **Giới hạn số luồng (Hard Concurrency Cap)**:
  - Mặc định tối đa: **5 luồng cuốn chiếu** (`MAX_WORKERS = 5`, `concurrency = 5`).
  - Tuyệt đối cấm để concurrency tự do (10, 20, 30 workers) trên máy trạm Windows chạy chung môi trường Farm.
- **Stagger khởi động (Startup Stagger)**:
  - Bắt buộc chèn độ trễ so le giữa các lần submit worker:
  ```python
  with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
      futures = []
      for m, s, email in eligible:
          futures.append(executor.submit(_process_single, m, s, email))
          time.sleep(3)  # Giãn cách 3 giây chống nghẽn GPM API port 19995
      for f in as_completed(futures):
          f.result()
  ```

---

## 5. Cơ chế dọn dẹp kép trong `finally:` (Deterministic Dual-Teardown)
Mọi worker khởi động profile GPM bắt buộc phải bọc trong khối `try ... finally:` với 2 bước dọn dẹp:

```python
finally:
    # Bước 1: Gọi API đóng profile mềm
    if profile_id:
        try:
            requests.get(f"http://127.0.0.1:19995/api/v3/profiles/stop/{profile_id}", timeout=10)
        except Exception:
            pass

    # Bước 2: Force-kill dứt điểm tiến trình Chrome theo remote debugging port
    if remote_port:
        try:
            ps_cmd = (
                f"Get-CimInstance Win32_Process -Filter \"Name = 'chrome.exe'\" | "
                f"Where-Object {{ $_.CommandLine -match '{remote_port}' }} | "
                f"ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }}"
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=10)
        except Exception:
            pass
```

- Với các tác vụ map theo máy Farm (`machine_id = m`), port CDP thường quy ước là `5100 + m`.
- Với các script dynamic, trích xuất port trực tiếp từ `remote_debugging_address` (ví dụ `127.0.0.1:65249` -> `remote_port = 65249`).

---

## 6. Đồng bộ bắt buộc giữa Runtime và Git Deploy
Khi chỉnh sửa các script watchdog hoặc cron trong `%LOCALAPPDATA%/hermes/scripts/`:
- BẮT BUỘC kiểm tra và đồng bộ sang file tương ứng trong `D:/Taadaa/Hermes/deploy/hermes-home/scripts/`.
- Chạy `diff -u` xác nhận 2 file khớp nhau 100%.
- Kiểm tra cú pháp bằng `python -m py_compile` cả 2 bản trước khi kết thúc ca.
