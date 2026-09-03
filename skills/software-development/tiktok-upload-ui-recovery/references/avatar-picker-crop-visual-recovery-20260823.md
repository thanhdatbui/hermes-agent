# Avatar picker/crop visual recovery reference

## Observed sequence
- Workbook source was `Tik1.xlsx`, machine 44, account `v.th.thoooo`, Folder Video `345`.
- The avatar source resolved through the workflow path resolver to `D:\TIKTOK-videonuoinick\345\avatar.jpg`.
- The picker selected one image and displayed `Đã chọn 1` / `Tiếp (1)`.
- The next screenshot showed TikTok `Cắt` with the new image, `Hủy`, and red `Lưu`; vision confirmed it was no longer the picker.
- Tapping scaled crop-save point `(792, 1794)` produced `Sửa hồ sơ` with the new avatar and target identity visible.
- The runner later reported `AVATAR_CROP_OPEN_FAILED` because its semantic/visual path did not observe the already-saved surface. This was a false failure, not a failed avatar update.
- The device was then force-stopped and returned to Android Home; both machine and serial locks were verified absent.

## Geometry classifier
For a 1080x1920 portrait surface:
- Crop save surface: both bottom red regions are present: `(552,1728,760,1860)` and `(824,1728,1032,1860)`.
- Picker Next surface: only the right red region `(824,1728,1032,1860)` is present.
- These are classifiers, not permission to tap without confirming the selected-count state and target image.

## Corrective implementation pattern
- After selecting the avatar, capture visual evidence before waiting for selectors.
- Use a bounded visual fallback for `Tiếp (1)` when semantic ATX nodes are stale.
- Use the two-red-region classifier to recognize crop and avoid reporting `AVATAR_CROP_OPEN_FAILED` on a real crop screen.
- After tapping `Lưu`, verify the edit-profile surface and target handle/avatar; once verified, stop TikTok, return Home, and release locks.
- Keep report status and visual acceptance evidence separate so a stale report cannot overwrite a proven live result.
