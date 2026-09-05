# Farm Alert Actionable Payload — Template & Mapping

## Problem
LLM Agent khi nhận farm alert dạng cũ (`[MÁY N] DỪNG PHIÊN` với triệu chứng mơ hồ) sẽ bị kích hoạt reflex `grep -rn` / `search_files` quét diện rộng để tìm chuỗi lỗi trong codebase → vi phạm quy tắc farm safety.

## Solution
Alert phải chứa sẵn **4 thông tin điều hướng** để Agent thực thi ngay, không cần tìm kiếm:
1. Lệnh inspect hiện trường
2. File flow phụ trách
3. File log run
4. Lệnh canary test lại máy

## Template Alert Chuẩn
```text
🚨 [FARM ALERT: MÁY {machine}] DỪNG PHIÊN
• Quy trình / Script: {process_name} ({repo_name})
• Máy: {machine} | Serial: {serial} | Nick: {account}
• Triệu chứng: {error_reason}
• Hiện trường: ĐANG MỞ

📋 BẮT BUỘC THỰC THI (5 BƯỚC RECOVERY - CẤM ADB TAY / CẤM QUÉT ĐĨA):
1. B1 (Inspect): python D:/Taadaa/tools/inspect_machine.py {machine}
2. B2 (Root Cause): Đọc log run ({log_path}) & mở flow ({flow_path})
3. B3 (Patch Code): SỬA CODEBASE trong repo để script tự xử lý lỗi (CẤM gõ lệnh ADB ngoài chữa ngọn)
4. B4 (Canary Test): Chạy lệnh kiểm chứng thực tế:
   {canary_cmd}
5. B5 (Closeout): Báo cáo diff code + kết quả canary
```

## Code Mapping per Repo

### tiktok-luot nuoi acc (Feed Session)
- **flow_file**: `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py`
- **log_path**: `D:/Taadaa/tiktok-luot nuoi acc/.ai-runs/latest/summary.txt`
- **canary_cmd**: `powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines {machine} -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run`

### tiktok-follow
- **flow_file**: `D:/Taadaa/tiktok-follow/follow_runner/flows/follow_engine.py`
- **log_path**: `D:/Taadaa/tiktok-follow/follow_runner/runs/latest/summary.txt`
- **canary_cmd**: `powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-follow\scripts\run-follow.ps1" -Machines {machine} -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run`
- **Note**: Script `run-follow.ps1` chưa tồn tại → cần tạo hoặc dùng `python -m follow_runner.run_follow --machine {machine} --config config.yaml --account-row-index 1 --skip-identity-verify`

### Tiktok_Reg
- **flow_file**: `D:/Taadaa/Tiktok_Reg/scripts/run_night_chain_pipeline.py`
- **log_path**: `D:/Taadaa/runtime/kibe/artifacts/runs/social-batch-all/latest/all_results.json`
- **canary_cmd**: `python D:/Taadaa/Tiktok_Reg/_run_all_targets.py`

### tiktok-add-2fa (tiktok-add-bao-mat-f2a)
- **flow_file**: `D:/Taadaa/tiktok-add-bao-mat-f2a/python_runner/flows/...`
- **log_path**: `D:/Taadaa/tiktok-add-bao-mat-f2a/.ai-runs/latest/summary.txt`
- **canary_cmd**: `powershell ...`

## Implementation Point
`automation_core/src/automation_core/alerts.py` → function `send_farm_machine_alert()` accepts 3 new kwargs:
- `flow_file: str = ""`
- `log_path: str = ""`
- `canary_cmd: str = ""`

Each script that calls `send_farm_machine_alert()` MUST pass its own flow/log/canary paths.

## Pitfall: Large File Patching
File `multi_machine_feed_session.py` (4834 lines, 483KB) has 7 call sites for `send_farm_machine_alert()` with `script_name="tiktok-follow"`. Patching via `patch` tool on such a large file easily introduces indentation errors. Use `execute_code` with Python `read_file`/`write_file` or delegate to a subagent for bulk changes on large files.

## Pitfall: build/ vs src/ Sync
`D:/Taadaa/automation-core/build/lib/automation_core/alerts.py` must be updated alongside `src/`. After editing `src/`, run `pip install -e .` from the repo root to sync.
