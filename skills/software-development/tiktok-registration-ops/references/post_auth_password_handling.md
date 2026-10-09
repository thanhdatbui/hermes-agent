# Post-Auth Late Password Handling Pattern

In `social_reg_v1.py`, registration flows can sometimes encounter a late "Tạo mật khẩu" / "Password" screen during `handle_post_auth_screens()`.

### Correct Helper Signature
There is NO `fill_password(device_id, email, ...)` in `social_reg_v1.py`.
The canonical helper is:
```python
fill_password_and_login(device_id, password, stt=None)
```

### Password Resolution Pattern
To resolve the password for the account:
```python
tracking_meta = get_tracking_account_meta(email)
tiktok_pw = (tracking_meta.get("pass") or "").strip()
if not tiktok_pw:
    tiktok_pw = make_tiktok_password()
fill_password_and_login(device_id, tiktok_pw, stt=stt)
```

### Unit Testing & Mocking Caveats
- `social_reg_v1` does NOT have an `is_feed_or_profile_active` helper. Do not mock it.
- `handle_post_auth_screens()` exits the loop by inspecting the UI hierarchy text for home/feed markers like `"ho so"`, `"profile"`, `"danh cho ban"`, etc. Mock `get_ui_xml` return sequence with the screen XML followed by an XML containing `<node text="Hồ sơ" />` to break out cleanly.
