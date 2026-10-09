# Dynamic Video Push Timeout and Cleanup over Farm USB Hubs

## Context & Problem

In phone farm environments (e.g. 20–80 Samsung phones sharing USB hubs), ADB transfer bandwidth per device can throttle down to ~0.8–1.0 MB/s.
If `MediaManager.push_video` uses a hardcoded timeout (e.g. 120s), large video files (>100MB, such as 160MB renders on batch machines like m63) exceed the transfer deadline:
- ADB push times out.
- The workflow crashes or aborts the account slot.
- Partial or corrupt video files may linger on the device storage.

## Solution

### 1. Dynamic Timeout Calculation
Calculate push timeout dynamically based on the local video file size in MB:
- Transfer rate estimate: `0.8 MB/s` (worst-case farm USB hub throughput).
- Buffer: `60s` margin for device wake / disk flush / I/O latency.
- Minimum floor: `180s` (to prevent premature timeouts on slow connections even for smaller files).

```python
file_size_mb = local_path.stat().st_size / (1024 * 1024) if local_path.exists() else 0
# Floor at 180s, scale with file size (0.8 MB/s + 60s buffer)
push_timeout = int(max(180, (file_size_mb / 0.8) + 60))
```

### 2. Pass Timeout to ADB Push
```python
result = self._adb.run(
    ["push", str(local_path), remote_path],
    timeout=push_timeout,
    check=False,
)
```

### 3. Safe Failure Cleanup
When push fails (`not result.ok`) or post-push verification fails (`not self._verify_file_exists(remote_path)`):
- Immediately attempt to remove any partial / corrupted file on the device:
  ```python
  try:
      self._adb.shell(["rm", "-f", remote_path], timeout=10, check=False)
  except Exception:
      pass
  ```
- Wrap cleanup in `try...except` so that secondary cleanup errors (e.g. device disconnect) do not mask the primary error or crash the exception handling flow.

## Verification Checklist

1. **Syntax & EOL**:
   - `python -m py_compile scripts/tiktok_workflow/media_manager.py`
   - `git diff --check` (ensure pure CRLF on Windows repo, no bare LF).
2. **Focused Tests**:
   - `python -m pytest tests/test_tiktok_workflow.py -k TestMediaManager`
   - Assert small file (e.g. 1MB) gets minimum 180s timeout.
   - Assert large file (e.g. 160MB) scales: `int(max(180, 160/0.8 + 60)) == 260s`.
   - Assert failure branches trigger remote cleanup without masking `MediaManagerError`.
