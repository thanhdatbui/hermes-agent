# Samsung S7 UI-timeout propagation

Use this reference when a shared automation-core UI wait is increased for slow SM-G930F/SM-G930W8 consumers.

## Scope boundary

Increase only waits for UI rendering, XML capture, foreground/readiness polling, element/predicate polling, picker/editor state, and UI recapture. Keep ADB atomic operations (`tap`, `swipe`, `input`, `back`, `wm size`, raw `screencap`), lock/device ownership, proxy/network, reboot, transfer, and workbook/business-operation timeouts unchanged unless the task explicitly says otherwise.

A 60-second UI budget does not cure every failure:

- non-XML or killed UiAutomator output is a service/transport failure, not a slow render;
- valid XML for the wrong foreground surface is a navigation/state-normalization failure, not a timeout;
- popup/package-installer foreground must be handled with semantic evidence before the TikTok foreground gate.

## Structured-capture deadline trap

A consumer can accidentally defeat a correct caller budget by passing a much
smaller fixed `deadline_seconds` into `capture_ui_xml`. On slow S7 transports,
a 3-second deadline leaves roughly 2 seconds for persistent capture and too
little for the bounded shell fallback. The downstream account/navigation error
may then be misleading even though earlier capture generations succeeded.

Diagnose from the structured capture timeline, not only the surfaced exception:

1. Isolate the exact live-run time window and list every `ui_capture_*.json` and
   `ui_dump_error_*.json` generation in order.
2. Compare successful node counts/elapsed times with failed artifacts'
   `diagnostics.deadline_ms`, persistent signatures, and shell fallback result.
3. If all failures share a consumer-imposed deadline shorter than the caller's
   explicit UI timeout, treat that cap as a starvation candidate. Do not call
   it the root cause merely because the final code is an anchor/selector error.
4. Write RED at the adapter seam: call `dump_ui(timeout=N)` and assert core
   receives `deadline_seconds == N`. Then remove only the artificial cap.
5. Preserve `max_local_recaptures`, provisioning policy, exact foreground and
   capture-generation verification. A genuine transport timeout remains
   fail-closed; a larger bounded deadline must not relabel or suppress it.
6. Keep atomic ADB, lock, proxy, reboot, transfer, workbook, and business-action
   timeouts unchanged. Update the local UI compatibility registry and run the
   focused test, full consumer suite against the pinned core artifact,
   `py_compile`, EOL/BOM checks, and `git diff --check`.

This is a materially different recovery strategy only after the deadline cap is
removed and verified; it does not authorize a blind identical live retry.

## Propagation workflow

1. Read the repo's `AGENTS.md`, `PROJECT_RULES.md`, and handoff/structure docs.
2. Snapshot branch/upstream, `git status --short --untracked-files=all`, scoped diffs, and EOL state before editing.
3. Confirm ownership. A dirty file may be unrelated work; if the user says no one is editing the repo, continue, but preserve unrelated dirty files. If an active owner exists, do not clobber it.
4. Search production code for actual capture/read paths (`capture_ui_xml`, `dump_current_ui`, `uiautomator dump`, foreground polls, predicate waits). Do not mass-replace every numeric timeout.
5. Add a focused regression contract for each consumer family: assert UI defaults/budgets and assert protected atomic timeout values remain unchanged where practical.
6. Run the focused suite with the correct source import path (`PYTHONPATH=src` for core; consumer-specific `PYTHONPATH` where needed), then `py_compile` and EOL/diff checks.
7. Stage an explicit allowlist only. Verify cached names, cached diff, exact commit file list, local SHA, remote SHA, and remaining dirty files. Push each repo independently.

## Known Windows verification traps

- A bare `pytest` may import an installed/stale `automation_core`; run core tests with `PYTHONPATH=src`.
- Consumer tests may need `PYTHONPATH=python_runner` or execution from the package root.
- `PytestCacheWarning` caused by a protected `.pytest_cache` is a warning, not proof of a product failure; report it separately.
- CRLF/mixed-EOL consumer files must be edited byte-safely. Do not normalize the whole file for a one-line timeout change.
- Full-suite failures from unrelated metadata/provider/workbook tests must remain separate from focused timeout evidence; do not repair unrelated dirty work merely to claim a green timeout patch.

## Reporting

Report three categories distinctly: (1) repos changed and pushed with focused evidence, (2) repos audited but with no applicable production UI path, and (3) repos with unrelated blockers/dirty work preserved. Never claim that a worker's summary is verified until the current worktree, exact diff, tests, and remote ref are checked independently.
