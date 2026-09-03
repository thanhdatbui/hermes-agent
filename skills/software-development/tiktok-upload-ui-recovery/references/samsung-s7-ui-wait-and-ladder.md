# Samsung S7 UI wait + recovery lessons

Session-derived reference for slow SM-G930 farm devices. Keep this detail here rather than making it a one-off skill.

## Diagnosis split

1. **UI render/read race:** picker, editor, composer, avatar edit, or Post controls appear late. A short element wait can produce `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED` or equivalent false negatives.
2. **UIAutomator service failure:** `non_xml_ui_dump`/null XML/exit 137 or `Killed` is not a normal timeout. Run the ladder immediately; B1 is ATX/uiautomator kill.
3. **Wrong surface:** if the dump/screenshot proves Profile or a video-detail surface, waiting longer will not create a `+` button. Normalize only with semantic evidence or classify as a surface/navigation issue; never tap a guessed coordinate.
4. **Permission overlay:** Android packageinstaller can own foreground after the create tap. For TikTok media permission, semantic-allow the popup first, then re-check TikTok foreground and picker. Do not fail on the foreground gate before processing the permission dialog.

## Timeout policy

- UI XML capture and Android/app startup: 60s.
- UI element polling and render-state polls (picker, upload entry, video tile, Next, editor, composer, avatar edit/picker/crop, Post preview, camera-to-gallery): 60s by default on S7.
- Keep atomic ADB transport commands (`tap`, `back`, `wm size`, individual shell actions) short; increasing those blindly to 60s can hide transport hangs.
- A 60s wait is not permission to tap: every action still needs semantic/resource/screenshot evidence and post-action recapture.

## Ladder placement

Startup UI failure occurs before the adapter is constructed. Route B1 using `self.context.adb_client`, not `adapter._adb`; otherwise the ladder silently has no ADB handle and the run can stop at `CONNECT_DEVICE` without recovery. After B1, continue the bounded B2/B3 policy and preserve evidence/lock state.

## Verification and release

- Verify the newest report, not an old artifact: require `status=SUCCESS`, `post_submission_state=ACCEPTED`, and `post_verified=true` for a successful upload.
- Run the target workflow test file with the target machine's Python, then `git diff --check`.
- User's release gate: commit + push after the full relevant pytest suite is green; live-run is verification after release. If live exposes a bad fix, revert immediately to the prior git revision and then fix forward.
- For a machine-specific outlier such as m74, prefer evidence/test-only analysis and avoid committing a farm-wide workaround unless independently reproduced and covered by regression tests.

## User interaction preference

Respond in concise Vietnamese, report the exact failing surface/signature and evidence path, and act on fixes without repeatedly asking for permission when scope is already clear. Do not dump raw English logs; summarize the core.
