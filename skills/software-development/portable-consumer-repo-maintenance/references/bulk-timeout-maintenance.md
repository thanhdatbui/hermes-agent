# Bulk UI-capture timeout maintenance

Use this reference for a user-provided allowlist spanning several consumer repositories.

## Procedure

1. Build an explicit manifest: repository, exact file, symbol/call site, current value, requested value, and exclusions. Treat scanned line numbers as navigation hints only; workers and prior edits can shift them.
2. Preflight every repository independently: `git status --short --untracked-files=all`, targeted file existence, current diff, byte-level EOL counts, and a hash/size snapshot. A dirty target is not permission to overwrite it; separate pre-existing hunks from the requested hunk.
3. Classify each site before editing:
   - shared capture APIs: `capture_ui_xml`, `capture_ui_observation`, `dump_current_ui`;
   - adapter-local wrappers that forward to those APIs;
   - raw shell `uiautomator dump`, which is a different implementation and must be reported separately unless the request explicitly includes raw shell capture.
4. Apply only content-asserting replacements. For CRLF or mixed-EOL files, read bytes, patch an exact unique anchor, and write bytes without newline normalization. Do not use `Path.read_text()/write_text()` or a formatter for a timeout-only change.
5. Re-scan the final files for the requested old/new values and for protected invariants (budgets, coordinate fallbacks, settle delays, boot timeouts, and unrelated wait/retry constants). Confirm the changed diff is limited to timeout/deadline expressions.
6. Verify each repository independently: `py_compile` for changed Python files, relevant focused pytest targets, and `git diff --check`. Keep full-suite results separate from focused results. Do not commit, push, or run live device automation unless the user explicitly asks.

## Important edge cases

- If the requested line/value no longer exists because the current checkout already differs from the scan, do not force a textual match. Inspect the effective timeout path and make the smallest equivalent capture-only change, then report the line drift.
- A file may already be modified by another worker. Never reset, checkout, or rewrite the whole file; use a byte-level unique replacement or stop and report an ownership collision.
- Do not raise every `timeout=20` in a large flow. Raise only the capture/deadline path named by the manifest; preserve business waits, retry budgets, settle `0.3`, coordinate fallback, and boot timeout invariants.
- A session/tool-call limit before the first write means the task is incomplete. Report the exact read-only findings and do not imply that code or tests were completed.

## Duplicate anchors and dirty-tree attribution (verified 2026-08-10, 8-repo 60s bump)

- **The same timeout literal repeats across many sites in one file.** In `capture_recovery.py`-style recovery modules, `command_timeout = _bounded_timeout(timeout, minimum=1.0, maximum=8.0)` appeared at BOTH L1173 and L1293, and `request_timeout = _bounded_timeout(timeout / 2.0, minimum=2.0, maximum=10.0)` at BOTH L1294 and L2091. In `automation_core/ui.py`, the two-line block `settle_delay_seconds: float = 0.3,\n    deadline_seconds: float = 3.0,` was identical in `capture_ui_observation` (L204) and `_dump_current_ui_lightweight` (L1068). The count-assert (`data.count(old) == 1`) correctly refused these — do not weaken it to `>= 1`.
- **Disambiguation recipe: extend the anchor with a neighboring unique line** instead of accepting ambiguity:
  - Pair with the NEXT line when the following line differs (`timeout / 3.0, maximum=4.0` after L1173 vs `timeout / 2.0, minimum=2.0` after L1293 — replace both lines in one anchor).
  - Prefix with the preceding command line (`["cat", "/proc/sys/kernel/random/boot_id"],` before L259; `["/data/local/tmp/atx-agent", "server", "-d", "--stop"],` before L2775; `target_dir.mkdir(parents=True, exist_ok=True)` before L2091).
  - Use distinguishing substrings: `self.timeout` vs `timeout`, `rpc_timeout =` vs `request_timeout =`.
  - For two identical two-line blocks (settle+deadline), add the THIRD preceding line (`readiness_probe:` in the observation API vs `artifact_dir: Path | None,` in the lightweight dump) to make the anchor unique.
  - The one-line-ahead scan (listing every matching line with its line number) is what reveals which sites are duplicates BEFORE writing — always produce it first and group identical strings.
- **A prior worker may already have bumped the value in the dirty working tree.** Triage said `min(20.0→60.0)` at one site; the uncommitted diff vs HEAD showed `8.0→20.0` (worker's earlier edit), so my diff vs HEAD read `8.0→60.0`. Anchor on the CURRENT working-tree bytes (what the file actually contains now), not on the triage's before-value, and state the two-step delta in the report.
- **Pre-existing dirty files make `git diff` show foreign hunks.** One target repo had ~1875 foreign insertions; `git diff | grep timeout` surfaced unrelated `timeout=18` magic-link lines. Attribute your hunks by grepping the diff for your exact old→new byte strings (e.g. `-UI_XML_COMMAND_TIMEOUT = 8` / `+UI_XML_COMMAND_TIMEOUT = 60`) and list everything else as pre-existing worker dirt in the report — never claim it.
- **Verify EOL by counting, not by diffing.** Compare crlf/bareLF counts before and after per file (mixed files: both counts unchanged, e.g. 414/18 and 9392/2525 stayed identical). `git diff --check` rc=0 is the whitespace gate; the `LF will be replaced by CRLF` warnings are autocrlf noise, not an error.

## Semantic timeout keys and protected transport budgets

When a consumer uses one config key such as `adb_seconds` for both UI reads and atomic ADB commands, never raise that shared key to satisfy a render-wait request. Add a semantic UI key (for example `ui_capture_seconds: 60`) and keep the atomic transport default unchanged (`adb_seconds: 15`). Route only `capture_required_ui`/render-read paths through the new key; leave tap/swipe, proxy/network, reboot/process, and workbook timeouts untouched. Update the runtime default map and config examples together, and add a focused regression probe that asserts both the new UI value and the preserved atomic value.

For a dirty Windows consumer checkout, use an explicit stage allowlist (`git add -- <production files> <focused tests>`), inspect `git diff --cached --name-status`, commit only after focused verification, and push the tracked upstream branch only when requested. Re-check local/remote SHA and `git status --short --branch` afterward; a pre-existing dirty test or untracked runtime files must remain unstaged and be called out explicitly.

The `tiktok-luot nuoi acc` Samsung S7 case also established that a system may re-mark the workspace unverified in a later turn even after a prior probe. In that turn, rerun a fresh `tempfile`-managed `hermes-verify-*.py` under `%TEMP%`, execute it against the exact changed behavior, prove deletion, and report it as **ad-hoc verification**, separate from focused-suite or compile claims. Do not answer with stale verification evidence alone.
