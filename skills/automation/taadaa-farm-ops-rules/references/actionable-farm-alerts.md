# Actionable Farm Alerts Specification & Mapping Guide

## 1. Nguyên tắc cốt lõi
- Mọi cảnh báo dừng phiên bắn về Telegram nhóm **Farm Alerts** (`send_farm_machine_alert` từ `automation_core.alerts`) bắt buộc phải ở định dạng **Actionable Alert**.
- Actionable Alert cung cấp sẵn 4 dòng thực thi đích danh để Hermes Agent vào việc ngay mà **KHÔNG BAO GIỜ** dùng `grep`, `find`, `os.walk` hay quét đĩa.

## 2. Chuẩn Function Signature (`automation_core.alerts`)
```python
from automation_core.alerts import send_farm_machine_alert

send_farm_machine_alert(
    machine=42,
    serial="ce06160692e07d0404",
    script_name="<tên script>",
    account="<tên nick/email>",
    error_reason="<triệu chứng lỗi>",
    status_text="GIỮ HIỆN TRƯỜNG ...",
    adb_path=r"C:\Program Files (x86)\xiaowei\tools\adb.exe",
    flow_file=r"<đường dẫn file flow code chịu trách nhiệm>",
    log_path=r"<đường dẫn file/folder log run>",
    canary_cmd=r"<lệnh canary test lại máy thật>",
)
```

## 3. Bảng Mapping Chuẩn Toàn Farm

| Script Name | Subsystem / Repo | `flow_file` | `log_path` | `canary_cmd` |
| :--- | :--- | :--- | :--- | :--- |
| `multi-machine-feed-session` | Lướt nuôi nick (`tiktok-luot nuoi acc`) | `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py` | `D:/Taadaa/tiktok-luot nuoi acc/.ai-runs/latest/summary.txt` | `powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines {machine} -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run` |
| `tiktok-follow` | Follow tự động (`tiktok-follow`) | `D:/Taadaa/tiktok-follow/follow_runner/flows/follow_engine.py` | `D:/Taadaa/tiktok-follow/follow_runner/runs/latest/summary.txt` | `powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-follow\scripts\run-follow.ps1" -Machines {machine} -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run` |
| `tiktok-video` | Upload video (`Tiktok-video`) | `D:/Taadaa/Tiktok-video/scripts/tiktok_workflow/run_post.py` | `D:/CodexRuntime/tiktok-video/runs` | `python -m scripts.tiktok_workflow --config "<config_file>" --workflow-workbook "<workbook_path>" --single-device {serial} --video-number {next_video} --no-dry-run` |
| `Tiktok_Reg` | Đăng ký tài khoản (`Tiktok_Reg`) | `D:/Taadaa/Tiktok_Reg/social_reg_v1.py` | `D:/Taadaa/Tiktok_Reg/social_reg_log.txt` | `python social_reg_v1.py {stt} --ss --email {email}` |
| `tiktok-add-2fa` | Bật bảo mật 2FA (`tiktok-add-bao-mat-f2a`) | `D:/Taadaa/tiktok-add-bao-mat-f2a/python_runner/run_batch_live_2fa.py` | `D:/Taadaa/tiktok-add-bao-mat-f2a/runtime/kibe/reports` | `python python_runner/run_batch_live_2fa.py --live --limit 1` |

## 4. Định dạng Output Telegram
```text
🚨 [FARM ALERT: MÁY {machine}] DỪNG PHIÊN
• Máy: {machine} | Serial: {serial} | Nick: {account}
• Triệu chứng: {error_reason}

📋 BẮT BUỘC THỰC THI (KHÔNG GREP / KHÔNG TÌM KIẾM):
1. Lệnh lấy hiện trường: python D:/Taadaa/tools/inspect_machine.py {machine}
2. File flow phụ trách: {flow_file}
3. File log run: {log_path}
4. Lệnh canary test lại máy {machine}:
{canary_cmd}
```
