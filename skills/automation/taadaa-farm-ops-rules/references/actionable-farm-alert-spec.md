# Actionable Farm Alert Specification

## 1. Problem Statement
Khi Watchdog hoặc người vận hành gửi tin nhắn cảnh báo dạng văn bản tự do (ví dụ: `🚨 [MÁY 42] DỪNG PHIÊN - unknown TikTok state`), Agent có xu hướng tự động dùng `grep -rn` hoặc `search_files` quét mã nguồn để định vị nơi sinh ra chuỗi lỗi, gây tốn thời gian, timeout và vi phạm nghiêm trọng Farm Safety Rules.

## 2. Actionable Farm Alert Payload Standard
Mọi cảnh báo gửi tới Agent qua Telegram / Gateway BẮT BUỘC tuân thủ format đóng gói sẵn hành động (Actionable Command Contract):

```text
🚨 [FARM ALERT: MÁY <N>] DỪNG PHIÊN
• Máy: <N> | Serial: <SERIAL> | Nick: <ACCOUNT>
• Triệu chứng: <SHORT_DESCRIPTION>

📋 BẮT BUỘC THỰC THI (KHÔNG GREP / KHÔNG TÌM KIẾM):
1. Lệnh lấy hiện trường: python D:/Taadaa/tools/inspect_machine.py <N>
2. File flow phụ trách: D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/<flow_file>.py
3. File log run: D:/Taadaa/tiktok-luot nuoi acc/.ai-runs/latest/summary.txt
4. Lệnh canary test lại máy <N>:
powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row <ROW> -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
```

## 3. Agent Execution Contract (5-Step Gate)
1. **Bước 1 (Inspect):** Thực thi ngay `python D:/Taadaa/tools/inspect_machine.py <N>` để lấy focus app, live ADB screenshot, và run log gần nhất.
2. **Bước 2 (Evaluate):** Đọc trực tiếp screenshot live và log summary được chỉ định.
3. **Bước 3 (Patch):** Mở đích danh file flow trong alert, dispatch worker chỉnh sửa selector / recovery logic (nếu kẹt UI mới).
4. **Bước 4 (Canary Test):** Thực thi lệnh Canary test máy <N> đã đóng gói trong alert.
5. **Bước 5 (Report):** Báo cáo kết quả gọn gàng (Success/Fail) vào nhóm.
