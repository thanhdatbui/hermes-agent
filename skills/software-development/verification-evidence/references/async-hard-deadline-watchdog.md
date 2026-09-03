# Async hard-deadline watchdog reference

## Minimal regression matrix

1. **Queue timeout**
   - Occupy the upload concurrency lease.
   - Invoke the upload hook with a finite remaining hard deadline.
   - Assert the lease is called with `timeout=<remaining budget>`.
   - Assert the result is timeout/fail-closed, includes queue wait and hard-budget evidence, and has `subprocess_started=False`.
   - Assert `subprocess.run` was not called.

2. **Deadline before queued start**
   - Use a single worker or otherwise queue a second child behind a longer first child.
   - Bind one absolute monotonic deadline before submitting children.
   - Let the deadline expire while the second child is queued.
   - Assert the second child never begins its side effect and is reported failed, not successful.

3. **Executor shutdown**
   - Make a worker remain blocked past the outer deadline.
   - Assert the caller returns without waiting for that worker; use an executor shutdown path equivalent to `shutdown(wait=False, cancel_futures=True)`.
   - Assert pending futures are terminalized and required device-lock/handoff state is retained.

## Evidence fields

Use explicit fields rather than inferring from log ordering:

- `upload_queue_wait_seconds`
- `upload_hard_budget_seconds`
- `upload_queue_timeout`
- `subprocess_started`
- a reason distinguishing queue timeout, deadline-before-queue, deadline-after-queue, and subprocess timeout

## Windows test command

Quote repositories whose paths contain spaces. For focused Python tests, use the repository's automation interpreter when available and disable cache providers when the environment injects incompatible packages:

```text
python -m pytest -q -p no:cacheprovider python_runner/tests/test_multi_machine_feed_session.py
```

Run `py_compile`, AST parsing, and `git diff --check` after the final edit. Treat a timed-out broad suite as incomplete evidence; report the exact focused counts separately.
