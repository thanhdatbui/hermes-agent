# Live unlock and rerun procedure

Use this reference when the user explicitly asks to unlock/release a machine and rerun TikTok Follow after a live UI incident.

## Target and lock discipline

1. Resolve the requested machine to its canonical serial before any device action.
2. Inspect the lock store by both machine and serial. Do not infer ownership from a PID, an old report, or a nearby machine's lock.
3. If the requested machine has no lock, do not delete another machine's lock. A lock on machine 47 is not evidence that machine 3 is locked.
4. If a lock is present, verify its owner/project/status. The default is no interference with an active official owner. If the user explicitly authorizes preemption, use the shared `automation_core.device_lock` operator-preempt/takeover API with exact machine+serial scope and a documented reason; never unlink lock files or hand-write lock JSON. Capture the old owner identity and new canary lease identity before starting the runner. Retained `failed_locked` locks still require the explicit authorized core release API.
5. Re-check the requested machine's lock after preemption and before rerun. Both machine and serial aliases must point to the canary lease; if either alias still belongs to the old owner or ownership is changing concurrently, stop. The post-run check must prove that the canary aliases are absent; report unrelated locks separately.
6. Hold the canary lease for the entire official runner execution, including preflight and cleanup. Release only that lease in a terminal `finally`; if the runner reaches `MANUAL_REVIEW` or another failure, preserve evidence and report the exact terminal status before release.

## Official rerun

- Run the repository's official entrypoint, not an ad-hoc ADB tap or a direct `run_follow.py` path if the repo exposes a module entrypoint.
- Use the resolved serial/account row and the requested mode explicitly. For this repo the canonical form is:

```bash
export ADB_SERVER_SOCKET=tcp:localhost:5037 ADB_MDNS=0
cd /d/Taadaa/tiktok-follow
/d/Taadaa/python-envs/automation/Scripts/python.exe -m follow_runner.run_follow \
  --machine <N> --config config/<config>.yaml \
  --account-row-index <row> --mode <mode>
```

- A real rerun is successful only when the runner emits `FOLLOW_RESULT` with `status: "OK"`; include the actual followed/skipped values. Dry-run and unit tests are not live proof.
- If the runner is blocked by a current owner or preflight, stop and report the exact blocker. Do not force takeover, restart ADB, clear app state, reboot, or stop cron.

## Verification and reporting

- Run focused tests for the changed selector/flow, then the full repository test suite when the working tree is stable. A timeout, stale result, or mixed dirty-tree test is not a pass.
- Run `py_compile` and `git diff --check` for the final source state.
- Keep the user-facing report short and direct: `Mục đích → Kết quả → Blocker`. Lead with the result, not the internal explanation. Explain "lần 2" in one sentence only if asked: it means the bounded retry after recovery, not a second business follow.
- Never claim an unlock, rerun, or success from a plan line alone; require the release/lock re-check and the actual `FOLLOW_RESULT`.

## Common pitfall

A live XML can show the relation list while the parser still rejects it. Record the concrete resource IDs and add a narrow structural regression fixture (for example, a new RecyclerView ID plus its row Follow-button ID). Do not loosen validation globally or convert every unknown surface into a valid list.

## Stale lock detection — BẮT BUỘC trước khi từ chối canary

Khi đọc lock file thấy `owner_active: True` hoặc `status: running`, KHÔNG tin mù vào field đó. Bắt buộc xác minh PID thực sự còn sống:

```python
import psutil
from automation_core.device_lock import inspect_device_lock

lock = inspect_device_lock(str(machine))
pid = lock.get("pid") if lock else None
pid_alive = False
if pid:
    try:
        proc = psutil.Process(pid)
        pid_alive = proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        pid_alive = False
```

- **PID còn sống thật (`pid_alive=True`):** Lock hợp lệ — không can thiệp, báo BLOCKED.
- **PID chết hoặc không tồn tại (`pid_alive=False`):** Lock là STALE — chạy canary bình thường, không cần preempt.
- **Không có lock file:** Máy rảnh — chạy canary bình thường.

**Sai lầm điển hình (Máy 59, 2026-09-03):** Alert `GIỮ HIỆN TRƯỜNG` đồng nghĩa farm đã dừng tiến trình trên máy đó. Lock file còn lại là stale (PID chết). Agent đọc `owner_active: True` trong file và từ chối chạy canary không cần thiết — sai. Phải kiểm tra PID thực tế trước khi kết luận.

