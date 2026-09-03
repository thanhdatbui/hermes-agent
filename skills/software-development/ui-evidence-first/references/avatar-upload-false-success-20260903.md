# Avatar upload false-success (TikTok farm, 2026-09-03)

## What happened
Runner `run_tiktok_upload_avatar.ps1` reported `THÀNH CÔNG (exit=0, verified=True)`
plus log line `[ENSURE_AVATAR] Avatar upload thành công`, but the live TikTok
profile still showed the default placeholder avatar. The user caught it from a
real screenshot; the coordinator's post-run screenshot was unread/blank.

## Root cause
`_save_avatar_without_story` tapped Save `(792, 1794)`, slept a fixed 4s, then
`_handle_ensure_avatar_impl` called `adapter.back()` + `am force-stop` immediately.
TikTok needs 5–10s after Save to compress and upload the image to its CDN; the
early Back/force-stop cancelled the in-flight upload. Fix committed in
`Tiktok-video` (`_wait_for_avatar_upload_complete`, remove early `back()`,
`avatar-uploaded-confirmed.png` artifact).

## Durable rule
- Log/exit-code success = save tap happened, NOT server-side avatar persisted.
- Claim avatar success only after: fresh live re-open of profile + fresh
  screenshot + non-placeholder avatar (photo variance, not silhouette/camera).
- Blank/white/Home/unread post-run screenshot = `UNPROVEN`, never success.
- Missing-vision image attachments: say so explicitly, ask for re-upload;
  never overrule the user's visible evidence.
