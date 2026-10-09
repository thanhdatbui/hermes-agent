# Account Switcher & Screen Classification Pitfalls

## 1. `automation_core.tiktok.account_switcher.is_switcher_open()` Verification Logic

When inspecting UI XML or writing unit tests for `is_switcher_open()`, note the exact verification condition:

```python
return bool(account_like) and (
    has_add_account
    or (has_title and has_login_option)
    or has_selected_account
)
```

### Pitfall
- Having only a header node like `<node text="Chuyển đổi tài khoản" ... />` is **not sufficient**.
- `is_switcher_open` requires at least one account candidate (`bool(account_like)` evaluated by `_looks_like_account`), e.g. an account username or ID node, in addition to `has_add_account`, `has_selected_account`, or `has_title and has_login_option`.
- For mock XML in unit tests, always provide both the switcher title/action and at least one valid account row (e.g. `@username` or valid ID).

## 2. Notification / SystemUI Allowlisting in Screen Classifiers

- When extracting searchable UI text for screen classification (e.g. `_allowlisted_ui_text` in `login_runner/device_inspector.py`):
- Filter nodes by `package_allowlist` (e.g. `com.zhiliaoapp.musically`, `com.ss.android.ugc.trill`).
- If node attribute `package` is present and not in the allowlist, skip the node's `text` and `content-desc`.
- This prevents notification bars, Google Play Services ("Yêu cầu đăng nhập"), or other system dialogues from incorrectly triggering login screen detection.
