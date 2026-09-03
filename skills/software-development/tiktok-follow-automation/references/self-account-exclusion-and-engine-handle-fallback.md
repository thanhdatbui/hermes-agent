# Case UI-32 & Case UI-40: Self-Account Exclusion in Follower List and Engine Handle Fallback

## Context & Problem
When traversing an anchor's follower/following list in Mode 2 (e.g. Case UI-32 on Machine 8 `tolmavhj12k`, Case UI-40 on Machine 6 `bch.ngc.ngc91`), the account currently logged in on the device (`active_account`) may appear in the list if the anchor follows or is followed by this account.
TikTok does not show any relationship action button for the logged-in user (`r["follow_button"] is None`, showing a chevron `>` or non-interactive row).
Without proper self-account exclusion, the runner misidentifies the row as a broken/occluded button and triggers `MANUAL_REVIEW: follower row không có nút follow semantic`.

## Root Cause & Property Divergence
Different parts of the follow runner and test fixtures historically accessed the active account via different property names:
- `engine.account_id`
- `engine.active_account`
- `engine.active_account_handle`
- `cfg.account_id`

If `mode2_follow_followers.py` omitted `engine.active_account_handle` in its fallback resolution chain, any `FollowEngine` instance that only set `active_account_handle` would fail to identify the self-account row, causing false `MANUAL_REVIEW` alerts.

## Canonical Fix Contract
1. **Fallback Resolution Chain in Mode 2**:
   In `follow_runner/flows/mode2_follow_followers.py`, resolve `active_account` with full fallback:
   ```python
   active_account = _normalize_handle(
       getattr(engine, "account_id", "")
       or getattr(engine, "active_account", "")
       or getattr(engine, "active_account_handle", "")
       or getattr(cfg, "account_id", "")
       or ""
   )
   ```
2. **Complete Alias Synchronization in FollowEngine**:
   In `follow_runner/flows/follow_engine.py`, initialize all three attributes:
   ```python
   self.active_account_handle = ""
   self.active_account = ""
   self.account_id = ""
   ```
   And whenever `self.active_account_handle = row.tik_id` is assigned (both in `skip_identity_verify` and after `switch_account_and_verify`), synchronously update `self.active_account` and `self.account_id`:
   ```python
   self.active_account_handle = row.tik_id
   self.active_account = row.tik_id
   self.account_id = row.tik_id
   ```
3. **Filtering Missing Button & Pending Rows**:
   Exclude rows matching `active_account` from both `missing_button_rows` and `pending` rows:
   ```python
   missing_button_rows = [
       r for r in rows
       if r["follow_button"] is None
       and _normalize_handle(r.get("handle", "")) != active_account
       and not state.is_followed(r.get("handle", ""))
       and not state.is_skipped(r.get("handle", ""))
   ]
   ```
