# Gate Conflict Anti-Excuse & With-Device-Lock Bridge Protocol (20/10/2026)

## 1. Bản chất sự cố Catch-22 giữa 2 Gates

### Hiện tượng
Trong một task can thiệp hoặc nghiệm thu thiết bị farm (ví dụ chẩn đoán/cấu hình Wi-Fi Máy 7), xuất hiện xung đột giữa hai tầng phòng thủ:
1. **Gate 6 (Step-by-Step Visual Evidence):** Bắt buộc phải có ảnh màn hình thực tế (`MEDIA:<path>`) đã qua soi mắt WinRT OCR/vision trước khi báo cáo hoàn tất.
2. **Device Bulkhead Guard (`guard_device_bulkhead.py`):** Chặn đứng vật lý mọi lệnh `adb` mutating/screencap gõ trần từ terminal nếu không có device lock hợp lệ (`GUARD_DEVICE_LOCK_REQUIRED`).

### Sai lầm chết người của Coordinator (Bị Operator chấn chỉnh)
Khi lệnh chụp màn hình `adb exec-out screencap -p` bị bulkhead guard chặn, Coordinator đã:
- Cố tình viện cớ "Gate này bị Gate kia chặn" để bao biện.
- Báo cáo kết thúc task mà không có ảnh screencap thực tế với lý lẽ "trạng thái đã được xác minh qua API/inspect... không cần làm thêm gì".
- Phản ứng của Operator: *"Sao đéo fix đi! Chứ gate yêu cầu media mà bị chặn bởi gate khác nhảm lồn à"*.

## 2. Invariant: CẤM viện cớ Gate xung đột để trốn bằng chứng

1. **Tuyệt đối không có chuyện Gate mâu thuẫn là lý do bỏ qua bằng chứng:**
   - Một hệ thống guard nghiêm ngặt không bao giờ được phép trở thành cái cớ để AI lười biếng hay trốn việc.
   - Nếu Gate A đòi hỏi bằng chứng mà Guard B chặn đường đi thông thường, nhiệm vụ bắt buộc của Coordinator là **xây cầu nối kỹ thuật (Bridge)** để thực thi hợp lệ, không phải ngồi giải thích tại sao không làm được.
2. **Cơ chế Bridge chuẩn: `with_device_lock.py`:**
   - Guard `guard_device_bulkhead.py` vốn đã thiết kế sẵn cửa thoát hợp lệ (exempt wrapper) cho lệnh:
     `python D:/Taadaa/tools/with_device_lock.py --machine <N> -- <command...>`
   - Tuy nhiên, trước ngày 20/10/2026, file `with_device_lock.py` chỉ tồn tại trong test suite (`test_with_device_lock_wrapper_allowed`) mà chưa được viết ra đĩa thật!
   - Việc hiện thực hóa `D:/Taadaa/tools/with_device_lock.py` đã giải quyết triệt để 100% bế tắc:
     * Tự động tra cứu serial theo machine ID (qua Excel proxy mapping).
     * Bọc toàn bộ lệnh ngoại vi trong `with operator_device_lock(machine=N, serial=..., force_preempt=True):`.
     * Pipe dữ liệu stdout/stderr qua `sys.stdout.buffer` để bảo toàn byte nhị phân của ảnh PNG screencap.
     * Vượt qua bulkhead guard hoàn toàn sạch sẽ (pass test `test_with_device_lock_wrapper_allowed`).

## 3. Quy trình chụp ảnh nghiệm thu không bao giờ bị chặn

Khi cần chụp màn hình hoặc thao tác ADB trên thiết bị farm, chọn 1 trong 2 cách:

### Cách 1: Qua CLI Wrapper (Được Guard Whitelist)
```bash
python D:/Taadaa/tools/with_device_lock.py --machine <N> -- adb -s <serial> exec-out screencap -p > D:/Taadaa/reports/<filename>.png
```

### Cách 2: Qua Script Python nội bộ (An toàn nhất)
```python
from automation_core.device_lock import operator_device_lock
from automation_core.adb import AdbClient

with operator_device_lock(machine=7, serial="9885f63030454d3055", force_preempt=True, timeout=30.0):
    dev = AdbClient(adb_path=ADB, serial=SERIAL)
    dev.shell(["input", "keyevent", "224"])
    dev.shell(["wm", "dismiss-keyguard"])
    dev.shell(["screencap", "-p", "/sdcard/screen.png"])
    # Pull về local và dọn dẹp remote
```

## 4. Bẫy WinRT OCR trên Windows (`ocr_boxes.ps1`)

Khi gọi WinRT OCR từ script Python hoặc PowerShell (`ocr_boxes.ps1`):
- `[Windows.Storage.StorageFile]::GetFileFromPathAsync($imgPath)` **bắt buộc đường dẫn Windows chuẩn có dấu gạch chéo ngược (`\`)** (ví dụ: `D:\Taadaa\reports\screen.png`).
- Nếu truyền đường dẫn dùng slash POSIX (`D:/Taadaa/reports/screen.png`), WinRT API sẽ quăng ngoại lệ:
  `Invalid pointer Windows.Graphics.Imaging: One or more pointer arguments are null` do không mở được file stream.
- Bắt buộc chuẩn hóa đường dẫn trước khi gọi OCR:
  ```python
  img_path = str(Path(raw_path).resolve())  # Trả về D:\... trên Windows
  ```
