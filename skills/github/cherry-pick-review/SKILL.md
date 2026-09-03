---
name: cherry-pick-review
description: Review cherry-picked/backport commits for dropped context — missing constant/import definitions, stale pre-rule patterns, partial migrations, silent fail-open gates. Trigger on commits labeled "cherry-pick <sha>" or backport diffs.
---

# Cherry-Pick Review (backport diffs)

Commits named `(cherry-pick <sha>)` reappear across Taadaa repos (`Tiktok_Reg`, consumer repos). A cherry-pick re-applies a diff onto a DIFFERENT base tree — new context often breaks incomplete copies. Review these differently from normal commits: **the upstream commit is the ground truth, and the new base is the danger zone.**

## Method (verified 2026-08-18 — 3-commit review, 2 failed)

1. **List + diff surface first.** `git log --oneline -8`, then `git show --stat <sha>` per commit. Note label `cherry-pick <orig>` for each.
2. **Pull the upstream commit** (`git show <orig>`) and diff the delta between upstream and the cherry-pick (`git diff <cp>~1 <cp>` vs `git diff <orig>~1 <orig>`). The cherry-pick should be a SUBSET (older base) — every dropped hunk is a suspect.
3. **Undefined-name scan (fastest MAJOR finder):**
   - `grep -n "USED_NAME" file` then `grep -n "USED_NAME\s*=" file` — usage without any assignment anywhere = guaranteed `NameError` at runtime. 0 assignments = crash.
   - Also check `import` blocks: upstream may import symbols; the cherry-pick often drops the import line too (same failure class).
   - Python: `ast.parse` + regex scan is enough; pyflakes isn't installed in stock envs.
4. **Fail-open sweep on safety gates.** Any `try: ... except Exception as exc: log("...skipped (non-fatal)")` around a gate (VPN/proxy/lock/workbook/requirements) = the gate silently disables when anything raises. A crashed gate must BLOCK (fail-closed), never skip. This turns a code bug into a silent policy bypass — the worst outcome class in farm ops (see `taadaa-farm-ops-rules` §5 FAIL-OPEN TRAP).
5. **Verify against CURRENT rules, not the original commit's era.** Upstream commits older than the latest rule change carry the pre-fix pattern (e.g. hardcoded proxy-mapping path vs `resolve_proxy_mapping_path()` fail-closed added 17/08). A faithful cherry-pick of an old commit can violate today's farm rule while being byte-identical to its source.
6. **Check same-family call sites for partial migration.** New helpers (e.g. `swipe()` jitter) that upstream wired into 8+ call sites: cherry-pick may only convert one. `grep -n 'old pattern' file | grep -v 'new helper'`.
7. **Environment reality-check:** run the checks against the ACTUAL runtime interpreter/venv (`/d/Taadaa/python-envs/automation/Scripts/python.exe`) and confirm the API surface exists (`hasattr` on the installed `automation_core`), not the source tree. Import paths differ (installed wheel vs repo dir).
8. **Escalation:** any BLOCK-level gate touched by the change — even if the code looks right — gets a read of the surrounding function to confirm it still raises on block (not swallowed by outer try). If the gate is in a `finally`/`handoff` path, state the exit code it produces.

## Report shape (user-facing)

- Verdict per commit: APPROVED / MINOR_FIXES / REJECT — with commit id (short).
- Findings numbered MAJOR / MINOR / NIT; each with **locator `file:line`** and the consequence in production terms (what actually happens at runtime, e.g. "batch runs without VPN gate, log shows 'skipped'").
- Never modify files during review — report only.

## Pitfalls

- **Don't trust `--stat` "1 file, 2 insertions"** — a tiny cherry-pick of a torn commit can be the whole bug.
- **Module import path trap:** `import automation_core` may resolve to a stale system site-packages copy, not the farm venv. Always check `os.path.dirname(automation_core.__file__)` + `importlib.metadata.version`.
- **Commit message says "cherry-pick X" but the diff ≠ X's diff** — always reconstruct the upstream and diff against it; the label is intent, not proof.
- **A skip-branch (`except Exception → "non-fatal"`) is a finding even when no bug is present** — it converts every future bug in the gate into a silent skip.

## References

- `references/2026-08-18-cherry-pick-vpn-gate.md` — worked case: 3 cherry-picks on Tiktok_Reg `reg-stable-0722`; `NameError` from dropped constants, stale pre-§5 hardcoded mapping path, partial swipe migration. Includes the exact grep one-liners.