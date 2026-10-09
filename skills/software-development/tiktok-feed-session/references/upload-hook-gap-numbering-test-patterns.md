# Upload Hook Gap Numbering & Test Mocking Patterns

## 1. Subprocess Mocking Target in `test_upload_hook.py`
- Do NOT mock `flows.multi_machine_feed_session._run_single_upload_subprocess` — this helper function does not exist in `flows.multi_machine_feed_session`.
- Always mock `subprocess.run` directly:
  ```python
  from unittest.mock import MagicMock, patch

  run_id = "run_SERIAL_M5_test_gap"
  fake_proc = MagicMock(
      returncode=0,
      stdout=f"Starting real workflow: run_id={run_id}\nPost verification PASSED",
      stderr="",
  )
  with patch("subprocess.run", return_value=fake_proc) as mock_run:
      res = _run_upload_hook(ctx, account, child_ctx, child_result)
  ```

## 2. Post-Verification Report Requirement
- When testing video upload hook (including gap numbering fallback where next sequential video is skipped and a higher number is picked):
  - `_run_upload_hook` validates post execution via `<tiktok_video_runtime_root>/<run_id>/report.json`.
  - The report must be written before `_run_upload_hook` checks it:
    ```python
    report_dir = tmp_path / "video-runs" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "report.json").write_text(json.dumps({
        "status": "SUCCESS",
        "post_verified": True,
        "video_number": 5,
    }), encoding="utf-8")
    ```
  - If `report.json` is missing or `post_verified` is not read properly, `_run_upload_hook` fails with `reason: 'post_verification_failed'`.
