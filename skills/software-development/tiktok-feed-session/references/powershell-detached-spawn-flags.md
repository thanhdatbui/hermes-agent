# Quy tắc cờ tiến trình PowerShell Detached Spawn trên Windows (Hermes Cron)

## Bối cảnh
Khi Hermes Cron hoặc Python wrapper (`tiktok_runner.py`) spawn tiến trình launcher nền (`run-feed-session.ps1`) trên Windows, tiến trình cần chạy detached/background độc lập để không block cron tick và không bị terminate khi cha thoát.

## Cạm bẫy & Lỗi nghiêm trọng (DETACHED_PROCESS)
- `DETACHED_PROCESS = 0x00000008` (hoặc `0x00000208` khi kết hợp `CREATE_NEW_PROCESS_GROUP = 0x00000200`) khiến `powershell.exe` **tự động thoát / chết ngay lập tức (instant termination)**.
- **Nguyên nhân:** PowerShell 5.1 (`powershell.exe`) trên Windows yêu cầu một console host hợp lệ để khởi tạo console subsystem. Khi set `DETACHED_PROCESS`, console bị ngắt hoàn toàn khiến runtime console của PowerShell crash hoặc exit 0 ngay từ đầu, không kịp gọi sang `python.exe run_tiktok.py`.

## Chuẩn giải pháp (CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP)
Sử dụng cờ kết hợp:
```python
if sys.platform == "win32":
    popen_kwargs["creationflags"] = 0x08000200  # CREATE_NEW_PROCESS_GROUP (0x200) | CREATE_NO_WINDOW (0x8000000)
else:
    popen_kwargs["start_new_session"] = True
```

- `CREATE_NO_WINDOW (0x08000000)`: Chạy ẩn không hiện cửa sổ command prompt, nhưng vẫn cho phép PowerShell phân bổ console subsystem nội bộ hợp lệ.
- `CREATE_NEW_PROCESS_GROUP (0x00000200)`: Tạo process group độc lập để quản lý tín hiệu và ngắt vòng đời độc lập với tiến trình cha.
