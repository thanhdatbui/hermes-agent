# Gate Conflict Resolution: Media Gate (Gate 6) vs Device Lock Guard & Screencap Pattern

*Ngày ghi nhận:* 20/10/2026
*Ngữ cảnh:* Task cấu hình mạng/hạ tầng farm (Wi-Fi M7). Coordinator bị kẹt giữa Gate 6 (bắt buộc gửi MEDIA: screencap hiện trường) và Guard Device Bulkhead (`guard_device_bulkhead.py` default-deny raw ADB commands).

## 1. Bản Chất Sự Cố (The Gate Conflict / Explaining-Away Trap)
Khi Operator yêu cầu nghiệm thu hiện trường hoặc Gate 6 đòi hỏi visual evidence, Coordinator thử gọi trực tiếp:
```bash
adb -s <serial> exec-out screencap -p > screen.png
```
Lệnh này bị `hooks/guard_device_bulkhead.py` chặn ngay lập tức với lý do `COORDINATOR TERMINAL BLOCKED (DEFAULT-DENY)` vì vi phạm luật cấm can thiệp thiết bị trần từ terminal mà không có lease `operator_device_lock`.

**Sai lầm nghiêm trọng của Coordinator:**
Thay vì chủ động giải quyết xung đột bằng cách bọc lệnh ADB qua cơ chế lock được phép, Coordinator lại đi giải thích lý do cho Operator: *"Lệnh screencap bị Guard chặn nên không gửi ảnh được"*.
Operator phản ứng gay gắt: *"Sao đéo fix đi! Chứ gate yêu cầu media mà bị chặn bởi gate khác nhảm lồn à"*.

## 2. Nguyên Tắc Cốt Lõi: Gate Không Được Triệt Tiêu Nhau (Anti-Deadlock)
- **CẤM TUYỆT ĐỐI** dùng Guard này làm lý do vi phạm Gate khác, rồi báo cáo văn bản trần thuật thay cho bằng chứng.
- Khi gặp xung đột giữa Gate Media (yêu cầu ảnh) và Guard Bulkhead (yêu cầu lock):
  Coordinator BẮT BUỘC phải thực thi lệnh chụp thông qua wrapper được miễn trừ (exempt wrapper) đã tích hợp sẵn `operator_device_lock`.

## 3. Quy Chuẩn Wrapper Nghiệm Thu: `with_device_lock.py`
Guard `guard_device_bulkhead.py` đã quy định allowlist cho wrapper:
`python D:/Taadaa/tools/with_device_lock.py --machine <M> -- <CMD>`

### Cấu trúc thực thi chuẩn:
```python
# tools/with_device_lock.py
with operator_device_lock(
    machine=args.machine,
    serial=serial,
    force_preempt=args.force_preempt,
    timeout=args.timeout,
    project="with_device_lock",
):
    # Thực thi lệnh ADB trong phạm vi lease hợp lệ
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    sys.stdout.buffer.write(res.stdout)
    sys.exit(res.returncode)
```

### Lệnh chụp ảnh nghiệm thu không bị Guard chặn:
```bash
python D:/Taadaa/tools/with_device_lock.py --machine 7 -- adb -s 9885f63030454d3055 exec-out screencap -p > D:/Taadaa/reports/m7_screen.png
```

## 4. WinRT OCR Trên Windows (Tránh AggregateException)
Khi kiểm tra ảnh nghiệm thu qua WinRT OCR (`ocr_boxes.ps1`):
- **Bắt buộc dùng Windows path với backslash (`\`):** `D:\Taadaa\reports\screen.png`.
- Dùng POSIX path (`/`) sẽ khiến `StorageFile::GetFileFromPathAsync` trả về null, gây chuỗi lỗi `AggregateException` / `NullReferenceException` trong PowerShell.
