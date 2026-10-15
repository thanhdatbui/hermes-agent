# Windows Startup Auto-Resume Hook cho Hermes Gateway (Manual Restart & Power Loss)

## 1. Vấn đề cốt lõi
- **Hạn chế của preflight:** Hàm `preserve_in_flight_sessions` (gắn cờ `resume_pending = true`) trước đây chỉ được gọi bên trong script preflight `farm_preflight_daily_reset.py`. Script này chỉ chạy khi hệ thống tự động reboot theo lịch cron 3 ca (05:20, 11:20, 17:20).
- **Hệ quả khi reboot tay:** Khi User bấm Restart bằng tay trong Windows, hoặc máy sập nguồn/crash/Windows Update, preflight không được kích hoạt -> Không có session nào được gắn cờ `resume_pending` -> Khi Gateway khởi động lại, bot nằm im chờ tin nhắn mới, làm đứt đoạn các phiên làm việc dài hoặc các tác vụ đang dở dang.

---

## 2. Kiến trúc giải pháp: Startup Hook Heuristic (Khởi động ưu tiên cao nhất)

Thay vì cố gắng bắt sự kiện shutdown của Windows (dễ bị bỏ sót khi sập nguồn hoặc tắt nóng), giải pháp là đặt một Hook ngay tại thời điểm Windows khởi động (`Windows Startup`):

### Tệp thực thi:
1. **`00_Hermes_AutoResume_Hook.vbs`** đặt tại:
   `C:\Users\Kibe\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\00_Hermes_AutoResume_Hook.vbs`
   - Tiền tố `00_` đảm bảo Windows luôn ưu tiên chạy tệp này đầu tiên trước tất cả các tệp `.vbs` khác trong thư mục Startup (đặc biệt là trước `Hermes_Gateway.vbs`).
   - Nội dung VBS:
     ```vbscript
     Option Explicit
     Dim sh
     Set sh = CreateObject("WScript.Shell")
     On Error Resume Next
     sh.Run "python ""D:\Taadaa\tools\auto_resume_startup_hook.py""", 0, True
     Set sh = Nothing
     ```
   - Chạy đồng bộ (`True`) để đảm bảo quá trình quét và đánh dấu hoàn tất 100% trước khi Hermes Gateway thức dậy.

2. **`D:\Taadaa\tools\auto_resume_startup_hook.py`**:
   - Gọi hàm `preserve_in_flight_sessions(lookback_minutes=60)` từ `farm_preflight_daily_reset.py`.
   - Quét CSDL `storage.sqlite` / `gateway_routing` của Hermes:
     * Lọc các session Telegram hoạt động trong vòng 60 phút gần nhất (dựa trên `MAX(timestamp)` từ bảng `messages`).
     * Kiểm tra tin nhắn cuối cùng (`active = 1`): Nếu là `user`, `tool`, hoặc `assistant` có `tool_calls` dở dang -> Tự động gắn cờ `resume_pending = true` và `resume_reason = "restart_interrupted"`.
     * Nếu tin nhắn cuối là `assistant` đã trả lời xong -> Bỏ qua để tránh spam tin nhắn vào Telegram.

---

## 3. Luồng vận hành hoàn chỉnh

```text
[User bấm Restart tay / Sập nguồn / Crash]
                   │
                   ▼
     [Windows đăng nhập & chạy Startup]
                   │
                   ▼ (Ưu tiên số 1)
       00_Hermes_AutoResume_Hook.vbs
                   │ (Chạy auto_resume_startup_hook.py)
                   ▼
  Quét SQLite -> Gắn cờ resume_pending = true cho session dở
                   │ (Hoàn tất trong ~0.05s)
                   ▼ (Ưu tiên tiếp theo)
          Hermes_Gateway.vbs
                   │
                   ▼
   Gateway boot -> Đọc thấy resume_pending
                   │
                   ▼
  [Tự động đánh thức Agent vào Telegram chat tiếp tục công việc!]
```
