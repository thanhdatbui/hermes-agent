# Hermetic Mocking for Alert & Telegram Dispatch Tests

## Problem & Incident Anatomy

When tests exercise watchdog, alert, or reporting code (e.g., `dispatch_split_reports`, `send_alert`, Telegram API callers), developers often test formatting, filtering, or chunking logic:
```python
# ANTI-PATTERN: Missing transport and token mocks
def test_dispatch_split_reports_filters_bullet_headers(self):
    body = [
        "🏢 【FARM KIBE】",
        "• Tổng máy xử lý: 80 máy",
        "• Follow chéo (0 lượt follow):",
        "  + Success (0)",
    ]
    # BUG: dispatch_split_reports reads live TELEGRAM_BOT_TOKEN from .env
    # and invokes urllib.request.urlopen(), spamming live chat groups!
    ret = dispatch_split_reports("Test Header", ["\n".join(body)], [])
    self.assertNotIn("• Follow chéo", ret)
```

### Consequences
1. Whenever `pytest`, a subagent, or `closeout_gate.py` runs, real HTTP POST requests are sent to live Telegram chat IDs (e.g., `-5127276494` for Tiktok Follow, `-5435853713` for Tiktok Video).
2. Because test fixtures use incomplete metadata (`win_name=""`, `active_row=""`), the resulting messages appear broken (e.g., `📊 [TIKTOK FOLLOW]  hoàn tất (Row )` with empty row and dummy stats), creating user alarm and channel spam.
3. Multiple review/remediation loops multiply the spam (e.g., sending the same dummy report 4+ times in 10 minutes).

---

## Required Hermetic Mocking Pattern

EVERY test calling dispatch or alert routines MUST hermetically patch **both** the token resolution and the network transport:

```python
from unittest.mock import patch, MagicMock

def test_dispatch_split_reports_filters_bullet_headers(self):
    body = [
        "🏢 【FARM KIBE】",
        "• Tổng máy xử lý: 80 máy",
        "• Lướt Feed:\n  + Success (70)",
        "• Follow chéo (0 lượt follow):\n  + Success (0)",
        "• Đăng Video (1 video):\n  + Success (1)",
    ]
    with patch("automation_core.alerts._load_bot_token", return_value="fake_token"), \
         patch("urllib.request.urlopen", return_value=MagicMock(status=200)) as mock_url:
        ret = dispatch_split_reports("Test Header", ["\n".join(body)], [])
    
    self.assertNotIn("• Follow chéo", ret)
    self.assertNotIn("• Đăng Video", ret)
```

### Key Checklist
1. **Never allow ambient credentials into tests:** Always mock `_load_bot_token` or unset `TELEGRAM_BOT_TOKEN` in the test environment.
2. **Always mock network transport:** Patch `urllib.request.urlopen` or `requests.post` / `httpx.post` at the entry point of the module under test.
3. **Capture payloads instead of transmitting:** If asserting on outgoing messages, use a `fake_urlopen` side effect that captures `req.data` into a list for inspection.

---

## Coordinator Delegation Contract Quirks for Test Repairs

When dispatching worker subagents to repair tests under strict farm guards:
- `TASK_KIND: EDIT` is mandatory.
- `FILE: <absolute_path>` is required.
- Delimiters `OLD_STRING: <<< ... >>>` and `NEW_STRING: <<< ... >>>` are required.
- `FOCUSED_TEST:` must strictly match `python -m pytest <file.py>::<test_node> -q` (single `::` separator, `-q` flag required).
- Avoid unquoted spaces in paths for `FOCUSED_TEST` to satisfy guard regular expressions.
