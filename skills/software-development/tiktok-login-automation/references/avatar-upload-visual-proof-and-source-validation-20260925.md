# Avatar upload: visual proof and source validation

## Failure pattern
A TikTok runner can return `exit=0`, `verified=True`, or `AVATAR_SMOKE_SUCCESS` after pushing a file, opening the picker, tapping Next, tapping Save, and returning to Profile. Those signals prove workflow progress only. They do not prove the correct avatar is rendered for the requested account. In the reviewed run, screenshots were later found to show a different account (`@vy.nguyen8730`) and the claimed post-upload avatar was not visibly proven.

## Required proof sequence
1. Before acting, capture the live profile and exact handle. Do not trust workbook row, stale XML, prior screenshots, or runner status.
2. Validate the source: inspect the original frame/metadata and reject anime/cosplay, film stills, dark transition frames, TikTok UI/music-disc icons, and crops without a clearly visible person. OpenCV face detection is only a candidate generator; constrain detections to the central content region and inspect the candidate image.
3. After upload, wait for the bounded CDN settle period, then reopen/refresh the target profile. If the current handle is not the requested handle, stop and mark blocked.
4. Capture one fresh full-profile screenshot showing the handle and avatar. Crop the actual avatar circle from the correct coordinates/layout and compare it with the intended source. A crop/save screen, picker tile, edit-profile screen, or profile of another account is not final proof.
5. Only report success when the fresh screenshot visibly proves both exact account identity and the intended avatar. Otherwise report `FINAL_BLOCKED` with the artifact path and reason.

## Delivery retry
For a failed `MEDIA:` attachment, verify the artifact exists/readable, then retry the same attachment once. Never claim the user saw or approved an image merely because the local file exists. Keep proof claims limited to what the fresh artifact actually shows.
