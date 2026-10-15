# Windows Startup Auto-Resume Heuristic Hook

## Bối cảnh & Vấn đề
- Trước đây, cơ chế `preserve_in_flight_sessions` (gắn cờ `resume_pending = true` vào SQLite `gateway_routing`) chỉ được gọi bên trong `farm_preflight_daily_reset.py` — tức là chỉ kích hoạt khi hệ thống reboot theo lịch cron tự động (ca 05:20, 11:20, 17:20).
- Nếu User **tự bấm Restart Windows bằng tay**, **tắt nóng**, hoặc **máy sập nguồn đột ngột**, script reset không kịp chạy -> cờ `resume_pending` không được gắn.
- Khi máy bật lại, Hermes Gateway khởi động lên thấy không có cờ nên nằm im, không đánh thức agent tiếp tục các tác vụ đang dở dang (ví dụ subagent/worker đang chạy ngầm).

## Giải pháp: Startup Heuristic (Hook khởi động ưu tiên cao nhất)
Thay vì cố gắng bắt sự kiện shutdown (dễ bị bỏ sót khi sập nguồn hoặc tắt cưỡng bức), giải pháp tối ưu là **phát hiện và bù cờ ngay khi Windows vừa boot lên**, trước khi Gateway kết nối.

### 1. File hook VBS trong Windows Startup
- Đường dẫn: `C:\Users\Kibe\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\00_Hermes_AutoResume_Hook.vbs`
- Tiền tố `00_` đảm bảo Windows luôn khởi chạy script này trước các tiến trình khác trong thư mục Startup (bao gồm cả `Hermes_Gateway.vbs`).

```vbscript
' 00_Hermes_AutoResume_Hook.vbs
Option Explicit
Dim sh
Set sh = CreateObject("WScript.Shell")
' Chay an (windowStyle=0, bWaitOnReturn=True de dam bao xong truoc khi Gateway len)
sh.Run "python ""D:\Taadaa\tools\auto_resume_startup_hook.py""", 0, True
```

### 2. Script logic Python (`auto_resume_startup_hook.py`)
- Đường dẫn: `D:/Taadaa/tools/auto_resume_startup_hook.py`
- Quét SQLite `gateway_routing` trong vòng `lookback_minutes = 60` phút gần nhất.
- Điều kiện đánh dấu: Session có tin nhắn cuối cùng là `user` hoặc `tool` (tức là lệnh chưa có câu chốt phản hồi từ `assistant`).
- Gán cờ:
  ```json
  {
    "resume_pending": true,
    "resume_reason": "startup_unresolved_recovery",
    "last_resume_marked_at": "<ISO_TIMESTAMP>"
  }
  ```

### 3. Vòng đời đánh thức của Gateway
1. Máy boot -> `00_Hermes_AutoResume_Hook.vbs` chạy trong 0.05s, gắn cờ `resume_pending` cho các session bị ngắt.
2. `Hermes_Gateway.vbs` boot -> đọc SQLite thấy `resume_pending = true` -> tự động phát sinh wake-up turn vào đúng channel/topic Telegram.
3. Coordinator tỉnh dậy, đọc context gần nhất và tự động nối lại công việc mà User không cần nhắc tay.
