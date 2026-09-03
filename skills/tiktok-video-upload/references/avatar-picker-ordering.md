# Avatar Picker Ordering — COMPAT-AVATAR-011 (2026-08-15)

Session-specific detail behind the COMPAT-AVATAR-011 fix in SKILL.md. Read
`avatar-mediastore-picker.md` first for the six-gate model; this file records
the ordering failure mode that kept machine 4 in an `AVATAR_SAVE_SELECTOR_MISSING`
loop even after MediaStore rows were clean.

## The ordering bug (root cause)

The old `_handle_ensure_avatar_impl` sequence was:

1. Open the avatar bottom sheet ("Tải ảnh lên" / "Thư viện") — this OPENS the
   Android photo picker.
2. THEN delete stale avatar files, purge rows, push the fresh unique file,
   touch, rescan MediaStore.

The Android photo picker renders its grid from a snapshot taken when the
picker OPENS. Files pushed/scanned AFTER that moment do not appear in the
already-open grid; the grid keeps showing whatever existed at open time — in
machine 4's case, the previous run's tile (an orphaned MediaStore row whose
backing file had been deleted by step 2).

Result, repeated across runs:
- `Tap tile ảnh đầu tiên (mới nhất sau push): (6, 222, 269, 488)` logged.
- Tap landed on the stale/orphan tile → selection circle stayed HOLLOW,
  button stayed plain `Tiếp` (no "(1)").
- `AVATAR_SELECTION_FAILED`-adjacent UI evidence, then
  `AVATAR_SAVE_SELECTOR_MISSING` (the crop/save screen never appeared because
  nothing was selected).
- Launcher reported `exit=1, verified=False` → MANUAL_REVIEW.

A manual user tap on the SAME picker AFTER the push/index worked — because the
picker was reopened on the fresh row. That asymmetry (script fails, human
succeeds with the same image) is the fingerprint of a stale-open-picker grid.

## The fix (implemented + verified)

Reorder `_handle_ensure_avatar_impl` to match the video-flow pattern (media
ready BEFORE picker opens):

1. Delete stale avatar files everywhere (`avatar_*`, `av_*`).
2. Purge MediaStore rows (`purge_media_rows("avatar_")`, `purge_media_rows("av_")`).
3. Delete the target path, push the unique timestamped file.
4. `touch_remote_file` + `purge_media_rows("avatar_")` again + `refresh_media_library`.
5. Re-dump the UI (`change_xml = adapter.dump_ui()`) and tap "Tải ảnh lên" /
   "Thư viện" — the picker now opens with the fresh row already indexed.
6. `_select_avatar_from_download` → `_save_avatar_without_story` unchanged.

Verification:
- Focused avatar tests: 48 passed, 308 deselected (7.18s).
- `py_compile` + `git diff --check` clean.
- Live run machine 4: `AVATAR_SMOKE_SUCCESS`, `avatar_status:
  FORCED_REPLACED_VERIFIED`, log `[ENSURE_AVATAR] Avatar upload thành công`.
- Launcher STILL printed `worker exit=0 nhưng thiếu report/verifier proof;
  chuyển MANUAL_REVIEW` — the known avatar-only mislabel; report.json is the
  ground truth, not the launcher verdict.
- Profile screenshot (TikTok → Hồ sơ tab) showed the new portrait: woman,
  dark hair, white top, hand near face, green foliage — matches the folder-26
  `avatar.jpg`. Confirmed by live phone, not by ledger.

## Manual profile-verify launch gotcha (same session)

- `adb shell am start -n com.ss.android.ugc.trill/.main.MainActivity` →
  `Error type 3: Activity class ... does not exist`.
- `.splash.SplashActivity` → same error.
- Working launch: `adb shell monkey -p com.ss.android.ugc.trill 1` → feed on
  "Đề xuất". Then read "Hồ sơ" bounds from `uiautomator dump` (text node
  `[864,1864][1080,1903]`, clickable content-desc node `[864,1794][1080,1920]`;
  tap ~(972,1857)) → screenshot.
- Trap: tapping (990,1880) while TikTok is NOT foregrounded just sits on the
  Samsung home screen; always confirm TikTok is actually open via dump before
  judging the avatar.
