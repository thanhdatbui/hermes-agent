# Actionable Farm Alert Contract & Architecture

## 1. Cấu trúc Actionable Alert Contract (chuẩn hóa 2026-09-03)
Khi bất kỳ script nào trên Farm (Feed, Follow, Reg, 2FA...) phát sinh lỗi dừng máy, alert gửi về Telegram group BẮT BUỘC dùng format Actionable Payload phát sinh từ `automation_core.alerts.send_farm_machine_alert`:

```text
🚨 [FARM ALERT: MÁY <N>] DỪNG PHIÊN
• Máy: <N> | Serial: <serial> | Nick: <account>
• Triệu chứng: <error_reason>

📋 BẮT BUỘC THỰC THI (KHÔNG GREP / KHÔNG TÌM KIẾM):
1. Lệnh lấy hiện trường: python D:/Taadaa/tools/inspect_machine.py <N>
2. File flow phụ trách: <đường dẫn file flow cụ thể>
3. File log run: <đường dẫn file log summary cụ thể>
4. Lệnh canary test lại máy <N>:
<lệnh powershell hoặc python canary test cụ thể>
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
