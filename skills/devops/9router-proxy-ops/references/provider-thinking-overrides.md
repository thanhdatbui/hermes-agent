# 9Router Provider Thinking Overrides & Request Inspection

## Mechanism

9Router supports provider-level thinking / reasoning overrides configured via:
1. **Web UI:** `Providers` -> `[Provider Name]` -> `Thinking` dropdown (options: `Auto`, `None`, `Low`, `Medium`, `High`, `Max`, etc.).
2. **Database:** SQLite table `settings` (row `id = 1`), JSON field `providerThinking`:
   ```json
   {
     "codex": { "mode": "max" },
     "antigravity": { "mode": "high" },
     "commandcode": { "mode": "high" },
     "gemini-cli": { "mode": "minimal" }
   }
   ```

## Priority & Override Behavior

In 9Router request pipeline (`8895.js` / `52136.js`):
- When `providerThinking[provider].mode` is set to anything other than `"auto"`, 9Router injects/overwrites the incoming request's reasoning parameters (`reasoning_effort`, `thinking`, `output_config`).
- Even if Hermes or client sends `reasoning_effort: "high"`, if 9Router's provider setting for Codex is set to `max`, the outgoing upstream request and the live console log will reflect `THINK:max`.

## Diagnostic & Remediation

To inspect current settings:
```python
import sqlite3, json, os
db = os.path.expanduser('~/AppData/Roaming/9router/db/data.sqlite')
con = sqlite3.connect(db)
for r in con.execute("SELECT data FROM settings WHERE id=1"):
    d = json.loads(r[0])
    print("providerThinking:", d.get("providerThinking"))
```

To reset or adjust:
- In Web Dashboard: Go to `Providers` -> select provider -> set `Thinking` dropdown to `Auto` (to respect client payload) or desired fixed level.
- Or update `providerThinking` in SQLite directly.
