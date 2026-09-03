# Quy Trình Actionable Farm Alert & Phân Vai Coordinator vs Worker (2026-09-03)

## 1. Phân Vai Bắt Buộc: Coordinator vs Worker Subagent
- **Session Chính (Coordinator):**
  - Đóng vai trò chỉ huy: Đọc log, inspect hiện trường máy N qua `python D:/Taadaa/tools/inspect_machine.py <N>`.
  - Phân tích nguyên nhân gốc rễ (Root Cause), lập implementation plan.
  - **BẮT BUỘC gọi `delegate_task(role='leaf')`** để giao toàn bộ việc đọc chi tiết codebase, sửa file, viết test cho worker subagent.
  - Sau khi worker hoàn tất, Coordinator chạy lại Canary verification và chốt phiên qua 6 Gate.
  - **TUYỆT ĐỐI CẤM Coordinator tự dùng `write_file`, `patch` hoặc `terminal` sửa code trực tiếp trên session chính** (làm phình to context window và vi phạm phân vai).

## 2. Invariant Cấm Bấm Tay ADB Chữa Cháy
- **TUYỆT ĐỐI CẤM** chạy `adb shell input tap`, `input keyevent`, `input swipe` để "bấm qua" màn hình lỗi hoặc giải cứu thiết bị tạm thời.
- Máy bị lỗi là **HIỆN TRƯỜNG** để reproduce lỗi, trích xuất UI XML và viết handler tự động vào codebase (`python_runner` / `automation-core`) để toàn bộ 160 máy tự vượt qua khi vận hành thật.

## 3. Quy Chuẩn Actionable Farm Alert Payload (Đa Script)
Mọi script / pipeline khi gặp sự cố trên máy N (Feed, Follow, Upload Video, Reg, 2FA...) đều phải gọi `automation_core.alerts.send_farm_machine_alert` với đầy đủ 4 tham số động:

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

### Danh mục tham số theo từng Script:
| Script / Repo | `flow_file` | `log_path` | `canary_cmd` |
| :--- | :--- | :--- | :--- |
| **Feed Nuôi Acc** (`tiktok-luot nuoi acc`) | `.../flows/feed_swipe_smoke.py` | `.../.ai-runs/latest/summary.txt` | `powershell -File ".../run-feed-session.ps1" -Machines {N} -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run` |
| **Follow Tự Động** (`tiktok-follow`) | `.../flows/follow_engine.py` | `.../runs/latest/summary.txt` | `powershell -File ".../run-follow.ps1" -Machines {N} -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run` |
| **Upload Video** (`Tiktok-video`) | `.../scripts/tiktok_workflow/run_post.py` | `D:/CodexRuntime/tiktok-video/runs` | `python -m scripts.tiktok_workflow --config "..." --workflow-workbook "..." --single-device {serial} --video-number {video} --no-dry-run` |
| **Đăng Ký Nick** (`Tiktok_Reg`) | `D:/Taadaa/Tiktok_Reg/social_reg_v1.py` | `D:/Taadaa/Tiktok_Reg/social_reg_log.txt` | `python social_reg_v1.py {stt} --ss --email {email}` |
| **Bật 2FA** (`tiktok-add-bao-mat-f2a`) | `.../python_runner/run_batch_live_2fa.py` | `.../runtime/kibe/reports` | `python python_runner/run_batch_live_2fa.py --live --limit 1` |
