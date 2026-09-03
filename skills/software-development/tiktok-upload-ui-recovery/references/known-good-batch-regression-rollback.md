# Known-good batch compatibility and rollback

## Trigger
A recently patched upload/UI path turns a batch that previously had broad `THÀNH CÔNG` results into `VIDEO_PICK` or `CAPTION_FILL` failures, even though screenshots show the expected TikTok composer.

## Evidence-backed rule
1. Stop live workers using the regressed code.
2. Compare the last known-good batch summary and its commit with the regressed commit range before making another UI patch.
3. Do not keep stacking visual gates, coordinate fallbacks, selector restrictions, or retries merely to rescue an unproven patch.
4. When the user explicitly says to return to an earlier Git version, do it immediately: create a backup branch, reset/revert, verify `git diff <target>` is empty, push the intended main, then stop until directed to rerun.

## Incident: 2026-08-10
- Known-good `f4e4520`, batch `batch_tik1_list_43_20260810_065538`: **32 successful machines**. Machine 15 explicitly logged `Filling caption via clipboard → POST → profile tile increment → workbook update`.
- A subsequent experimental range imposed exact caption-field identity and additional XML re-verification. When uiautomator XML was empty/partial, screenshots still showed the final `Thêm mô tả` + `Nháp/Đăng` composer, but the strict selector raised `Caption field not found via selectors`, blocking POST.

## Interpretation
A screenshot-confirmed composer plus a missing XML selector is a verifier compatibility regression candidate, not proof that TikTok or media upload failed. Keep the known-good path unless a replacement passes a staged farm proof and demonstrates no regression.
