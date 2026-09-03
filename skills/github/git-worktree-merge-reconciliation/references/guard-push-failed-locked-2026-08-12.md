# Guard-serialized push: codex/failed-locked-phase1 → master (2026-08-12)

Spec-driven integration push của automation-core với blocker = untracked plan file. Workflow tổng quát: SKILL.md §24.

## Repos / branches

- master: `D:\Taadaa\automation-core`, branch `master`, base HEAD/origin = `5519ae915a98fc2fbb9e19bc58179b0be5d343e8`
- feature: `D:\Taadaa\automation-core-failed-locked-wt`, branch `codex/failed-locked-phase1`, HEAD `8a3ede57199f2b879ea3d098ac714300b2a2f7aa` (6 approved commits, ahead origin/master)

## Blocker untracked (byte-preserved)

- `D:\Taadaa\automation-core\.hermes\plans\2026-08-11_ai-escalation-failed-locked.md`
- size 36324, sha256 `be67465f1024f276572c7fc57a500bb297ab5fc855306dbb5b827a1266f13122`
- preserved tại `C:\Users\Kibe\AppData\Local\Temp\automation-core-plan-preserve-be67465f….md` (giữ backup sau restore, sha/size khớp lại)

## Merge guard

- acquire: `python tools/core_merge_guard.py acquire --repo D:/Taadaa/automation-core --owner failed-locked-integration` → in JSON lease `{owner, pid, host, acquired_at, token}`; GIỮ token cho release.
- release: `python <repo>/tools/core_merge_guard.py release --repo D:/Taadaa/automation-core --owner <owner> --token <token>` → `released`; `status` sau đó = `unlocked`.
- Lock dir = `<git-common-dir>/automation-core-integration.lock` (git-common-dir → guard dùng chung mọi worktree của repo). Held → exit 2. Stale recovery sau 900s chỉ khi host trùng + pid chết.
- Script có `--repo` default = `Path(__file__).resolve().parents[1]` — chạy từ trong repo có thể bỏ `--repo`.

## Merge (ff-only)

- `git merge --ff-only codex/failed-locked-phase1` → `Updating 5519ae9..8a3ede5`, 19 files, 3052 insertions(+)/68 deletions(-)
- 6 commits (cũ→mới): `d302dee` feat FAILED_LOCKED terminal giữ device lock, `9e592af` fix baseline collection tools.verify_wheel_metadata, `6d83f8c` feat AI escalation hook core, `e62c2f7` fix fail-closed FAILED_LOCKED pre-record, `57355ad` feat cli list/inspect/open redacted, `8a3ede5` docs(audit) failure-class/handler audit
- File mới: `docs/ai/recovery-failure-class-audit-2026-08-11.md`, `src/automation_core/escalation.py`, `tests/test_escalation.py`

## Test gate

- Focused 8 files (recovery_contract, mandatory_recovery_contract, device_lock, events, escalation, global_recovery, cli, package_metadata): **178 passed**
- Full suite `PYTHONPATH=src python -m pytest -q`: **566 passed / 1 failed** — known failure duy nhất `tests/test_startup.py::test_android_startup_orders_unlock_rotation_then_recents` (step order: `battery_level_simulated` xuất hiện giữa, expected `ensure_portrait_rotation_prepare`). Không sửa test.

## Compile / push / verify

- `PYTHONPYCACHEPREFIX=<temp ngoài repo> python -m compileall -q src/automation_core` → 114 .pyc, temp xoá, `git diff --check` + status sạch
- `git push origin master` → `5519ae9..8a3ede5 master -> master`
- `git ls-remote origin refs/heads/master` = `8a3ede57199f2b879ea3d098ac714300b2a2f7aa`; `git log origin/master..HEAD` rỗng

## Final state

- Status: `## master...origin/master` (0/0) + `?? .hermes/plans/2026-08-11_ai-escalation-failed-locked.md` — expected pre-existing artifact, KHÔNG push/xoá/dọn
- Guard: released → `unlocked`; feature worktree sạch; plan restored byte-for-byte (sha/size khớp)
