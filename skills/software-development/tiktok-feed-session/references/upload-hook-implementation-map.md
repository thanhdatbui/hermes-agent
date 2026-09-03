# Upload Hook Implementation Map (_run_upload_hook) — 2026-08-19

Bản đồ code + trạng thái implement `_run_upload_hook` trong
`D:\Taadaa\tiktok-luot nuoi acc\python_runner\flows\multi_machine_feed_session.py`
(1469 dòng). Task đang DỞ (session bị network error giữa chừng — chưa implement, chưa viết test).

## Design doc chuẩn (đọc trước khi code)
- `tiktok-workbook-slot-mapping` → `references/feed-shift-upload-hook-pattern.md`:
  Preflight Gate fail-open/safe-skip (session gate, sensitive stop, workbook Tik, account ID,
  video render ready + integrity, time budget ≥30 phút), subprocess isolation, báo cáo 3 phần,
  parity date snapshot từ lúc bắt đầu ca (KHÔNG tính lại bằng `datetime.now()` ở phiên 3).

## Vị trí hàm trong file target (đã xác minh)
- `_run_follow_hook(ctx, account, child_ctx, child_result)` — dòng ~844. **Pattern để mirror**.
- `_write_follow_result(child_ctx, payload)` — dòng ~948 → ghi `follow_result.json` vào child artifact root.
- `_run_child` — dòng ~961; gọi follow hook tại ~1117:
  ```python
  if child_result.final_status in {"success", "degraded"}:
      try:
          _run_follow_hook(ctx, account, child_ctx, child_result)
      except Exception as exc:
          child_ctx.logger.log(...)  # hook fail KHÔNG chặn kết quả feed
  ```
- `_SENSITIVE_STOP_WORDS` — dòng ~835: login/otp/2fa/captcha/security/verify/verification/password/locked/banned/suspended.
- `MachineFeedSessionResult` dataclass — dòng ~429 (`as_dict()` mask serial/username).
- `_build_child_context` — dòng ~600; child artifact root = `ctx.artifacts.run_dir / "machines" / f"machine_{account.machine}"`.
- `prepare_multi_machine_feed_session` — dòng ~499; `_aggregate_rows` — dòng ~1180.

## Pattern follow hook (mirror cho upload)
- Subprocess thuần: `subprocess.run(command, capture_output=True, text=True, timeout=int(ctx.config.get("follow_timeout_seconds") or 900), cwd=r"D:\Taadaa\tiktok-follow")`.
- Đọc kết quả từ stdout prefix `FOLLOW_RESULT <json>` → update dict, `_write_follow_result`.
- `TimeoutExpired` → payload status="timeout", reason="follow-timeout", vẫn ghi result.
- Log: `child_ctx.logger.log(device_id=..., account=..., step="follow-hook", action="run_follow", result="ok"/"follow_failed", artifact_path=str(child_ctx.artifacts.run_dir), extra={...})`.
- Config keys follow: `follow_runner_path`, `follow_config_path`, `follow_timeout_seconds`, `python_exe`.

## Upload hook — thông số thiết kế
- Invocation (từ design doc):
  `python -m tiktok_workflow --config D:\Taadaa\Tiktok-video\config-machine-<M>.yaml --workflow-workbook <TikPath> --machine <M> --no-dry-run`
- Tik workbook path: `D:\OneDrive\TaadaaData\kibe\Tik{row_index}.xlsx` (**tik3.xlsx chữ thường**); sheet `TaiKhoan`.
  Cột dùng cho gate: `ID` (trống/MISSING_ID → skip), `Folder Video`, `Video Đã Đăng` (next = int+1).
- Target video: `D:\TIKTOK-videonuoinick\<Folder Video>\<next_video>.mp4` — phải tồn tại, size > 10KB,
  không write-lock (FFmpeg đang render = skip `video_not_rendered`).
- Hard timeout subprocess = 900s; chỉ chạy khi còn ≥ 30 phút trước ca kế tiếp.
- Kết quả ghi `upload_result.json` trong child artifact dir (pattern `_write_follow_result`).
- 3 lớp bằng chứng success (sự cố m74 false positive — xem skill workbook-slot-mapping):
  receipt `post_submission_state=ACCEPTED`, profile scan `viewports >= 2`, ảnh độc lập.

## Plumbing CÒN THIẾU (chưa implement — cần làm)
- **`_session_index` chưa tồn tại**: grep toàn repo (trừ `.ai-runs`/`__pycache__`) = 0 hits.
  Cần thêm: arg `--session-index` trong `run_tiktok.py` (khu vực `--account-row-index`, dòng ~630
  `config["_account_row_index"] = int(args.account_row_index or 1)`) → `config["_session_index"]`
  → đọc trong `_run_child`/hook. Gate: chỉ chạy khi `session_index == 3` (phiên cuối ca).
- `MachineAccount` (core/feed_session_workbook.py dòng 40) KHÔNG có field session index —
  lấy từ config, không từ row.
- Parity date chẵn/lẻ: snapshot lúc bắt đầu ca (xem cron entrypoint / `_feed_session_machines`),
  không tính lại ở hook.

## Test — trạng thái & pattern
- `tests/test_multi_machine_feed_session.py` (unittest style): imports `_path_setup`,
  helpers `write_workbook(path, rows)`, `make_ctx(temp_dir, workbook, machines=..., max_workers=...)`
  với config dict chứa `adb_path`, `timeouts`, `safety{allow_navigation_only, allow_feed_swipe, ...}`,
  `feed_session`, `_machines`, `_account_workbook`, `_account_row_index`, `_max_workers`.
- **Hiện KHÔNG có test nào cho `_run_follow_hook`** (grep `tests/` rỗng) — `test_upload_hook.py` mới
  sẽ là test đầu tiên cho hook subprocess; mock `subprocess.run` + đọc `upload_result.json` +
  assert log events trên `child_ctx.logger.events`.
- Chạy test: `python -m pytest tests/test_upload_hook.py -q` từ `python_runner/`.

## PITFALL path có space (lặp lại lần 2)
`search_files`/rg báo `IO error ... system cannot find the path specified` với
`D:\Taadaa\tiktok-luot nuoi acc` — luôn dùng terminal grep:
`cd "/d/Taadaa/tiktok-luot nuoi acc/python_runner" && grep -n "<pattern>" <file>`
