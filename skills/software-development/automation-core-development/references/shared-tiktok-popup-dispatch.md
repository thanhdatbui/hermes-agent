# Shared TikTok popup dispatch

## Session-derived contract

The account-update prompt is not an account-switcher-only event. TikTok can redraw it after switching accounts, opening Profile, or between feed/navigation actions. The shared core owns detection and action selection; consumers own when to call a checkpoint.

## Standalone vs Chained popup rule (Facebook contacts/email permission)

- Popups such as `facebook_contacts_email_permission` ("Cho phép TikTok có quyền truy cập vào email và danh sách bạn bè trên Facebook của bạn?") can appear **standalone** on Profile or during feed sessions without any preceding Add Phone popup.
- **Anti-pattern:** Consumer adding token gates requiring an Add Phone predecessor (e.g. `_validate_and_consume_add_phone_chain_token`). When the popup appears standalone, consumer dismissers reject it, leading to `unexpected popup/dialog marker detected` and unnecessary fail-closed lockups.
- **Rule:** Benign permission modals with verified safe dismiss actions (`dismiss_deny_button` -> "Không cho phép") must be authorized for standalone dismissal in consumer adapters matching core capability.

## Canonical call pattern

```python
from automation_core.tiktok.startup import dismiss_tiktok_popups

result = dismiss_tiktok_popups(
    capture_xml=capture_xml,
    tap=tap_element,
    press_back=press_back,
    relaunch=relaunch,
    max_passes=1,
)
```

Call this after each UI recapture that may be blocked by a TikTok modal. `dismiss_known_startup_popups` remains a compatibility alias, not a second implementation.

## Account-update matching

A safe match requires all of:

- title: `Tài khoản của bạn cần được cập nhật`
- security body: `Để tăng cường tính bảo mật, hãy liên kết số điện thoại hoặc địa chỉ email của bạn trước khi chuyển đổi tài khoản`
- clickable semantic action: `Để sau`

The resulting action is `dismiss_later_button`. Do not select the CTA `Liên kết số điện thoại hoặc email`, a generic `Để sau` from another dialog, or a hard-coded coordinate without XML evidence.

## Verification fixture pattern

Use two XML captures:

1. before: the complete prompt and both CTA/later elements;
2. after: a normal TikTok screen with the prompt absent.

Assert `detected`, `dismissed`, and `verified`; assert `popup_types == ("account_update_prompt",)` and `actions == ("dismiss_later_button",)`; record that only `Để sau` was tapped.

Run the same fixture at two conceptual checkpoints (for example `after_account_switcher` and `between_feed_actions`) to prove the API is lifecycle-neutral. Add a negative fixture missing the safe button or security body and assert no tap occurs.

## Provenance gate

Use a dedicated `codex/*` core worktree. On this Windows host, `PYTHONPATH` must use a Windows-style path such as `D:/Taadaa/<worktree>/src`; `/d/...` may be ignored by Windows Python. Probe `automation_core.tiktok.startup.__file__` before the test run and require it to point inside the implementation worktree. This prevents the editable install's MetaPathFinder from silently exercising the coordinator checkout.

## Closeout and delivery

The feature worktree is only the safe implementation surface; it is not the
shipped result. For an explicit `chốt phiên`/cleanup request: independently
review the exact allowlist, commit only that allowlist in the feature worktree,
fetch/rebase against actual upstream, fast-forward the coordinator
`master`/`main`, rerun the focused suite on the coordinator tree, push and
verify `git ls-remote` matches local HEAD, release the merge guard, then remove
only the task-owned worktree and branch. Final status must show coordinator
clean, local/upstream synchronized, guard unlocked, and no task worktree.
