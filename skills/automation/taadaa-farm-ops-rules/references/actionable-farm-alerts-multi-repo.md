# Actionable Farm Alerts Multi-Repo Standard

## Mục tiêu
Loại bỏ hoàn toàn phản xạ quét đĩa bừa bãi (`os.walk`, `glob`, `find`, `grep -rn`) khi nhận cảnh báo dừng máy `[MÁY N]` trên Phone Farm 160 máy.
Mỗi alert bắn về nhóm Telegram Farm Alerts bắt buộc phải là một **Actionable Payload** chứa sẵn lệnh trích xuất, đường dẫn file code phụ trách, file log và lệnh canary test riêng cho từng repo/workflow.

## 1. Chuẩn Function Signature (`automation_core.alerts`)
```python
def send_farm_machine_alert(
    machine: int,
    serial: str,
    *,
    script_name: str,
    account: str,
    error_reason: str,
    status_text: str = "ĐANG MỞ",
    adb_path: str = r"C:\Program Files (x86)\xiaowei\tools\adb.exe",
    chat_id: str = DEFAULT_ALERT_CHAT_ID,
    flow_file: str = "",
    log_path: str = "",
    canary_cmd: str = "",
) -> bool:
```

## 2. Bảng Mapping Actionable Alert Theo Từng Repo / Workflow

| Workflow / Repo | `script_name` | `flow_file` | `log_path` | `canary_cmd` |
| :--- | :--- | :--- | :--- | :--- |
| **Lướt Feed** (`tiktok-luot nuoi acc`) | `multi-machine-feed-session` | `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py` | `D:/Taadaa/tiktok-luot nuoi acc/.ai-runs/latest/summary.txt` | `powershell -File ".../run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run` |
| **Tự Động Follow** (`tiktok-follow`) | `tiktok-follow` | `D:/Taadaa/tiktok-follow/follow_runner/flows/follow_engine.py` | `D:/Taadaa/tiktok-follow/follow_runner/runs/latest/summary.txt` | `powershell -File ".../run-follow.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run` |
| **Upload Video** (`Tiktok-video`) | `tiktok-video` | `D:/Taadaa/Tiktok-video/scripts/tiktok_workflow/run_post.py` | `D:/CodexRuntime/tiktok-video/runs` | `python -m scripts.tiktok_workflow --config "<cfg>" --workflow-workbook "<wb>" --single-device <serial> --video-number <num> --no-dry-run` |
| **Đăng Ký Acc** (`Tiktok_Reg`) | `Tiktok_Reg` | `D:/Taadaa/Tiktok_Reg/social_reg_v1.py` | `D:/Taadaa/Tiktok_Reg/social_reg_log.txt` | `python social_reg_v1.py <STT> --ss --email <mail>` |
| **Bật 2FA** (`tiktok-add-bao-mat-f2a`) | `tiktok-add-2fa` | `D:/Taadaa/tiktok-add-bao-mat-f2a/python_runner/run_batch_live_2fa.py` | `D:/Taadaa/tiktok-add-bao-mat-f2a/runtime/kibe/reports` | `python python_runner/run_batch_live_2fa.py --live --limit 1` |

## 3. Quy Trình 4 Bước Cho Agent Khi Nhận Alert
1. **B1**: Chạy ngay `python D:/Taadaa/tools/inspect_machine.py <N>` để nắm hiện trường thật từ thiết bị.
2. **B2**: Đọc trực tiếp `flow_file` và `log_path` được chỉ định đích danh trong tin nhắn alert.
3. **B3**: Viết code auto-recovery vào file flow + chạy focused unit test (<30s).
4. **B4**: Chạy `canary_cmd` để chứng minh máy đã tự vượt qua lỗi và nhả lock an toàn.
