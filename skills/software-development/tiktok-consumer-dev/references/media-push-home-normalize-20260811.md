# MEDIA_PUSH → VIDEO_PICK normalize-Home fix (2026-08-11, commit 4b3d5fd)

Full detail for the m74 fix: after MEDIA_PUSH, TikTok can resume on **Profile
root** (`hồ sơ`) instead of Home. `_wait_for_feed` accepts ANY root surface
(including Profile) as "feed ready", so checkpoint MEDIA_PUSH passes — but
VIDEO_PICK requires Home (`trang chủ`) with a **labelled bottom-centre create
control** (`+`/`Quay`/`Tạo`/`Create`). Profile has no such control →
`_find_bounded_create_button` → None → repeated
`VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED` (m74,
`run_ce061606c21e153d03_20260811_063353`).

## Fix shape (generic, all machines — no machine-ID branch)

1. `_find_home_tab_center(xml)` — semantic bottom-nav Home tab selector:
   `resource-id` suffix `home_tab` OR text/content-desc `Trang chủ`/`Home`,
   bounded to the bottom strip (node top ≥ 75% of screen height). A
   mid-screen `Trang chủ` label (feed card) is never the tab.
2. `_is_home_surface_with_create_control(xml)` — VIDEO_PICK pre-gate: root
   surface (`_is_tiktok_root_surface`) AND home/feed marker AND
   `_find_bounded_create_button` found. Profile-only root never passes.
3. `_normalize_to_home_for_video_pick(adapter, xml, *, timeout=60)` — bounded
   loop: dump → verify gate → if pass: artifact + checkpoint VERIFIED →
   return True. Else tap Home tab semantically (max 3 taps; one bounded Back
   only for non-root subpages like sound detail; root surfaces — including
   Profile — never Back). Exhausted budget → **fail closed**:
   checkpoint `media_push_home_normalize` state FAILED, error
   `[VIDEO_PICK_HOME_NOT_REACHED]`, `is_ui_unavailable=True`, artifact
   `media-push-home-normalize-failed.png` → handler returns False → transition
   goes FAILED/MANUAL_REVIEW, NEVER VIDEO_PICK.
   Sparse-XML compat: visual feed gate (`_visual_feed_surface_visible`) counts
   as Home evidence ONLY when XML has no Profile markers
   (`sửa hồ sơ`/`thêm tiểu sử`/`edit profile`/`add bio`).
4. Wire into `_handle_media_push` AFTER `_wait_for_feed` succeeds, before
   `return True` (config `home_normalize_timeout`, default 60).

Registry: `COMPAT-VIDEO-PICK-004` in `docs/tiktok-ui-compatibility.md`.
Regression tests (5): `test_media_push_normalizes_profile_root_to_home_before_pick`,
`test_media_push_normalize_fails_closed_without_create_control`,
`test_media_push_handler_does_not_fall_through_when_home_normalize_fails`,
`test_media_push_home_with_create_control_passes_without_tab_tap`,
`test_find_home_tab_rejects_non_bottom_nav_trang_chu`.
TDD evidence: RED = 5 failed (AttributeError, methods missing) → GREEN 7 passed
(`-k 'media_push or home_tab'`) → full file 337 passed (332 baseline + 5).

## Fixture contract: XML-bounds helpers need a full-screen node

`_find_bounded_create_button` and `_find_home_tab_center` derive screen
size from the MAX node bounds in the dump. Test fixtures MUST include a
full-screen reference node `<node bounds="[0,0][1080,1920]" />`, exactly like
the pre-existing fixture at `test_bounded_create_recovery_requires_bottom_center_semantic_control`.
Without it, screen_height collapses to the button's own bounds and the
bottom-strip / bottom-centre ratio checks silently reject valid controls
(observed: create button at (540,1857) rejected because screen_width=648 from
the button itself; mid-screen `Trang chủ` accepted because threshold = 75% of
480). Real uiautomator dumps virtually always carry a full-screen root frame.

## The patch-tool indentation corruption (hit TWICE this session)

Hermes `patch` (mode=replace) **mangled indentation on large CRLF Python
blocks**: every line of the replacement got extra leading spaces
(+8/+16), producing `IndentationError: unexpected indent` — including on a
block whose `old_string` was unique and asserted. This is a distinct failure
from the backslash-doubling pitfall in `references/crlf-safe-restore-and-append.md`.
Small/short replacements (few lines) succeeded; ~200-line method insertions
failed both times. The mangled text is written to disk, and a *failed*
follow-up terminal command that also contains the restore (`git checkout --`
chained with `&&`) can abort BEFORE the restore runs (bash heredoc parse error
aborts the whole line) — leaving corruption in place.

Workaround (proven):
1. Restore: `git checkout -- <file>` as its OWN simple command, then verify
   `git status --short` shows it clean.
2. Apply via byte-exact Python splice: write_file a temp script with
   `src.count(anchor_old) == 1` assertion + `src.replace(anchor_old, new_block, 1)`,
   run `python <script>.py`, `python -m py_compile <file>`, `git diff --stat`
   (expect pure insertions), delete the script.
3. Keep `new_block`/`anchor_old` inside the script file (write_file handles
   Vietnamese + CRLF content safely); NEVER inline as a bash heredoc — long
   heredocs fail in git-bash (`unexpected EOF while looking for matching '`),
   which also silently skips any `&&`-chained restore in the same command.
4. If a mangled block is already in the working tree, a uniform
   `lines[i] = lines[i][4:]` dedent-by-4 of the exact line range (verified via
   py_compile) repairs it without a full restore.
