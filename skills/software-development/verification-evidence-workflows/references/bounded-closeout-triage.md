# Bounded closeout-gate triage reference

## Observed Windows recipe

Repository: `D:/Taadaa/automation-core`.

Use an out-of-band parent process so pytest output is streamed and the child is
killed at a hard bound without touching repository files:

```bash
python -u -c "import subprocess,sys,time; cmd=[sys.executable,'-m','pytest','-vv','-s','tests/test_tiktok_benign_popup.py','--tb=short']; print('START',time.strftime('%Y-%m-%d %H:%M:%S'),flush=True); t=time.monotonic(); p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1); timed=False
for line in iter(p.stdout.readline,''):
 print(line,end='',flush=True)
 if time.monotonic()-t>115: p.kill(); timed=True; break
rc=p.wait() if not timed else p.returncode
print('DIAGNOSTIC_RC',rc,'TIMED_OUT',timed,'ELAPSED',round(time.monotonic()-t,2),flush=True)"
```

First collect the file so dot positions can be mapped to node IDs:

```bash
python -m pytest --collect-only -q tests/test_tiktok_benign_popup.py
```

## Concrete transcript pattern

The suspected focused file collected **49 items**. A current bounded verbose run
printed each node and ended with:

```text
tests/test_tiktok_benign_popup.py::test_location_permission_dialog_english_detected_and_dismissed PASSED
...
 tests/test_tiktok_benign_popup.py::test_add_phone_unlabeled_button_close_detected PASSED
============================= 49 passed in 4.37s ==============================
DIAGNOSTIC_RC 0 TIMED_OUT False
```

Thus a prior progress string such as `...........................F.........`
must not be treated as a root-cause locator. Collection output maps the apparent
failure position to a real test, while the verbose run proves whether that node
and the subsequent suspected hang node still reproduce.

## Candidate versus current worktree

For the observed closeout candidate:

- `HEAD~1..HEAD` contained six tracked paths: `AGENTS.md`,
  `src/automation_core/alerts.py`, `src/automation_core/batch_aggregator.py`,
  `src/automation_core/device_lock.py`,
  `src/automation_core/tiktok/account_switcher.py`, and `tests/test_alerts.py`.
- The current worktree had five tracked modified paths: all except
  `src/automation_core/device_lock.py`.
- `docs/ai/workflows/farm-alert-coordinator-loop.md` was untracked and therefore
  absent from ordinary `git diff`, unless explicitly included in candidate
  accounting.
- Current focused diagnostics passed: `test_alerts.py` 30, `test_batch_aggregator.py`
  56, `test_account_switcher_preconfirmed.py` 43,
  `test_device_lock.py` 79, and `test_tiktok_benign_popup.py` 49.

The correct classification was **transient/stale gate evidence**, not a current
structural defect. The smallest next action was to rerun the closeout gate against
the stable current candidate; if it repeated obsolete output, inspect the exact
gate command and payload rather than editing production code.
