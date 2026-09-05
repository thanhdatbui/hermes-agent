# Actionable Farm Alert Specification

## 1. Problem Statement
Khi Watchdog hoặc người vận hành gửi tin nhắn cảnh báo dạng văn bản tự do (ví dụ: `🚨 [MÁY 42] DỪNG PHIÊN - unknown TikTok state`), Agent có xu hướng tự động dùng `grep -rn` hoặc `search_files` quét mã nguồn để định vị nơi sinh ra chuỗi lỗi, gây tốn thời gian, timeout và vi phạm nghiêm trọng Farm Safety Rules.

## 2. Actionable Farm Alert Payload Standard
Mọi cảnh báo gửi tới Agent qua Telegram / Gateway BẮT BUỘC tuân thủ format đóng gói sẵn hành động (Actionable Command Contract):

```text
🚨 [FARM ALERT: MÁY <N>] DỪNG PHIÊN
• Quy trình / Script: <process_name> (<repo_name>)
• Máy: <N> | Serial: <SERIAL> | Nick: <ACCOUNT>
• Triệu chứng: <SHORT_DESCRIPTION>
• Hiện trường: ĐANG MỞ

📋 BẮT BUỘC THỰC THI (5 BƯỚC RECOVERY - CẤM ADB TAY / CẤM QUÉT ĐĨA):
1. B1 (Inspect): python D:/Taadaa/tools/inspect_machine.py <N>
2. B2 (Root Cause): Đọc log run (D:/Taadaa/tiktok-luot nuoi acc/.ai-runs/latest/summary.txt) & mở flow (D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/<flow_file>.py)
3. B3 (Patch Code): SỬA CODEBASE trong repo để script tự xử lý lỗi (CẤM gõ lệnh ADB ngoài chữa ngọn)
4. B4 (Canary Test): Chạy lệnh kiểm chứng thực tế:
   powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts
un-feed-session.ps1" -Machines <N> -Row <ROW> -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
5. B5 (Closeout): Báo cáo diff code + kết quả canary
```

## 3. Agent Execution Contract (5-Step Gate)
1. **Bước 1 (Inspect):** Thực thi ngay `python D:/Taadaa/tools/inspect_machine.py <N>` để lấy focus app, live ADB screenshot, và run log gần nhất.
2. **Bước 2 (Evaluate):** Đọc trực tiếp screenshot live và log summary được chỉ định.
3. **Bước 3 (Patch):** Mở đích danh file flow trong alert, dispatch worker chỉnh sửa selector / recovery logic (nếu kẹt UI mới).
4. **Bước 4 (Canary Test):** Thực thi lệnh Canary test máy <N> đã đóng gói trong alert.
5. **Bước 5 (Report):** Báo cáo kết quả gọn gàng (Success/Fail) vào nhóm.
