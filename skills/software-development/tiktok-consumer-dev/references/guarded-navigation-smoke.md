# Guarded navigation-only smoke tests

Use this pattern when a live Android/TikTok smoke must exercise navigation while a nearby destructive action (Follow, Post, Delete, account switch, payment) is explicitly forbidden.

## First classify the finding: harness defect or production defect

A helper is not an end-to-end flow. Before patching production:

1. Trace the real caller and record the UI state immediately before the helper call.
2. Make the smoke establish that exact precondition.
3. Compare the helper's observed failure with the real call path.
4. If the throwaway harness invoked the helper from a different state, classify it as `HARNESS_PRECONDITION_MISMATCH`; do not create a production regression/commit for it.

Session-proven example: Mode 2 calls `_open_follower_tab` from Feed. A smoke invoked it while still on the account's Profile, so Search could not be found. Live XML/PNG proved Profile + a semantic Home sibling. The production finding was therefore disproved; the corrected smoke must navigate Profile -> Home/Feed before calling the helper.

This distinction prevents a green unit suite plus a misleading live harness from manufacturing a fake production bug.

## Separate authorization tiers

Treat these as different mutation scopes:

- package launch;
- navigation taps/text/back;
- business action (Follow/Post/Delete/etc.);
- recovery (force-stop/reboot/data mutation).

Permission for one tier does not imply the next. A navigation-only smoke must never enter the business-action or recovery tiers.

## Guard the input sinks, not only the call sites

A static scan or post-run ledger alone cannot prove that a broad production helper did not reach an unexpected input primitive. Wrap the adapter and enforce policy at every input/control sink:

- `shell`, `tap`, `swipe`, `type_text`, `keyevent`;
- `press_back`, `back`, `press_home`;
- `launch_app`, `force_stop`, `exec_out`;
- any direct subprocess/ADB alias reachable from the imported helpers.

Use an explicit state machine. Each allowed input must:

1. re-dump fresh XML;
2. uniquely rebind the expected semantic node;
3. reject stale or duplicate candidates;
4. verify the incoming coordinates equal that node's current center;
5. consume a one-shot stage token;
6. run the VPN/target/lease gate immediately before input;
7. append a redacted ledger entry.

For navigation-only Follow smoke, reasonable stages are `PROFILE_TAB`, `HOME_TAB`, `SEARCH_ICON`, `SEARCH_INPUT`, `EXACT_RESULT_ROW`, `FOLLOWER_TAB`, and `RESTORE_FEED`. No raw coordinate fallback.

### Hard-deny destructive controls

Deny before the sink if text/content-desc/resource-id/classification matches any destructive action. For Mode 2, deny the row action resource-id (`tcj` / `FOLLOWER_FOLLOW_BUTTON_RESOURCE_ID`) and exact normalized markers from `FOLLOW_BUTTON_TEXT`, `FOLLOW_BACK_TEXT`, `FOLLOWED_TEXT`, including `Đã follow`. Allow `Follower` only when it is the unique clickable relation-tab resource after the exact profile-identity gate; do not use a broad `follow` substring rule.

Use a terminal exception derived from `BaseException` (for example `SafetyAbort`), caught only by the top-level harness. Production helpers may contain `except Exception`; a normal exception can be swallowed and converted into `False`, allowing a fallback input. Also latch `denied=True`, and test that no input occurs after denial.

### Shell allowlisting

Validate argv as a list of strings, never a joined shell command. Reject control characters and shell metacharacters in every argument. Prefer exact argv tuples over first-token allowlists. Restrict `cat` to the one UI-dump path; unrestricted `cat` is a data-leak path. Test newline, separators, substitutions, redirects, and arbitrary path/command variants.

## Own-profile and target-state proof

An `sf5` username node alone does not prove the account's own Profile root. Require a composite proof, such as:

- TikTok is the exact foreground package;
- exactly one nonempty `sf5` identity node;
- unique clickable bottom-nav Profile node is selected;
- unique clickable Home sibling is present in the bottom-nav region;
- follower-list recycler is absent.

An external user's profile may also contain `sf5`; reject it when the own-Profile bottom-nav proof is missing or unselected.

## Privacy-safe evidence

Raw UI XML and screenshots can contain account handles, follower identities, avatars, queries, and badges. Hash raw captures in memory, but persist only:

- sanitized XML retaining safe structural fields while replacing non-allowlisted text/content-desc with hash prefixes;
- blank-canvas diagrams containing constant labels and geometric outlines only.

Do not crop or copy original screenshot pixels into an allegedly sanitized artifact; a node rectangle can still include adjacent PII.

## Watcher/VPN evidence must be generation-bound

A Scheduled Task marked Running, live PIDs, or an ordered status list is not enough. Events can be stale or stitched across concurrent generations. Bind readiness evidence to a newly created watcher run directory and its root PID/process creation time/process tree, then require one event number in strict order through `WATCH_EVENT_VERIFIED_SUCCESS`. Correlate machine + in-memory serial + time epoch; redact identifiers in artifacts.

If the watcher repeatedly reports mapping reload errors, first classify file accessibility without reading cells or secrets. An exact workbook left open in Excel can hold the canonical mapping and produce `PermissionError` while watcher processes remain alive. This is a mapping-owner problem, not evidence of a TikTok navigation or VPN implementation bug. Reuse `android-device-automation/references/gan-proxy-watcher-ops.md` for watcher process and lock semantics.

During a high-risk smoke, eliminate watcher/device-lock TOCTOU: the approved execution design must show who owns the device at every transition and why the watcher cannot reclaim it between the final lease check and ADB input.

## Two-phase audit gate

Do not repeatedly seek live authorization from an abstract plan that itself requires an exact-script audit.

1. **Phase 1, offline only:** one worker writes the guarded harness and fake tests; live APIs are disabled.
2. Parent independently verifies exact files, hashes, call graph, tests, protected paths, and no live side effects.
3. An independent auditor reviews the exact harness bytes/test evidence and returns `APPROVED`.
4. Only then issue a one-shot Phase-2 authorization token and run the bounded live attempt.

A plan audit can validate architecture, but it cannot substitute for the exact-script audit. Worker completion and exit code are not acceptance evidence.

## Terminal gate

`VERIFIED_SUCCESS` requires the new run's own manifest to prove all mandatory preconditions, generation/lease/VPN/input-ledger/privacy/final-state gates and `follow_action_invoked=false`. A report file alone is insufficient. On failure, retain fail-closed handoff evidence; do not retry the same live attempt merely because the harness or worker exited.

## Session outcome boundary

The investigation that produced this reference established the harness-precondition mismatch and the mapping-workbook lock diagnosis, but the corrected live smoke did not reach terminal success before the tool budget ended. Treat the safety architecture above as audit requirements; do not claim that the unexecuted recovery sequence itself was live-proven.
