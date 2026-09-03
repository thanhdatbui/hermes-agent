# TikTok Shop “Chi tiết giá” bottom-sheet: detection and safe dismissal

## Trigger

Use this pattern when a feed session reports an unknown TikTok state after a swipe and the supplied UI evidence shows a TikTok Shop price-details sheet (“Chi tiết giá” / “Price details”) covering the video.

This is a benign commercial overlay. It must never be treated as permission to purchase, open the product, or tap a generic coordinate.

## Detection contract: fail closed

A match is valid only when all of the following are true:

1. A real XML `node` has exact text or content-desc `Chi tiết giá` or `Price details`.
2. The title node has exact `package="com.ss.android.ugc.trill"`.
3. The title belongs to one non-root ancestor XML `node` that is also package-owned by `com.ss.android.ugc.trill`.
4. The ancestor is a bounded sheet, not a full-screen root. Do not use fixed screen-size cutoffs; derive captured bounds when checking full-screen coverage.
5. Price-detail content (for example `Tổng phụ`, `Voucher`, `Giảm giá`, `Thuế`, `Shipping`, `Total`) is inside the same ancestor subtree and below the title.
6. The close target is inside that same subtree, has a valid center, and has `clickable="true"`. Accept only exact close labels (`Đóng`, `Close`, `X`, `×`) or a close/dismiss resource ID on the clickable node.

Do not combine evidence globally across the XML tree. A title in one subtree plus a `Close` control, price text, or TikTok resource ID elsewhere is not sufficient. Do not accept a package-less node merely because its resource ID begins with the TikTok package prefix. Package comparison is exact and case-sensitive.

## Dismissal contract

1. Capture and parse the current hierarchy before acting.
2. Re-run the strict detector and tap only the returned clickable close element center.
3. Do not fall back to a generic `X`, arbitrary small button, blind coordinate, or `BACK` when the close target is unverified. The popup handler is allowed to fail closed.
4. Recapture after the tap.
5. Invalid/empty/non-XML post-capture is `*_recapture_unverified`, not success.
6. If the sheet is still present, return a blocked/failed result even if its close button metadata changed or disappeared. For this check, use a presence detector with `require_close=False`, while retaining all ownership, package, bounds, title, and price-content checks.
7. Only report dismissal success when the post-capture is valid and the price-details sheet is absent.

## Regression matrix

At minimum test:

- Positive: exact TikTok package-owned sheet, price content, clickable close → handler matches and taps the close center.
- No context: same visible text without TikTok package → no match.
- Wrong ancestor: title/content/close nodes under a non-TikTok ancestor → no match.
- Wrong case: package differs only by case → no match.
- Full-screen root: package-owned full-screen root at more than one resolution (including 720×1600) → no match.
- Non-clickable close label → no match and no tap.
- Invalid post-capture → dismissal fails closed with `recapture_unverified`.
- Still-present post-capture with unchanged close → fails closed.
- Still-present post-capture with changed/removed close metadata → fails closed via presence mode.
- Existing dispatcher routes remain unchanged; do not include unrelated logout/edit-name changes in the candidate.

## Exact-candidate closeout

In a dirty shared worktree:

1. Compare the requested popup hunk against current dirty hunks. Same-file dirt is not automatically a conflict; block only on actual overlap or active ownership of the popup hunk.
2. Build the review candidate from `HEAD` plus only the popup production/test hunks. Do not stage the whole dirty files.
3. Review the exact candidate bytes, then materialize the exact staged tree and run the focused tests there. A working-tree pass is not enough.
4. Keep the staged index isolated if unrelated files are already staged.
5. Rebuild and re-review after every candidate edit. A previous approval is stale after any byte change.
6. For a target incident, require a fresh canary with `final_status: success`, the exact target, and valid artifacts before commit.
7. Commit only the explicit popup production/test paths, pull-rebase, push, and verify remote SHA equals local HEAD.

## Evidence and reporting

Use concise evidence: target, exact failure signature, detector/handler result, test counts, canary artifact, review verdict, commit paths, and remote SHA. Separate unrelated dirty paths from the candidate. Never claim success from a wrapper exit code alone.
