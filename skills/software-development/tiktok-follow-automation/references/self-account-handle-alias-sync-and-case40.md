# Case UI-40: Self-Account Exclusion Fallback Chain & FollowEngine Alias Synchronization

## Root Cause & Symptom

When executing Mode 2 (anchor follower/following traversal), the device's currently active logged-in account (e.g. `bch.ngc.ngc91` on Machine 6) may appear in the anchor's relation list.

On TikTok 46.x+:
- The logged-in self-account never displays a relationship action button (`Follow`, `Đã follow`, `Follow lại`). It displays only username/nickname and a chevron `>` arrow.
- Accessibility XML dump renders `r["follow_button"] = None` for this row.

In `mode2_follow_followers.py`:
- The self-account exclusion logic filters out `r` where `_normalize_handle(r.get("handle", "")) == active_account`.
- If `active_account` resolves to `""`, the row is treated as an external target missing a semantic follow button, triggering:
  `MANUAL_REVIEW: follower row không có nút follow semantic`

## The Alias Drift Anti-Pattern

`FollowEngine` in `follow_engine.py` historically initialized and assigned:
```python
self.active_account_handle = row.tik_id
```

While `mode2_follow_followers.py` looked up:
```python
active_account = _normalize_handle(
    getattr(engine, "account_id", "")
    or getattr(engine, "active_account", "")
    or getattr(cfg, "account_id", "")
    or ""
)
```
Because `active_account_handle` was omitted from the lookup chain, `active_account` became `""`.

## Dual-Sided Resolution Pattern

1. **Consumer Fallback Chain (`mode2_follow_followers.py`)**:
   Include all known historical attribute variations in the fallback chain:
   ```python
   active_account = _normalize_handle(
       getattr(engine, "account_id", "")
       or getattr(engine, "active_account", "")
       or getattr(engine, "active_account_handle", "")
       or getattr(cfg, "account_id", "")
       or ""
   )
   ```

2. **Producer Engine Alias Synchronization (`follow_engine.py`)**:
   Initialize and synchronize all aliases simultaneously across both standard and skip-identity paths:
   ```python
   # In __init__:
   self.active_account_handle = ""
   self.active_account = ""
   self.account_id = ""

   # Upon account assignment:
   self.active_account_handle = row.tik_id
   self.active_account = row.tik_id
   self.account_id = row.tik_id
   ```

3. **Regression Fixtures**:
   - Verify self-account exclusion when only `active_account_handle` is set on engine.
   - Verify self-account exclusion when mixed with legitimate target accounts in the same viewport.
   - Verify `FollowEngine` alias synchronization across initialization and session execution.
