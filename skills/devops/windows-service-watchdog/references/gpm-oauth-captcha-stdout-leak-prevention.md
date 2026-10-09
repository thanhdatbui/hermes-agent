# GPM OAuth & Captcha Solver Stdout Leak Prevention in no_agent Cron

## Root Cause
When running scheduled multi-worker browser/OAuth automation (such as GPM Antigravity Feeder on OmniRoute) via Hermes cron (`no_agent: true`), importing helper scripts (e.g. `add_oauth_omniroute.py`) causes root logging pollution.
These helper modules configure:
```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),  # <-- ROOT CAUSE
    ],
)
```
When Google detects multi-worker automation and presents reCAPTCHA audio challenges, solver exceptions (`Frame was detached`, `Target closed`, `No bframe found`) get emitted via `logger.info()` / `logger.error()`.
Because `StreamHandler(sys.stdout)` is active, these logs dump directly to `sys.stdout`. Hermes `no_agent: true` cron treats any non-empty stdout as an active user message and delivers it to Telegram, causing spam alerts.

## The Dual-Defense Cleanliness Pattern
To completely silence sub-module logs and preserve the Silent Watchdog pattern:

```python
# 1. Force root logger to sys.stderr at WARNING level
import logging
logging.basicConfig(stream=sys.stderr, level=logging.WARNING, force=True)

# 2. Scrub any existing StreamHandler bound to sys.stdout
for _h in list(logging.root.handlers):
    if getattr(_h, "stream", None) == sys.stdout:
        logging.root.removeHandler(_h)

# 3. Clear handlers on third-party / helper loggers
for _name in ("add_oauth_omniroute", "Batch12Untouched", "playwright", "urllib3"):
    logging.getLogger(_name).handlers.clear()
```

## Report Invariant
1. If `success_count == 0`: write details to `sys.stderr` only. `sys.stdout` MUST be 0 bytes.
2. If `success_count > 0`: print ONE concise summary block to `sys.stdout` for Telegram delivery.
