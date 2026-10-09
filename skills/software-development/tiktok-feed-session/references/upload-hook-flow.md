# Upload Hook Architecture & Direct Trigger (--allow-upload-hook)

## Context & Problem
Trước đây (khi còn picker / cohort system), upload hook được gate chặt chẽ bởi:
1. `_effective_session_index(child_ctx.config) == 2` (trong `multi_machine_feed_session.py` vòng lặp runner)
2. `session_index == 2` (Gate 1 trong `_run_upload_hook`)
Giá trị `session_index` được cohort manifest set (`0, 1, 2` tương ứng Session 1, 2, 3 của ca).

Khi cohort manifest bị deprecated/loại bỏ, runner không còn gán `_session_index` (hoặc luôn bằng None/0), dẫn tới upload hook luôn bị skip với lý do `missing-session-identity` hoặc `not-final-session`.

## Architecture Flow (--allow-upload-hook)
Để cho phép mỗi ca feed xong tự động đăng video nếu có video sẵn (không phụ thuộc cohort / session_index):

### 1. CLI Entry (`python_runner/run_tiktok.py`)
- Argument:
  ```python
  parser.add_argument(
      "--allow-upload-hook",
      action="store_true",
      default=False,
      help="Enable upload hook after feed session",
  )
  ```
- Config setup:
  ```python
  config["_allow_upload_hook"] = bool(args.allow_upload_hook)
  ```

### 2. Multi-Machine Flow (`flows/multi_machine_feed_session.py`)
- Caller gate:
  ```python
  if _effective_session_index(child_ctx.config) == 2 or child_ctx.config.get("_allow_upload_hook"):
      ...
      upload_res = _run_upload_hook(ctx, account, child_ctx, child_result)
  ```
- Hook Gate 1:
  ```python
  allow_hook = bool(ctx.config.get("_allow_upload_hook"))
  if session_index != 2 and not allow_hook:
      payload = {
          "machine": account.machine,
          "row": account.account_row_index,
          "status": "skipped",
          "reason": "not-final-session" if session_index else "missing-session-identity",
          "session_index": session_index or None,
      }
      _write_upload_result(child_ctx, payload)
      return payload
  ```

### 3. PowerShell Orchestrator (`scripts/run-feed-session.ps1`)
- Param: `[switch]$AllowUploadHook`
- Argument array forwarding:
  ```powershell
  if ($AllowUploadHook) {
      $arguments += "--allow-upload-hook"
  }
  ```

### 4. Hermes Cron Wrapper (`C:\Users\Kibe\AppData\Local\hermes\scripts\tiktok_runner.py`)
- Thêm `-AllowUploadHook` vào danh sách arguments gọi PowerShell trong `_spawn_feed_session()`.
