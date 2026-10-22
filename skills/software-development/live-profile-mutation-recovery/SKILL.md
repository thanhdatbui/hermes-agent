---
name: live-profile-mutation-recovery
description: "Use for live TikTok profile mutation recovery."
---

# Live TikTok Profile Mutation Recovery

Use this class-level workflow for pinning videos, changing avatars, editing profile metadata, or any other live mutation on a farm Android device when target identity, UI state, and post-action result must be proven.

## Non-negotiable completion contract

A dry-run, worker exit code, queue state, workbook flag, or local asset marker is not completion proof. Completion requires:

1. Exact machine/serial mapping from the canonical O(1) inspection tool.
2. Fresh UI evidence showing the intended account and intended profile surface before mutation.
3. The live action performed through the bounded runner with the correct device lock.
4. Independent post-action read-back from the exact account.
5. A fresh screenshot inspected with vision/OCR showing the expected result and no popup, black screen, clipping, or wrong account.

If any identity or read-back gate is missing, report `BLOCKED` with the actual error and evidence path. Never infer success.

## Runner lifecycle and exact-account closeout contract

The canonical runner must capture its own post-mutation evidence **before** force-stop/HOME/teardown and must carry the target identity through that capture. A later ad-hoc verifier that relaunches TikTok, guesses a profile tab, or uses an unbound account switcher can land on another farm account and create a false failure or false success. Therefore:

1. Bind `machine -> serial -> workbook row/slot -> target username -> source asset` in the run artifact before launch.
2. Confirm the target identity on the live Profile immediately before mutation.
3. Perform the mutation, then capture fresh UI XML and screenshot on that same target surface before cleanup. Persist both under the same attempt/run ID.
4. Verify exact username/display identity and expected avatar/pin marker from those fresh artifacts. Only after this gate may the runner update workbook state or teardown.
5. If the runner's current lifecycle tears down first, classify the result as `UNPROVEN`; the durable fix belongs in the canonical runner's closeout hook, not in a one-off script that taps guessed coordinates after the fact.

`exit=0`, `verified=True`, `FORCED_REPLACED_VERIFIED`, `Avatar=OK`, or a successful crop/save log are mechanical receipts only. They cannot override `post_verified=false`, a black/Home/Splash screenshot, or a screenshot showing another account. See `references/avatar-runner-lifecycle-and-identity-binding-20261021.md`.

## Operator communication after a failed closeout

When the operator asks why work stopped or expresses frustration, do not re-explain the whole history or ask the already-settled choice again. State the exact design failure in one sentence, distinguish mechanical action from semantic closeout, and continue the bounded canonical recovery. Return only `DONE` with fresh exact-account evidence or `BLOCKED` with the literal artifact/error; do not stop merely because the first verification path failed.

## Recovery sequence

1. **Classify the failure.** Separate transient transport/ATX/session errors from identity or UI-state errors. `UI_DUMP_INVALID` during profile navigation is not proof of a safe target; treat it as a blocked mutation until the screen is captured and inspected.

### User-confirmed target and no-repeat discipline

When the user has already selected an option (for example, avatar option 1), bind that choice to the exact source asset and proceed without asking the same question again. Keep status messages short while a bounded live run is active; report only the state, evidence, blocker, and next action.

### Exact-account post-upload gate

Runner claims such as `exit=0`, `verified=True`, `FORCED_REPLACED_VERIFIED`, `Avatar=OK`, or `post_verified` from a batch report are mechanical evidence only. They do not prove that the correct account is visible or that the intended image is displayed. After any profile mutation, the verifier must independently confirm the exact machine/serial and target username/display name on a fresh profile screenshot. A screenshot of another account, SplashActivity, Launcher, a black frame, or an unconfirmed switcher is invalid evidence and must produce `UNVERIFIED`/`FINAL_BLOCKED`, even if the runner succeeded. Do not attach or present such an image as completion proof.

See `references/avatar-exact-account-closeout-20261021.md` for the failure pattern and the required evidence fields.
2. **Inspect O(1).** For machine `N`, run `python D:/Taadaa/tools/inspect_machine.py N`. Record serial, focus, screen state, battery, Wi-Fi and proxy. Do not broad-scan the farm.
3. **Capture before cleanup or retry.** Acquire the device lock, capture the current screen, run WinRT OCR, and inspect the screenshot visually. If focus is `SplashActivity`, feed, a public profile, another account, or an unknown surface, do not tap through it.
4. **Use ATX session capture as the primary UI XML route.** Construct `AdbClient(adb_path=ADB_BIN, serial=serial)` and call `capture_atx_session_ui(...)`. The persistent ATX session route can return `VERIFIED_XML` even when direct device-local `/dumpUI` returns 404. Do not silently downgrade to shell UiAutomator dumping on S7/Android 7/8.
- Bound recovery. If the exact target can still be safely re-verified, allow one code-level recovery such as ATX session rediscovery/reset or adapter settling retry (up to 3 attempts with 1.0s delay checking `xml.lstrip().startswith(("<", "<?xml"))`), then one bounded retry.
- Preempt stale device locks safely. For operator-driven CLI mutations on single machines, use `operator_device_lock(machine=N, serial=serial, force_preempt=True, timeout=30.0)` to reclaim orphaned locks left by timed-out or aborted runs.
- Continuous user transparency during background runs. When dispatching workers or running bounded live interactions (>30s) in the background, send an immediate checkpoint status message before handing control to the background runner so the user is never left wondering if the coordinator is frozen.
- Fail closed. If XML remains invalid, account identity is unknown, or the runner reaches its retry bound, stop the mutation and preserve the failure screenshot/OCR/log.
7. **Verify post-action.** Re-dump the profile through ATX, parse the exact target account, verify the mutation marker/state, and capture a fresh screenshot for vision inspection. Only then report success.

## Evidence rules

- Keep failure and success screenshots separate and use absolute paths.
- Inspect a screenshot before attaching `MEDIA:`; confirm the intended Profile/Switcher, expected new content, and absence of visual defects.
- Report the exact exception, not a vague “automation failed.”
- Do not attach old screenshots or reuse prior session evidence.

## Farm safety pitfalls

- Never treat `dry_run=True` as a live canary.
- Never mutate while the app is on a different public profile or while `SplashActivity` is still active.
- Never use direct ADB input commands as an emergency way through an error screen.
- Never change account/workbook/queue state to `DONE` before real-device read-back.
- Do not write a skill entry describing an unvalidated worker patch as a reliable fix.
- S7 Profile Screen Edit Entrypoint & Button Geometry: On Samsung S7 (1080x1920) center-avatar layouts, the button row sits strictly BELOW the follower stats row (`y=744`), centered at `y ≈ 865` (`x ≈ 315` for 'Sửa hồ sơ', `x ≈ 540` for '+ Thêm tiểu sử'). NEVER tap `y ≈ 660` (empty space between username and followers) or fallback to `(72, 148)` (toolbar top-left); on modern TikTok S7 UI, `(72, 148)` is the 'Find Friends' icon, which triggers the fatal 35-step `FindFriendsPageActivity` loop (`exit_2`).
- Bio-less Profile "Sửa hồ sơ" Unlock Invariant: On accounts with no bio yet, TikTok suppresses 'Sửa hồ sơ' and displays only `+ Thêm tiểu sử` at `(540, 865)`. The runner MUST match `+ Thêm tiểu sử` (`\+\s*th[eé]m|tid\w{0,2}\s*s|th[eé]m\s*ti|tieu\s*su`). In `BIO_EDIT`, if `not bio_saved`, it must write and save a simple bio (e.g. `TARGET_BIO or "Xin chao"` via AdbKeyboard Base64). Once saved, TikTok returns to Profile with the 'Sửa hồ sơ' button revealed, allowing normal rename execution.
- Profile Username OCR vs Bio Placeholder Collision: Under the profile buttons, TikTok often shows placeholder suggestion text starting with `@` (e.g. `@ Tài khoản của tôi nói về...`). If `nickname_on_profile()` checks only `t.startswith("@")`, it parses the placeholder as the active username (e.g. `@taikhoancuatoin6ive`), falsely concluding the account is wrong and looping in Switcher 3 times (`exit_2`). Always enforce `" " not in t.strip()[:10]` and exclude `"tai khoan"`, `"nhac den"`, `"noi ve"`, `"chia se"` from username candidates.
- Watchdog Re-queue Contract: Only verified accounts with valid proof PNG are committed to state JSON. Failed runs (exit_1, exit_2, max steps) must never write cooldown state, ensuring they are automatically re-queued in subsequent 15-minute watchdog cycles.
- Name Classification Preservation: When checking stereotyped display names, ensure regex rules (such as numeric suffix or username-like patterns `[a-z0-9_.]+\d+`) are strictly ASCII-only so Vietnamese diacritic names (e.g. 'Đỗ Văn Hoàng', 'Trần Tiến Nghĩa', 'An', 'Hà') are never classified as username-like or discarded. Always fail-closed on checker exceptions and emit structured telemetry (`_stereotype_reason`) for every decision.
- Cold-boot Splash Tolerance: Never trip `MAX_SAME_STATE` aborts on `SplashActivity` / minimal text (`len(lines) <= 3`) during app launch; 4G proxies take 25–35s to load. Expand splash tolerance to 8 steps (~35–40s) and avoid pressing `BACK` during splash.
- Profile Username OCR Missing `@` vs Nickname Collision: Never allow `is_target_user(t)` on lines without `@` in `nickname_on_profile()`. If `t` does not start with `@`, loose fuzzy matching matches the *new display name* itself (e.g. `Thạch Tâm` vs `thachtam02`), misidentifying the name as the username and failing with `name = None`. The username line must strictly start with `@` (`t.startswith("@") and b[1] < 750`). Nickname candidate boxes must filter out standalone numbers (`re.fullmatch(r"\d+", t)`) and noise text (`tin vui`, `ban dang`, `tra hay`). Always use a post-save profile scan (`if saved: any(is_target(t) for t, b in boxes if 200 <= b[1] <= 700)`) to confirm success.
- Bio-less Profile "Sửa hồ sơ" Unlock Invariant: On accounts with no bio yet, TikTok suppresses 'Sửa hồ sơ' and displays only `+ Thêm tiểu sử`. If the rename runner backs out of `BIO_EDIT` because `BIO_REQUESTED == False`, it enters an infinite ping-pong loop between `PROFILE` and `BIO_EDIT` until reaching max steps. If `not saved`, the runner must automatically unlock 'Sửa hồ sơ' by saving a unique, non-duplicate Vietnamese bio matching the identity (e.g. `Chào bạn, mình là {NEW_NAME}` via AdbKeyboard Base64). Once saved, TikTok returns to Profile with the 'Sửa hồ sơ' button revealed.
- TikTok 7-Day Name Change Cooldown: Detect in-page cooldown warnings (`tiep tuc thay doi`, `tiep tvc thay ddi`, `sau ngay`) immediately upon entering `NAME_EDIT`. Tap cancel and abort fail-closed with `cooldown_7d` instead of wasting 5 retry iterations against a disabled Save button.
- Find Friends Trap & Dual-Mode Profile Layouts: On center-avatar layouts (follower Y > 600), the top-left icon `(72, 148)` is 'Find Friends', NOT the edit pencil. Tapping it opens suggested accounts (leading to stranger profiles). Only use `(72, 148)` when follower Y < 600 (left-avatar layout); for center-avatar layouts, fallback to the center button `(315, 865)`. If 'Find Friends' appears, immediately press `BACK`.
- Eliminating Loose Name Heuristics: Never accept bare diacritic checks (`has_vietnamese and not digits`) as proof that a profile name is valid. Chip prompts like "Bạn có tin vui?" produce OCR fragments like `"Ban cé"`, falsely marking dirty accounts as `ALREADY`. Only accept direct `NEW_NAME` matches or smart generator verification.
- Bio Edit Screen Misclassification Trap (`@ Nhắc đến`): On the Bio edit screen (`BIO_EDIT`), TikTok displays a `@ Nhắc đến` (Mention) action chip. If `classify()` prioritizes `PROFILE` by checking `l.startswith("@")`, it falsely classifies `BIO_EDIT` as `PROFILE`, causing the runner to search for edit buttons on a keyboard screen and aborting with a 5-step PROFILE loop (`exit_2`). Always classify `BIO_EDIT` before `PROFILE` when `@ Nhắc đến` or bio editing instructions (`chinh sua tieu`, `tieu sd`, `160/80` limit) are detected.
- Cronjob Topic Thread-Safe Delivery Invariant: Recurring watchdogs (like `tiktok-rolling-rename-watchdog`) must have their `deliver` field explicitly set to `platform:chat_id:thread_id` (e.g. `telegram:1076231895:296400`) rather than relying on automatic origin inference, ensuring alerts continue posting to the designated discussion topic even after the operator executes `/new`.
- Rename Watchdog ADB Bridge Hang vs FindFriendsPageActivity Loop (`exit_1` vs `exit_2`): When rename watchdog fails with `exit_1` and no report JSON, the root cause is ADB socket hang causing unhandled `subprocess.TimeoutExpired` outside try-except; fix by `adb kill-server && adb start-server`. When failing with `exit_2` (`vuot qua 35 buoc`), the root cause is fallback tapping `(72, 148)` which hits the 'Find Friends' icon instead of the pencil, opening `FindFriendsPageActivity` where a single BACK key only dismisses the keyboard; require explicit `FIND_FRIENDS` classifier and double BACK escape.

## Avatar-specific semantic gate

Mechanical upload success is not semantic asset success. Before changing an avatar, open and inspect the exact resolved source file used by the runner; never trust a proposal canvas label, filename, folder number, or prior description. Bind `target account -> source folder -> exact avatar path` before upload, then bind the same account to a fresh Profile screenshot after upload. A successful push, crop-save, `exit=0`, `verified=True`, `FORCED_REPLACED_VERIFIED`, or workbook `Avatar = OK` proves only the mechanical flow. It does not prove that the intended image was selected.

Verify profile fields independently: a Bio can be confirmed while the Avatar is wrong or unproven. Report `Bio: confirmed` and `Avatar: incorrect/unproven` separately. If source and post-action semantics disagree, report `BLOCKED` or `UNPROVEN` and do not treat the workbook flag as final. See `references/avatar-source-semantic-verification-20261020.md`.

## Supporting detail

See `references/live-profile-mutation-atx-recovery-20261020.md` for the validated ATX-vs-direct-`/dumpUI` observation, evidence sequence, and exact failed-live-run signature from a real machine.
See `references/avatar-source-semantic-verification-20261020.md` for the avatar-specific source-asset gate and the false-success pattern where the runner uploaded a canopy image while the proposal described a cat.
See `references/profile-standardization-top-video-pin-and-activity-wake-trap-20261022.md` for the mandatory top-view video pinning contract in channel standardization ("chuẩn hoá kênh"), the False-Positive Pinned Badge trap, and the TikTok SplashActivity launch package invariant.
See `references/tiktok-s7-profile-edit-pencil-coordinates-20261020.md` for the Samsung S7 Profile toolbar pencil icon coordinate invariant `(72, 148)` and root-cause analysis of the 5-step PROFILE loop abort.
See `references/tiktok-profile-no-bio-add-bio-button-variant-20261021.md` for the bio-less Profile variant (`+ Thêm tiểu sử` vs Find Friends trap) and dynamic button resolution.
See `references/cold-boot-splash-loading-tolerance-20261021.md` for the 4G proxy cold-boot splash loading tolerance invariant and prevention of premature UNKNOWN exit_2 aborts.
See `references/watchdog-requeue-and-stereotyped-name-classification-20261021.md` for the watchdog re-queue state machine contract, Vietnamese diacritic name preservation invariant, and structured classification telemetry.
See `references/tiktok-profile-ocr-username-and-loose-heuristic-traps-20261021.md` for username `@` OCR drop handling, the dual-mode layout Find-Friends trap avoidance, and loose name heuristic elimination.
See `references/tiktok-bio-edit-screen-misclassification-and-topic-delivery-20261021.md` for the Bio Edit screen `@ Nhắc đến` misclassification root cause and the cronjob topic thread delivery binding invariant.
See `references/tiktok-profile-rename-cooldown-and-bio-unlock-20261021.md` for the 7-day display name cooldown detection, bio-less 'Sửa hồ sơ' unlock invariant, and profile username OCR collision fixes.
See `references/tiktok-rename-profile-bio-edit-pingpong-loop-20261021.md` for the root-cause analysis and fix of the 35-step PROFILE-to-BIO_EDIT ping-pong loop caused by matching bio chips during rename-only runs.
See `references/rename-watchdog-adb-bridge-hang-and-find-friends-trap-20261022.md` for ADB bridge stale socket `exit_1` triage, the `FindFriendsPageActivity` loop trap, and the realist multi-class failure reporting contract.
