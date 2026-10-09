# Clean Python Environment Execution for Canary / Feed Session

## Vấn đề gặp phải (PIL _imaging Collision)
Khi chạy các lệnh Python hoặc PowerShell automation từ terminal trong phiên Hermes Agent:
* Hermes Agent tự động cấu hình hoặc inject biến môi trường:
  * `PYTHONPATH=C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages`
  * `VIRTUAL_ENV=...`
* Điều này khiến bất kỳ lời gọi Python nào (kể cả Python 3.12 hệ thống) ưu tiên nạp các thư viện C-extension từ venv của Hermes Agent trước. Kết quả là lỗi runtime:
  `ImportError: cannot import name '_imaging' from 'PIL'`
  hoặc thiếu các gói của farm như `automation-core`, `opencv-python-headless`.

## Môi trường Python chuẩn của Farm Taadaa
* **Python executable:** `C:\Users\Kibe\AppData\Local\Programs\Python\Python312\python.exe`
* Đã cài đặt sẵn và tương thích hoàn toàn:
  * `automation-core 0.4.45` (từ `D:\Taadaa\automation-core`)
  * `pillow 12.2.0`
  * `opencv-python-headless`
  * `openpyxl`, `tzdata`, v.v.

## Cách chạy chuẩn (PowerShell)
Luôn dọn sạch `PYTHONPATH` và `VIRTUAL_ENV` trước khi gọi script, đồng thời truyền tường minh tham số `-Python`:

```powershell
$env:PYTHONPATH = ""
$env:VIRTUAL_ENV = ""
powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" `
    -Machines <MACHINE_ID> `
    -Row 1 `
    -RecoveryTestSwipes 2 `
    -SkipAccountWorkbookSync `
    -Python "C:\Users\Kibe\AppData\Local\Programs\Python\Python312\python.exe" `
    -Run
```

## Chụp ảnh kiểm chứng sau Canary Test
```bash
adb -s <DEVICE_SERIAL> exec-out screencap -p > C:/Users/Kibe/AppData/Local/hermes/cache/images/may<N>_canary_verified.png
```
