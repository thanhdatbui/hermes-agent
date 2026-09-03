# Dynamic TikTok popup selector regression

## Contract

For an in-feed Shop CTA, the detector is valid only when the current XML contains:

- exact text `Mua ngay`,
- exact text `Đóng`,
- both actions in TikTok context (`package="com.ss.android.ugc.trill"` or a resource ID beginning with `com.ss.android.ugc.trill:`),
- a usable/clickable button node when the existing typed detector requires it.

The detector must not act on a close button by itself, and it must not act on a matching pair owned by another package.

The action is the exact `Đóng` element returned from the current parsed XML. Do not encode a resource ID such as `hvm`, `hyw`, or `hwn` in production action XPath. IDs are variant data, not policy.

## Implementation pattern

1. Inspect the existing shared/consumer typed detector before changing a blind rule.
2. Keep the blind rule's semantic buy marker as evidence, but add a narrow rule-specific resolver for the Shop CTA.
3. Parse the current XML once for the resolver; reject if the typed detector returns no match.
4. Resolve the close action from `match.close_element` (or equivalent current-XML node), and pass that element directly to the existing safe tap helper.
5. Preserve selector evidence: popup type, text/content-desc, resource ID, bounds, center, and the rule name. The observed ID may be recorded in evidence, but never used as a constant matcher.
6. For a fullscreen Shop surface with no usable close action, leave the typed close branch unmatched and use the existing bounded swipe handler. That handler must recapture and verify TikTok focus + feed + overlay absence + no sensitive marker.

## Regression matrix

Use small XML fixtures with clickable `android.widget.Button` nodes and bounds. At minimum cover:

- legacy/known variant: `Mua ngay` and `Đóng` with their current TikTok IDs;
- observed variant A: buy ID `com.ss.android.ugc.trill:id/hyq`, close ID `com.ss.android.ugc.trill:id/hyw`;
- observed variant B: buy ID `com.ss.android.ugc.trill:id/hwh`, close ID `com.ss.android.ugc.trill:id/hwn`;
- negative: close without `Mua ngay` (no shell action);
- negative: both labels under a non-TikTok package (no shell action);
- fullscreen overlay: `Mua ngay` plus fullscreen container and no usable close action, routed to exactly one `input swipe 540 1600 540 400 300`, followed by evidence-gated recapture; never tap the buy button.

For blind checkpoint tests, assert the exact ADB command uses the close node's bounds/center for each variant and assert no command contains a buy action. Keep the tests offline with mocked capture/ADB/logger; never use ADB, a real device, GemPhoneFarm, account data, workbook data, or live artifacts.

## Verification

Run the focused popup tests with the repository-pinned interpreter, then compile the touched Python files and run `git diff --check`. Inspect the final diff and confirm only the assigned source/test files changed; do not stage, commit, or push unless explicitly requested.
