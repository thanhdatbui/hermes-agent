# Public profile misclassified as login/account

## Incident shape

A `multi-machine-feed-session` alert reported `login/account screen detected`, but the preserved TikTok screenshot showed a public visited profile opened from suggestions:

- visible display name and `@username`;
- follower/following/likes statistics;
- `Follow` and `Nhắn tin` actions;
- suggestion labels such as `Tài khoản được đề xuất`, `Người mà bạn có thể biết`, and `Bạn bè với...`;
- no credential input and no real login surface.

The screenshot alone is useful for triage, but the code fix must be validated with the exact UI XML shape and the classifier/safety path.

## Root cause

The classifier recognized `profile` early only from a selected Profile tab or `com.ss.android.ugc.trill:id/view_profile`. A public profile opened from a suggestion card may expose neither. It then fell through to broad sensitive-marker/login handling because account-related text was present.

## Safe fix pattern

Add a conservative public-profile predicate **AFTER** authoritative login checks (`has_sensitive_marker()`, `detect_save_login_popup()`, `_is_account_switcher_sheet()`, `login_terms`):

1. **Display name + @handle:** a non-empty display name node directly above `@username` ($0 < \Delta Y \le 120\text{px}$) with horizontal bounds overlap in the same package.
2. **Numeric stats row:** at least two distinct stat categories (follower, following/`Đã follow`, likes/`Thích`) having numeric digits and aligned continuously on the same horizontal row ($\Delta Y \le 140\text{px}$, gap $\le 120\text{px}$).
3. **Dual clickable actions:** $\ge 2$ distinct profile action controls (`Follow`, `Đã follow`/`Đang follow`, `Nhắn tin`/`Message`) with `clickable="true"` directly under the stats row ($stat\_bottom \le Y \le stat\_bottom + 180\text{px}$). Suggestion cards typically have only one `Follow` button and fail this check.
4. **No global text-search rejection:** do not reject profiles merely because bio/caption text contains "password" or "sign in"; login precedence handles real login surfaces beforehand.

Return non-manual `profile`. Do not add a global bypass for the words `account`, `follow`, `message`, or `suggested`.

## TDD/replay recipe

1. Preserve the pre-task dirty baseline; do not overwrite unrelated edits.
2. Add a minimal XML fixture matching the public profile and run it before the production change. It must fail for the expected reason (`unknown` or `manual-needed:login`).
3. Implement the smallest classifier change at the precedence boundary.
4. Run the public-profile regression plus real-login and feed-login regressions.
5. Run the focused profile/login feed-session slice, compile the changed files, and run `git diff --check`.
6. Treat unrelated failures in a dirty worktree separately; do not widen this fix to feed-tab or other classifier behavior without evidence.

## Verification evidence

The successful replay should show:

```text
classifier=ScreenClassification(screen='profile', confidence=0.88, ..., manual_needed=False)
safety=ok known TikTok screen
```

The exact confidence/reason text may differ if the implementation evolves; the invariant is `profile`, `manual_needed=False`, and safety `ok` for the bounded public-profile shape, while real login remains blocked.
