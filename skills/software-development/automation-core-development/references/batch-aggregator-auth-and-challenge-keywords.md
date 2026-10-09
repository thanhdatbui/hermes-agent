# Batch Aggregator: Auth & Challenge Failure Classification

## Background & Invariants
`automation_core.batch_aggregator` monitors batch execution results and clusters errors into systemic failure reports or immediate P0 alerts.

### 1. Separation of Session Lost vs Challenge
Errors related to authentication are bifurcated into two categories:
- **Session Lost / Văng Account (`SESSION_LOST_KEYWORDS`)**:
  - Triggers `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]`.
  - Must catch both exact phrases and root terms: `"logged out"`, `"signed out"`, `"văng"`, `"session expired"`, `"phiên đã hết hạn"`, `"login screen"`, `"đăng nhập lại"`, `"require_login"`, `"login"`, `"account screen"`, `"auth"`.
  - **Pitfall**: Omitting `"login"` or `"account screen"` causes compound or hyphenated error signatures (e.g. `error_type="login-issue"`, `error_message="login/account screen detected"`) to miss the session lost category, breaking immediate P0 alert triggering in `test_p0_auth_alert_triggers_immediately`.
- **Temporary Challenge / Captcha (`CHALLENGE_KEYWORDS`)**:
  - Triggers `⚠️ [CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]`.
  - Keywords: `"verification"`, `"manual_challenge"`, `"checkpoint"`, `"captcha"`, `"verify"`.
  - Must filter out any machine already categorized under `session_lost_failures` to avoid duplicate reporting.

### 2. Immediate Alert Bypass
Dual-threshold criteria (`min_rate`, `min_count`) only govern systemic signature clustering. Any failure matching `SESSION_LOST_KEYWORDS` or `CHALLENGE_KEYWORDS` must set `should_alert = True` immediately, even on a single machine failure:
```python
should_alert = len(systemic) > 0 or len(session_lost_failures) > 0 or len(challenge_failures) > 0
```

### 3. Verification & Deployment Cycle
1. Run unit test suite with explicit repo `src` on `PYTHONPATH`:
   ```bash
   PYTHONPATH="D:/Taadaa/automation-core/src" python -m pytest D:/Taadaa/automation-core/tests/test_batch_aggregator.py
   ```
2. Propagate to active virtualenv site-packages:
   ```bash
   cp -rf D:/Taadaa/automation-core/src/automation_core/batch_aggregator.py /d/Taadaa/python-envs/automation/Lib/site-packages/automation_core/batch_aggregator.py
   ```
