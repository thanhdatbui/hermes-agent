# Follow Timeout Synchronization and Farm Concurrency Architecture

## Follow Timeout Architecture

1. **Timeout Synchronization Across Repositories:**
   - Parent Feed Session (`multi_machine_feed_session.py` in `tiktok-luot nuoi acc`): `DEFAULT_FOLLOW_HOOK_TIMEOUT_SECONDS = 1200.0` (20 minutes).
   - Follow Runner Core (`config.py` & `config.example.yaml` in `tiktok-follow`): `feed_timeout_seconds: 1200.0`.
   - The outer device session timeout (`DEFAULT_DEVICE_TIMEOUT_SECONDS`) is 2100.0s (35 minutes), leaving plenty of budget for startup, swipes, follow, and upload.

2. **Concurrency Differentiation (Feed vs Follow vs Upload):**
   - **Feed Concurrency:** Governed by the parent `ThreadPoolExecutor(max_workers=40)`.
   - **Follow Concurrency:** Throttled strictly by `_FOLLOW_CONCURRENCY = threading.BoundedSemaphore(DEFAULT_FOLLOW_MAX_CONCURRENCY)` (`DEFAULT_FOLLOW_MAX_CONCURRENCY = 20`) and cross-process OS file slot locks (`slot-0.lock`..`slot-19.lock`) under `~/.codex/follow-concurrency-locks`.
     - *Why 20?* When 40 machines execute `run_follow.py` simultaneously, 40 concurrent ATX UI dump / text typing / search commands flood ADB server (Port 5037), causing XML dump latency to spike from 0.5s to 15–30s per dump. Throttling follow concurrency to 20 child workers limits peak dump pressure on port 5037 while maximizing throughput for farm batches.
   - **Upload Concurrency:** Throttled strictly by `_UPLOAD_CONCURRENCY = threading.BoundedSemaphore(DEFAULT_UPLOAD_MAX_CONCURRENCY)` (`DEFAULT_UPLOAD_MAX_CONCURRENCY = 20`) under `~/.codex/upload-concurrency-locks`.
   - **Hardware Bottleneck Context:** Even on high-performance multi-socket Xeon hosts with abundant CPU/RAM, follow and upload concurrency MUST be capped to protect:
     1. ADB Server (Port 5037) & USB host controller endpoints from socket/packet drops during simultaneous hierarchy dumps, touch inputs, and video pushes.
     2. Egress proxy bandwidth across Singbox/MikroTik ports to prevent network stalls.

3. **Soft Deadline Budgeting in Follow Runner:**
   - `FollowEngine.has_time_for_next_action(reserve_seconds=60.0)` tracks elapsed session time against `cfg.feed_timeout_seconds`.
   - In `run_mode1` and `run_mode2`, before starting a new UID search or anchor traversal, the runner evaluates `has_time_for_next_action(60.0)`.
   - If time remaining is < 60s, the loop breaks gracefully and returns `status="OK"` with all followed accounts saved, rather than continuing blindly and being killed by parent `subprocess.TimeoutExpired`.
