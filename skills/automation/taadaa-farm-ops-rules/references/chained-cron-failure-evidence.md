# Chained no-agent cron failure evidence

Use this when a scheduled script chains multiple phases (for example, Gmail registration followed by TikTok registration) and Telegram reports only `Code N | Hoàn tất`.

## Evidence-first workflow

1. **Treat the Telegram line as wrapper status only.** A launcher can finish normally after a child phase returns non-zero, and a summary parser may fall back to `Hoàn tất` when it cannot find a summary line. Neither phrase proves that the batch succeeded.
2. **Anchor every conclusion to the exact run.** Start with the cron output timestamp and job ID, then locate the phase run directory, summary JSON/TXT, merge summary, target manifest, and child logs created during that run. Do not use an old shared log as proof unless its timestamp/run ID is anchored to the same execution.
3. **For a phase that produced a summary, report the summary counts and exact classifications.** Check `TOTAL`, `SUCCESS`, `FAILED`, `PENDING/VERIFY`, and result/merge counts. A merge step marked `DONE` can still have zero results; state that explicitly and check whether the workbook hash changed.
4. **For the next phase, verify the execution gates in order:** target detection output/manifest -> new batch run directory -> per-machine worker directories/logs -> verified result artifacts. If the phase exits in seconds and no new batch/worker artifacts exist, classify it as a preflight/target-detection/launcher failure, not as a TikTok UI, OTP, or account failure.
5. **Quote exact error signatures and separate facts from hypotheses.** `proxy readiness timed out`, `DEVICE_LOCK_*`, inventory conflict, missing script, and worker/UI errors are different classes. An exit code by itself is not a root cause.
6. **Report with evidence paths and counts, without credentials.** Redact email addresses, passwords, OTPs, tokens, and device serials from user-facing reports unless the user explicitly needs a non-secret identifier.

## Durable launcher/reporting fix

When maintaining the launcher (only after the user authorizes code changes), persist each phase's stdout and stderr to a run-specific artifact, include the artifact path and structured machine-level breakdown in the Telegram report:
- **Tách riêng các Phase:** Phase 1 (Reg Gmail/Mail) và Phase 2 (Reg TikTok).
- **Định dạng báo cáo chuẩn gọn (User rule):**
  • **Tổng máy:** <Số lượng>
  • **Success (<Số lượng>):** <Danh sách STT máy thành công>
  • **Fail (<Số lượng>):** <Danh sách STT máy thất bại kèm lỗi nếu có>
  Tuyệt đối KHÔNG in danh sách per-machine từng dòng `[OK] Machine X...` làm tràn chat.
- Tuyệt đối không chỉ in 1 dòng chung chung `Code N | Summary` hay fallback mập mờ mà không rõ máy nào được / máy nào hỏng.
Always ensure `subprocess.run(..., capture_output=True, text=True)` includes `encoding="utf-8", errors="replace"` when capturing output from Windows processes (PowerShell, ADB, CLI tools) to prevent `UnicodeDecodeError` in worker reader threads on non-UTF-8 console bytes (e.g. `0xa0` non-breaking space or Windows code page characters).

## Hermes cron timeout for chained batches

Hermes scheduler có hard timeout mặc định `_DEFAULT_SCRIPT_TIMEOUT = 3600s` cho script `no_agent: true`. Khi chuỗi ban đêm chạy nhiều phase/batch vượt quá 60 phút, Hermes scheduler sẽ ngắt script và gửi cảnh báo `provider timeout. Fallback chain was exhausted or unavailable`.
- **Cách Fix:** Chạy `hermes config set cron.script_timeout_seconds 10800` để nâng timeout lên 3 tiếng.
- **Xử lý khi bị ngắt dở:** Kiểm tra artifacts `D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\` lấy các file `tracking_result_stt*.json`, chạy `apply_deferred_tracking_results.py` và sync sang `taikhoan_run_safe.xlsx` qua `sync-safe-workbook.py`.

## Common pitfalls

- `exit code 1` from the chain is not enough to distinguish child failure, target detection failure, post-batch workbook merge verification failure, or launcher exception.
- Check whether devices succeeded while workbook merge failed: `merge_success_results.py` can record successful device results but fail at `single_writer_workbook_update` / verify step (`WORKBOOK_VERIFY_ROLLBACK_FAILED`), leaving workbook untouched despite successful worker executions.
- A `DONE` merge summary with `RESULTS_TOTAL=0` is completion of the merge step, not a successful registration batch.
- A stale manifest or a large append-only log can make a phase appear to have run; use mtime and run IDs to prove freshness.
- Do not infer UI/OTP problems when the phase never created worker artifacts.
