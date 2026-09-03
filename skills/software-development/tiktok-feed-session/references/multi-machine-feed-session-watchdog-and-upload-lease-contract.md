# Multi-Machine Feed Session: Hard Watchdog, Upload Slot Lease, & Publication Fence

## 1. Concurrency & Upload Slot Lease Contract
- **Cross-process & in-process locking**: Upload hook runs under `_upload_concurrency_lease` combining an in-process `threading.BoundedSemaphore(DEFAULT_UPLOAD_MAX_CONCURRENCY)` (16 slots) and filesystem locks `slot-0.lock` ... `slot-15.lock` rooted at `_upload_lock_root()`.
- **Strict boundary timeout**: Queue wait timeout must be calculated strictly via `_calculate_queue_timeout()` at the lease acquisition boundary: `min(upload_timeout_budget, hard_remaining_before_queue)`.
- **Deduct queue wait from subprocess**: When `subprocess.run` starts, `subprocess_timeout` MUST be `float(upload_timeout_budget) - queue_wait_seconds` (and capped by remaining hard deadline).
- **Near-zero sleep safety**: `_UploadConcurrencyLease.acquire()` sleeps with `min(0.05, rem)` where `rem = deadline - time.monotonic()`. It must NEVER sleep with a fixed floor like `max(0.001, rem)` to prevent overshooting the exact timeout boundary.

## 2. Hard Watchdog Deadline & Publication Fence (Single Winner)
- **Atomic CAS Election**: `_claim_watchdog_terminal(timing, force=False)` uses `state_lock` to perform an atomic compare-and-swap election:
  - Rejects if already terminalized or owner is already watchdog.
  - Enforces `time.monotonic() >= deadline` unless `force=True` (for worker process exceptions/crashes).
  - Rejects if worker completed success release before deadline (`success_release_completed=True` and `success_release_completed_at < deadline`).
  - Increments `generation` and sets `publication_owner = "watchdog"`.
- **Publication Lock Fence**: File I/O (`_finalize_child`, `_write_follow_result`, `_write_upload_result`, `_safe_fenced_log`) checks publication permissions and writes under `publication_lock`.
- **Atomic File Replacement**: All summary/manifest paths (including emergency exception fallback in `_write_fallback_child_artifacts` and mapping source errors) MUST write to a `.tmp` file and `os.replace` to destination under `publication_lock`.
- **Success-Release 10s Window**: If a worker completes `lease.finish(succeeded=True)` and records `success_release_completed_at` before deadline, watchdog claim returns `False`. The watchdog monitor loop waits `future.result(timeout=10.0)` for the child result, and cleanly skips if still incomplete without blocking the batch.

## 3. Worker Stagger & Per-Future Deadline Tracking
- **Non-blocking stagger**: Stagger delays (`launch_plan.delays_ms`) are executed inside the worker wrapper threads (`worker_wrapper`), not in the submission loop.
- **Terminalized check after stagger**: After waking from stagger sleep, worker must verify `time.monotonic() < deadline` and `not _watchdog_is_terminalized(timing)` before initiating device/VPN/app actions.
- **Immediate watchdog loop**: Watchdog loop tracks `pending_futures` immediately as futures are created. Pre-scan of prior evidence must occur before the executor submission loop so submission is instantaneous.

## 4. Cohort Identity Fail-Closed Strictness
- **Reject Boolean bypasses**: Explicit checks that `_cohort_artifact`, `_assignment_manifest`, `_worker_id`, `_cohort_bound_live` are not booleans.
- **Reject Whitespace/Empty Strings**: Explicit cohort identity fields (`tik`, `serial`, `account`, `feed.row`) must be non-empty and match exact types.
- **Mandatory structure**: Cohort plan entry must include `tik`, `feed` (with integer `row` and single-element integer list `machines`).
