# TikTok follow consumer — P3 safety gates and verification notes

Session-derived reference for the broader `automation-core-consumer` skill. Keep
these as reusable invariants when implementing a follow/search consumer; do not
copy the repository-specific filenames blindly.

## Follow-state classification

Use three explicit semantic sets:

- **Not followed:** `Follow`, `Follow lại`, `Theo dõi`.
- **Success:** `Đã follow`, `Đang theo dõi`.
- **Unknown:** no trusted marker matched.

`Follow lại` is **not** success. It must enter the reload/verification path. An
unknown dump must never become silent success: recapture/reload once under a
bounded policy, then return `MANUAL_REVIEW` if it remains unknown.

After every Follow tap:

1. Capture a **new** UI dump; never classify from the pre-tap dump.
2. Accept only the success set.
3. For not-followed, reload the target profile with a bounded retry count.
4. If the target still exposes a not-followed marker after the cap, set the
   machine-scoped `FOLLOW_BLOCKED` gate and stop that machine's follow session.
5. Release/retain locks through the engine's `finally` path; never continue to
   the next UID after `FOLLOW_BLOCKED`.

## Queue-based offline testing

A FakeAdapter with `xml_queue` is useful for navigation tests, but the queue is
the source of truth. Count every `dump_ui()` call in the production path,
including `wait_for_node`, post-navigation classification, and post-tap
verification. A queue that is short or ordered for a different UID causes long
waits and misleading failures.

Useful invariants:

- Patch `random.shuffle` in a deterministic queue test, or generate the queue
  in the same order as the seeded shuffle.
- Test `follow_one_uid()` outcomes separately from `run_mode1()` state updates:
  the former returns an outcome; the latter calls `mark()` and consumes budget.
- Keep engine-only injectables (`busy_check`, `switcher_fn`, `identity_fn`)
  separate from config overrides in test helpers.
- Run the actual suite with the source core first:
  `PYTHONPATH="D:/Taadaa/automation-core/src;." python -m pytest ...`
  so an installed stale wheel cannot mask the checked-out core API.

## Search navigation safety

Never treat UiAutomator `@index` as a stable search-result identity. A live
TikTok variant exposed both the focused search `EditText` and the real exact-UID
suggestion with `index="0"`; a generic `wait_for_node(text=uid)` fallback then
selected the input itself and merely refocused it instead of opening the
profile.

Use a fresh-dump semantic result gate:

1. Normalize the target and candidate text exactly (`strip`, optional leading
   `@`, `casefold`); do not use substring matching for identity.
2. Exclude `android.widget.EditText` and every `editable=true` node, even when
   the live UI reports the input's `editable` flag inconsistently.
3. Require valid bounds and exactly one non-input exact candidate. Zero means
   keep polling within the bounded timeout; more than one means fail closed,
   never pick the first node.
4. Tap only after the guarded adapter rebinds the same semantic candidate from
   a fresh dump. Then verify the destination's exact profile identity (for the
   known profile UI, one `/id/sf5` handle) before opening a Follower tab or any
   account-affecting action.
5. Reuse the same result-selection helper in initial search and profile reload;
   leaving an old `index="1"` fallback in reload creates a second latent path.

Regression coverage must include the live-shaped collision (focused EditText +
real suggestion, both exact UID and `index="0"`) and an ambiguous two-result
case. Assert the suggestion center was tapped and the EditText center was not.
Do not use coordinates for the Follow button or follower rows. If search input
and search icon share a content description, recapture and distinguish the
input by class/editable/focus state or an explicit core adapter hook rather than
blindly tapping the same selector twice.

## Fresh UI capture: stale remote XML is a false-success hazard

A failed `uiautomator dump /sdcard/window_dump.xml` can leave the previous
remote file intact. Calling `cat` unconditionally then returns valid-looking but
stale XML; foreground process proof does not make that hierarchy fresh. This can
misclassify launcher/Profile/Feed state and authorize the wrong semantic input.

For every safety-critical capture:

1. Remove the exact remote dump path first.
2. Run a new dump and require its exit code to succeed.
3. Only then read the file; require `cat` success, a parseable `hierarchy` root,
   meaningful nodes, and package/resource identity for the intended app.
4. On the first fresh-capture failure only, call the canonical shared-core
   UiAutomator/ATX recovery helper under the same device/VPN/foreground/lease
   gate, then repeat the complete remove → dump → read → verify sequence.
5. After the bounded recovery is consumed, fail closed. Never accept the old
   remote file and never convert foreground/package-manager state into UI proof.

Add a synthetic regression where attempt 1 fails while stale XML exists and
attempt 2 returns fresh app XML. Assert stale XML is never returned, recovery is
called exactly once, and the remote file is read only after a successful dump.

## Guarded navigation-only live canaries

A no-side-effect canary is still a production operation. Use this release order:

1. Pin exact production HEAD and source hashes; statically prove the harness
   calls the production navigation closures rather than a copied/preconditioned
   substitute.
2. Prove no-authorization refusal, compile/AST checks, exact shell argv
   allowlists, synthetic fail-closed tests, and a Follow-sink denial scan.
3. Audit the exact current runner bytes, then mint a short-lived parent-owned
   one-shot authorization bound to run ID, machine, HEAD, expiry and nonce.
4. Immediately before every input, recheck exact lease ownership, VPN, app
   foreground/package and watcher generation. Rebind the semantic node from a
   fresh verified dump before tapping.
5. Persist only privacy-safe structural evidence: sanitized XML and synthetic
   blank-box images; never raw screenshot/XML, serial, proxy, IP, credential or
   handle values.
6. Treat the authorization as consumed even when the attempt blocks. A second
   attempt needs a new run scope, new exact-byte audit and new authorization.

When a canary exposes a production defect, do not hide it by teaching the
harness an alternate route. Write a RED production regression, fix the shared
production seam, update the local UI compatibility record, run focused + full
gates, audit, commit/push and verify the remote ref. Only then clone/re-pin a new
one-shot runner. A terminal block must retain the lock as inactive handoff under
the project's policy; reclaim only through canonical audited same-project
recovery, never by deleting aliases manually.

## Recovery and scope boundaries

The four-step consumer navigation ladder is bounded and fail-closed:

1. ATX/UIAutomator cleanup using the transport actually owned by the adapter.
2. One force-stop/relaunch.
3. One soft reboot only when explicitly authorized by config/policy.
4. Evidence-backed coordinate fallback only where the contract permits it;
   never for Follow or follower-item actions.

An audit finding that a recovery command may kill its own transport must be
verified against the adapter implementation. If the adapter shell is direct
ADB, record that evidence; if it routes through ATX/UIAutomator, move the
cleanup action to the independent transport instead of swallowing the failure.

## Live-readiness checks before calling a phase complete

Offline FakeAdapter tests are not proof of production readiness. Before
approving a phase, import every module reached by the CLI and verify:

- all referenced optional modes exist or are lazily gated;
- production acquires `automation_core.device_lock` and
  `automation_core.workbook` leases in the shared namespace;
- leases are released or retained according to the terminal result in
  `finally`;
- `MANUAL_REVIEW`, `SKIPPED_LOCKED`, `FOLLOW_BLOCKED`, and `CONFIG_ERROR` stay
  distinct in reports/state;
- the CLI non-dry-run path actually constructs the adapter and runs the mode;
- new UI selectors have a local compatibility record and regression test;
- mode-specific fixtures claimed as calibrated come from a real UI dump when
  the implementation plan requires probing.

A green unit suite plus `LIVE_NOT_IMPLEMENTED`, an eager import of a missing
mode, or a no-op `finally` is still a blocked phase, not an approved release.

## Audit evidence discipline

Audit the exact committed diff, not a dirty working tree. Before each audit,
run the relevant tests, compile/import checks, and `git diff --check`. After a
worker reports completion, independently inspect the commit and rerun the
verifier. Use Claude AG for routine audits, GPT-5.6 Sol as the normal fallback,
and escalate to Claude CLI only for difficult/high-risk or unresolved audits.
