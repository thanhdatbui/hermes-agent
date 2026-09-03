# TikTok Follow: lockless ACCOUNT_READY + capture recovery ladder (2026-08-15)

Use this reference for `D:\Taadaa\tiktok-follow` ACCOUNT_READY work. It records the
operator-approved contract that supersedes the older retained-device-lock recipe
for this repo only. Do not generalize it to consumers whose current repository
rules still require leases.

## Current canonical contract

- The canonical Follow runner must not create, read, inspect, retain, hand off,
  update, or release shared device/workbook locks. A failure must not emit lock
  metadata or recreate a stale alias.
- Stale files under `.codex/device-locks` are not execution inputs for this
  consumer. Legacy aliases may only be retired as a separately authorized,
  guarded migration; normal runs never manipulate them.
- The only same-machine concurrency gate is a proven live process whose own
  command line contains `tiktok_workflow --machine N` or
  `tiktok_workflow --machine=N`. Match the machine boundary exactly so machine 1
  never matches machine 11. Return `SKIPPED_BUSY` before Android/TikTok action.
- ACCOUNT_READY remains a no-business boundary: explicit 1-based account slot,
  safe-workbook identity, public core chain `open_account_switcher` ->
  `select_exact_account` -> `verify_selected_account`, independent final
  recapture, exact TikTok foreground, `followed=[]`, and zero Search/Follow.
  Never expose the expected account value in plan, logs, or evidence.

## Process-probe self-match pitfall

An inline shell/Python diagnostic can falsely report several conflicts because
its own command line contains the literal strings being searched, including
`tiktok_workflow` and `--machine 1`. The parent shell and launcher can also carry
that text. Such output is diagnostic contamination, not a real owner.

Preferred proof:

1. Call the production busy predicate directly for the target.
2. For an independent scan, use a standalone temp script (so source text is not
   embedded in the process command line), exclude its own PID, and construct
   sentinels at runtime (`"tiktok_" + "workflow"`, `"--mach" + "ine"`).
3. Evaluate each process command line separately with an exact regex such as
   `(?:--machine\s+N(?=\s|$)|--machine=N(?=\s|$))`.
4. Record only PID/name, never credentials or full command lines.
5. If an earlier raw probe self-matched, label it explicitly as contaminated;
   do not silently quote its count as preflight evidence.

## Consumer-owned three-stage recovery

Disable nested core retry budgets for the public operation by passing
`profile_attempts=1`, `switcher_attempts=1`, and `load_attempts=1`.

Recoverable signatures are case-insensitive and include:

- `UI_DUMP_FAILED`
- `UI_DUMP_UNAVAILABLE`
- `uiautomator_idle_state_error`
- `uiautomator_null_root_node`
- downstream `SWITCHER_ANCHOR_AMBIGUOUS`

Run the initial complete public open/select/verify operation once. On one of the
above signatures, advance through this bounded ladder:

1. **B1 persistent ATX recovery** — require structured, freshly verified XML
   proof. Reject arbitrary truthy objects/strings. If proved, retry the complete
   public operation once.
2. **B2 canonical relaunch** — one force-stop/relaunch via the existing adapter,
   followed by exact Feed proof. If proved, retry the complete operation once.
3. **B3 guarded soft reboot** — only when the canonical config gate is enabled;
   use the public core guarded reboot path and require post-boot readiness plus
   exact Feed proof. If proved, retry the complete operation once.

A stage without proof does **not** permit an operation retry, but the runner may
advance to the next materially different stage. If a retry raises a different,
non-recoverable signature, stop immediately. If all stages exhaust, preserve the
latest recoverable error. Each stage and each corresponding operation retry is
bounded to one. Never add coordinate taps, raw reboot/process-kill logic, VPN
mutation, Search, or Follow to this ladder.

A healthy initial operation must short-circuit B1/B2/B3. A successful healthy
live run proves the direct path, not that each recovery stage executed live; use
production-symbol tests for ladder branch coverage and report that distinction.

## Verification gate

After the last code/test/doc edit:

1. Force the pinned automation-core wheel on `PYTHONPATH`; do not trust an ambient
   install. Verify the imported file and public signatures.
2. Run focused tests for exact-machine busy matching, lock-surface/metadata
   absence, public call kwargs/order, B1 early success, B1->B2->B3 exhaustion,
   no-proof/no-retry, changed-signature stop, adapter hooks, and reboot default.
3. Run the full `follow_runner/tests` suite, `py_compile`, and
   `git diff --check`; inspect BOM/NUL/EOL and statically scan production Python
   for forbidden lock imports/symbols.
4. Bind an independent read-only audit to exact current file bytes (SHA-256 +
   byte count). After any HANDOFF/docs/live-evidence edit, regenerate the prompt
   and rerun the audit. Before accepting `APPROVED`, rehash every bound file and
   require zero mismatches.
5. Historical documentation may mention old retained locks only when clearly
   dated and explicitly superseded by the current lockless rule.

## One-run live evidence checklist

Launch the canonical ACCOUNT_READY command exactly once for the named machine and
slot. A second launch is not a verification step after success.

Do not accept exit code alone. Verify all of:

- sanitized `FOLLOW_RESULT` is `OK`, `followed=[]`, no blocked/skipped result;
- evidence JSON says exact foreground, final identity recapture passed, and
  `zero_business_actions == {search: false, follow: false}`;
- screenshot and XML exist, hash correctly, render a normal TikTok Profile/Feed,
  show the switcher closed, and contain no login/OTP/CAPTCHA/permission/payment
  blocker;
- no expected account value leaked into evidence;
- no matching target runner/video process remains;
- both legacy machine/serial aliases remain absent after the run.

Session evidence snapshot: run `follow-1-5b9ac42bd71c` returned `OK` on the
initial public operation, persistent capture `VERIFIED_HEALTHY` with 171 nodes,
zero business actions/process/locks, focused 103 tests and full 233 tests passed,
and the post-live exact-byte independent audit returned `APPROVED`. Counts and
run IDs are historical evidence, not future acceptance constants.
