# Actionable Farm Alert Contract & Architecture

## 1. Cấu trúc Actionable Alert Contract (chuẩn hóa 2026-09-03)
Khi bất kỳ script nào trên Farm (Feed, Follow, Reg, 2FA...) phát sinh lỗi dừng máy, alert gửi về Telegram group BẮT BUỘC dùng format Actionable Payload phát sinh từ `automation_core.alerts.send_farm_machine_alert`:

```text
🚨 [FARM ALERT: MÁY <N>] DỪNG PHIÊN
• Quy trình / Script: <process_name> (<repo_name>)
• Máy: <N> | Serial: <serial> | Nick: <account>
• Triệu chứng: <error_reason>
• Hiện trường: ĐANG MỞ

📋 BẮT BUỘC THỰC THI (5 BƯỚC RECOVERY - CẤM ADB TAY / CẤM QUÉT ĐĨA):
1. B1 (Inspect): python D:/Taadaa/tools/inspect_machine.py <N>
2. B2 (Root Cause): Đọc log run (<đường dẫn file log summary cụ thể>) & mở flow (<đường dẫn file flow cụ thể>)
3. B3 (Patch Code): SỬA CODEBASE trong repo để script tự xử lý lỗi (CẤM gõ lệnh ADB ngoài chữa ngọn)
4. B4 (Canary Test): Chạy lệnh kiểm chứng thực tế:
   <lệnh powershell hoặc python canary test cụ thể>
5. B5 (Closeout): Báo cáo diff code + kết quả canary
```

## 2. Quy tắc cho Agent khi nhận Alert
1. **Tuyệt đối không quét đĩa / grep mò mẫm**: Tin nhắn alert đã chứa sẵn file flow và log path. Không dùng `grep -rn`, `find`, `os.walk` hay `search_files` diện rộng.
2. **Quy trình 5 bước khép kín (Action Gate)**:
   - **B1**: Chạy ngay `python D:/Taadaa/tools/inspect_machine.py <N>` để chụp màn hình và kiểm tra focus activity.
   - **B2**: Soi ảnh chụp hiện trường và file log được chỉ định.
   - **B3**: Đọc đích danh file flow được chỉ định trong alert (`read_file`) để sửa code/selector.
   - **B4**: Chạy lệnh Canary verification được cung cấp trong alert (<30s).
   - **B5**: Báo cáo kết quả cuối gọn gàng (Success/Fail + chi tiết).

## 3. Quy tắc cho Developer / Subagent khi gọi `send_farm_machine_alert`:
Bắt buộc truyền đầy đủ 3 tham số ngữ cảnh động tương ứng với từng repo:
```python
from automation_core.alerts import send_farm_machine_alert

send_farm_machine_alert(
    machine=machine,
    serial=serial,
    script_name="tiktok-follow", # hoặc multi-machine-feed-session, tiktok-reg...
    account=account,
    error_reason=reason,
    status_text="GIỮ HIỆN TRƯỜNG",
    adb_path=adb_path,
    flow_file=r"D:/Taadaa/tiktok-follow/follow_runner/flows/follow_engine.py",
    log_path=r"D:/Taadaa/tiktok-follow/follow_runner/runs/latest/summary.txt",
    canary_cmd=f'powershell.exe -ExecutionPolicy Bypass -File "D:\\Taadaa\\tiktok-follow\\scripts\\run-follow.ps1" -Machines {machine} -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run',
)
```
