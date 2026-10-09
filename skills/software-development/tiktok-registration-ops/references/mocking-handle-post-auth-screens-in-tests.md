# Mocking `handle_post_auth_screens` in Unit Tests

When writing unit tests for `handle_post_auth_screens` in `social_reg_v1.py` (e.g. testing late password screens, onboarding dismiss, or nickname handling):

### Pitfall: `maybe_save_login_info_prompt` consumes `get_ui_xml`
Inside `handle_post_auth_screens`, each loop iteration begins:
```python
xml = get_ui_xml(device_id)
...
if maybe_save_login_info_prompt(device_id):
    continue
```
`maybe_save_login_info_prompt(device_id)` internally calls `get_ui_xml(device_id)` again.

### Symptom
If a unit test sets a finite `side_effect` sequence on `get_ui_xml` expecting 1 call per loop iteration (e.g. `[pw_xml, main_xml]`):
```python
with patch.object(social, "get_ui_xml", side_effect=[pw_xml, main_xml]):
    ...
```
Mock `get_ui_xml` is called TWICE in round 1, exhausting the iterator and raising `StopIteration` when round 2 tries to fetch the UI XML.

### Correct Pattern
Always mock `maybe_save_login_info_prompt` to return `False` when testing specific post-auth branches:
```python
with patch.object(social, "maybe_save_login_info_prompt", return_value=False), \
     patch.object(social, "get_ui_xml", side_effect=[pw_xml, main_xml]), \
     patch.object(social, "get_tracking_account_meta", return_value={"pass": "..."}) as mock_meta, \
     patch.object(social, "fill_password_and_login") as mock_fill, \
     patch.object(social.time, "sleep"):
    social.handle_post_auth_screens("fake_dev", "test@test.com", stt=74)
```
This keeps each loop iteration strictly 1-to-1 with `get_ui_xml` mock outputs.
