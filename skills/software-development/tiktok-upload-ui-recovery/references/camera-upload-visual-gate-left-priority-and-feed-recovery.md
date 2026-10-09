# Camera Upload Visual Gate: Left Priority, Profile/Feed Drop Recovery & Handoff Signatures

## Context
On Samsung Galaxy farm devices (e.g., SM-G930F/W8), TikTok builds frequently place the upload/gallery thumbnail in the bottom-left or left region of the camera surface, while the right region often contains CapCut template / effect buttons or template previews.

If `_tap_visual_camera_upload_entry` prioritizes `right_targets` over `left_targets`, tapping right frequently triggers the CapCut template modal (`use_template` / `bq3`) rather than opening the media picker gallery.

## Pattern & Fix

### 1. Prioritize Left Targets Over Right Targets
In `scripts/tiktok_workflow/state_machine.py` -> `_tap_visual_camera_upload_entry`:
- Build `left_targets` with L (`x=0.145, y=0.82`) and BL (`x=0.11, y=0.95`).
- Sort `left_targets` by non-dark pixel ratio descending.
- Build `right_targets` with R (`x=0.875, y=0.83`).
- Order candidates: `ordered_candidates = left_targets + right_targets`.
- Only tap right targets if no left candidates are non-dark.

### 2. Recovery on Template Dismiss Drop to Feed or Profile
When CapCut template modal is dismissed (`_dismiss_capcut_template_surface`):
- Occasionally, dismissing the template pops both the template AND the camera, returning the UI to the TikTok Home feed root or the Profile root (`@username`).
- A naive check `if not self._is_camera_surface_xml(...) return False` immediately fails closed into an unnecessary soft reboot.
- Correct recovery:
  1. Check `create_btn = self._find_bounded_create_button(current_xml)`. If present, tap the center create button to re-enter camera surface.
  2. If on Profile surface or `create_btn` is not matched, check `home_tab = self._find_home_tab_center(current_xml)`. Tap Home tab ("Trang chủ") to return to Feed, then re-acquire the create control (+).

### 3. Video Pick Recovery Handoff Signature Mismatch
In `scripts/tiktok_workflow/run_post.py` -> `_load_video_pick_recovery_binding`:
- Checkpoint validation (line ~788) accepts `signature == "VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED"`.
- However, the handoff ledger filter (line ~873) and recapture signature validation (line ~884) hardcoded:
  `candidate_signature == "VIDEO_PICK_PROFILE_VIDEO_ACTION_SHEET"` and `recapture_signature == "VIDEO_PICK_PROFILE_VIDEO_ACTION_SHEET"`.
- Fix: Expand both checks to accept tuple of valid candidate/recapture signatures:
  `("VIDEO_PICK_PROFILE_VIDEO_ACTION_SHEET", "VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED")`.

### 4. Unit Test Verification Pitfall
When changing candidate priorities:
- Unit tests using synthetic/mock dual-thumbnail screenshots (`tests/test_tiktok_workflow.py`) will fail if their assertions expect Right thumbnail to be tapped first.
- Tests to update:
  - `test_tap_visual_camera_upload_entry_stops_if_camera_lost_after_dismiss_template`: expect initial tap on Left `(156, 1574)`, dismiss tap on `(84, 204)`, assert Right `(945, 1593)` not in `adapter.taps`.
  - `test_video_pick_camera_thumbnail_alternates_retry_targets`: expect retry sequence `[(118, 1824), (945, 1593), (118, 1824)]` instead of `[(945, 1593), (118, 1824), (945, 1593)]`.
