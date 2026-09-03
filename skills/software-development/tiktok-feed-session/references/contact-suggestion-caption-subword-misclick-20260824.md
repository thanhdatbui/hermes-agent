# Contact Follow Suggestion Caption Subword Misclick & Feed Ad Swipe Invariant

## Incident Context (2026-08-24, Machine 25 `thao.phan206`)
- **Alert**: `manual review required after contact_follow_suggestion dismiss: unknown`
- **Observed UI**: On normal For You feed (`Đề xuất`), automation tapped on video description `Chúng ta có thể đóng gói Lamine Yamal không??` (`id/desc`), opening TikTok search `devincaherlyc` with soft keyboard.

## Root Cause Breakdown
1. **False-Positive Classifier Match**:
   - `detect_contact_follow_suggestion` in `automation-core` matched the generic keyword `"đề xuất"`, which was triggered by the normal top tab `Đề xuất` (For You feed).
   - Follow marker matched the creator follow button `Follow Devin Caherly`.
2. **Subword & Description Node Misclick**:
   - `_element_contains` checked `"đóng"` via standard boundary matching that permitted subword matches in Vietnamese compound phrases like `"đóng gói"`.
   - The dismissal button search lacked exclusion of video caption/description containers (`:id/desc`), causing the text description to be classified as a clickable close button.
3. **Operator Rule on Feed Ad CTAs**:
   - User policy: For in-feed ad CTAs (Shop CTA, sponsored ad feedback, brand promos), always prefer swiping past the ad over tapping close buttons. Never tap blindly or attempt to click close controls when a swipe naturally moves to the next feed video.

## Prevention Contract
1. **Eliminate Generic Top-Tab Keywords**:
   - Never use standalone `"đề xuất"`, `"gợi ý"`, or `"contact"` alone in suggestion card detectors.
   - Require explicit suggestion card contexts: `"tài khoản được đề xuất"`, `"người mà bạn có thể biết"`, `"liên hệ từ danh bạ"`, `"gợi ý follow"`, `"trong danh bạ"`.
2. **Strict Word Boundaries for Vietnamese**:
   - Enforce punctuation/whitespace boundaries `(?:\b|(?<=[\s,;.!?]))<term>(?:\b|(?=[\s,;.!?]))` for single-word dismissal terms like `"đóng"`, `"close"`, `"save"` so compound words (e.g., `"đóng gói"`, `"đóng cửa"`) do not match.
3. **Exclude Caption & Description Containers**:
   - Dismiss target selectors must filter out `:id/desc`, `:id/title`, and other video metadata containers from close button candidates.
4. **Feed Ad Overlays -> Swipe Over Tap**:
   - Feed ad cards must prioritize bounded swipe-through (`_dismiss_feed_ad_overlay_by_swipe` / `shop_cta_swipe`) rather than searching for close buttons.
