# Batch Aggregator Artifact Parse Observability & Closeout Invariants

## Invariant: Never Swallow Parse Exceptions Silently
In `automation_core.batch_aggregator`, secondary artifact parsing (e.g. `follow_result.json`, `upload_result.json`, machine manifests) must never use bare `except Exception: pass`.
Doing so causes closeout review rejection because malformed artifacts or disk/permission errors disappear silently while reporting false success or unclassified states.

### Correct Pattern
Always log an observable warning with context (artifact type, artifact path, and exception):
```python
try:
    fldata = json.loads(fl_path.read_text(encoding="utf-8"))
    ...
except Exception as exc:
    log.warning("Failed to parse follow_result.json at %s: %s", fl_path, exc)
```
- Batch aggregation must remain resilient (do not raise/crash the batch parse loop).
- Logging ensures observability in production logs and enables assertions via pytest `caplog` in regression tests.

## Follow & Upload Classification Invariants
When inspecting machine artifact directories in `_parse_multi_machine_summary`:
1. **FollowHook Manual Review**: `status` in `("MANUAL_REVIEW", "ERROR", "EXCEPTION", "FAIL")` or `exit_code != 0` (and not `OK`/`SUCCESS`) -> `succeeded = False`, `error_type = "FollowScriptError"`, `error_message` prefixed with `FollowHook:`.
2. **FollowHook Released**: `status == "FOLLOW_FAILED"` or `follow_failed is True` -> `succeeded = False`, `error_type = "FollowReleasedError"`.
3. **UploadHook Script Error**: `status` in `("error", "fail", "timeout")` or `exit_code != 0` (and not `success`) -> `succeeded = False`, `error_type = "UploadScriptError"`, `error_message` prefixed with `UploadHook:`.
4. **Legitimate Skips**:
   - Follow: `status` in `("SKIPPED", "SKIP")` or reason containing `"under-10-videos"`, `"rest-day"`, `"organic-rest-day"`, `"cooling_period"`.
   - Upload: `status` in `("skipped", "skip")` or reason containing `"already_uploaded"`, `"organic-rest-day"`, `"rest-day"`, `"video_not_rendered"`, `"missing_video_folder"`, `"cooling_period"`, `"age_gate"`, `"under_10_days"`.
   - Skips must NOT convert the machine result into a failure.
5. **Malformed JSON**:
   - Must log warning at `logging.WARNING`.
   - Must not crash the parser.
