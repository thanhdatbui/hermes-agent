# Independent diff review — Tiktok-video avatar contract fix (2026-08-15)

Read-only review (no edits, no device/ADB/TikTok/farm/upload, no
credentials/workbooks) of the uncommitted diff vs HEAD in
`scripts/tiktok_workflow/media_manager.py`,
`scripts/tiktok_workflow/state_machine.py`, `tests/test_tiktok_workflow.py`.
Repo `D:\Taadaa\Tiktok-video`, branch main, ahead of origin by 6 commits,
working tree dirty ONLY in those 3 files. Verdict: **APPROVED**.

## Diff summary (18 insertions, 14 deletions)

1. `media_manager.py` — removed duplicate `"shell"` first arg from
   `_adb.shell([...])` in `purge_media_rows` (157-166), `delete_remote_glob`
   (292-293), `touch_remote_file` (304-305).
2. `state_machine.py` — `photo_album_labels` reordered to
   `("Pictures", "Camera", "Hình ảnh", "Images", "Ảnh")` (6684); comment
   rewrite at the first-image-tile tap (6721-6725).
3. `tests/test_tiktok_workflow.py` — `test_avatar_picker_opens_photo_album_
   when_download_is_absent` replaced by `test_avatar_picker_prefers_pictures_
   album_when_available` (1620-1683).

## Evidence checks that produced APPROVED

### 1. AdbClient.shell usage — installed-package ground truth
`automation_core/adb.py:206-207` (installed at
`C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages\automation_core\adb.py`):
```python
def shell(self, args: Sequence[str], *, timeout=None, check=False) -> AdbResult:
    return self.run(["shell", *args], timeout=timeout, check=check)
```
So the OLD code executed `adb shell shell content delete ...` → guaranteed
`shell: not found`. The diff fixes a real live bug (these helpers are called
from the avatar cleanup chain, state_machine.py:5534-5538). Repo-wide grep
`shell(\s*\[\s*"shell"` → zero stragglers; `device_transport.py` raw
`"shell"` argv entries are correct (direct subprocess `adb ... shell ...`).

### 2. Pictures-first ordering vs docs
- Push target: `/sdcard/Pictures/av_<safe>_<epoch>.<ext>`
  (state_machine.py:5514-5517) — consistent with `"Pictures"` first label.
- Machine-4 observation encoded at 6681-6683: the "Ảnh" album IS Pictures
  (picker has no Camera album).
- `docs/tiktok-ui-compatibility.md` has NO Pictures-album section and NO
  COMPAT-AVATAR-007 heading (grep: headings are -001..-006 at lines
  82/101/119/264/293/315/333/354). No doc section forbids the new ordering →
  no contradiction, only a doc-coverage gap.

### 3. Test coherence
- New test's fake adapter returns True for album tap ONLY when
  `label == "Pictures"` (line 1662); asserts `album_attempts[0] == "Pictures"`
  and `"Pictures" in caplog.text` — genuinely exercises the new ordering.
- `_wait_for_element(resource_id="o_9")` returns center (924,1842); final tap
  asserted as `adapter.taps[-1] == (924, 1842)`.
- Focused run: `pytest -k "test_avatar_picker_prefers_pictures_album_when_
  available or test_avatar_recent_fallback_prioritizes_newest_image_tile"`
  → 2 passed. Other non-PIL avatar tests (accepts tiles, tries-next-tile,
  fails-closed, opens-photo-album) → 3 passed.

### 4. Contract chain intact
Cleanup: stale globs across Download/Pictures/DCIM + `purge_media_rows`
(`avatar_`, `av_`) at 5524-5538; delete-stale-then-push 5548-5554;
`touch_remote_file` 5560; purge + `refresh_media_library` 5568-5575 (fails
closed `AVATAR_MEDIASTORE_INDEX_FAILED`); first-image-tile tap 6726-6743;
no-tile → `AVATAR_PICKER_NO_MATCH` 6730-6736.

## Pre-existing unrelated failures (reported separately)
Broken Pillow in the hermes venv:
`ImportError: cannot import name '_imaging' from 'PIL'` — fails every
PIL-importing test regardless of diff: `test_avatar_picker_visual_match_
finds_true_tile_below_first_row`, `test_avatar_recent_fallback_does_not_back_
out_of_picker`, 5× `test_media_push_*`. Proved via the traceback pointing at
`from . import _imaging as core` in PIL/Image.py, not at diff content.
Also `.pytest_cache` write PermissionError (Errno 13) — env noise.

## Non-blocking finding (doc follow-up)
Code comments at state_machine.py:5579 and 6721 cite `COMPAT-AVATAR-007`,
but no such entry exists in `docs/tiktok-ui-compatibility.md` (the ID
predates this diff; only the 6721 comment wording changed). Recommend adding
the doc entry in a follow-up. Not a blocker: no doc contract forbids the
new behavior.

## Reusable review recipe (for the class of task)
See SKILL.md "Doc-contract drift audit" → "Two doc-contract gates":
1. diff stat + named-file diff only, confirm tree otherwise clean
2. verify library-API assumptions against INSTALLED package
   (`inspect.getsource(AdbClient.shell)`), grep repo-wide for leftovers
3. cross-check push-target path vs album-order labels
4. run the changed tests; confirm the rewritten test exercises the NEW
   ordering and the removed test matched the old semantics
5. confirm fail-closed path preserved (no-tile raise, cleanup chain)
6. separate environment failures (broken venv/PIL) from code failures and
   report them separately
