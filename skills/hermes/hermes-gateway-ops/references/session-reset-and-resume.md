# Session reset and resume recovery

## Known failure pattern

A Telegram bot can display a reset banner such as:

- `Session automatically reset`
- `daily schedule at 4:00`
- `Conversation history cleared`

The effective cause is commonly:

```yaml
session_reset:
  mode: both
  idle_minutes: 1440
  at_hour: 4
```

`both` enables both 24-hour idle expiry and the daily wall-clock reset. The `at_hour` value is interpreted in the gateway's local/server timezone unless the deployment explicitly configures another timezone.

## Safe diagnostic sequence

1. `hermes config show` — confirm the active config path and model/gateway context.
2. `hermes config check` — validate the config.
3. Read `config.yaml` only around `session_reset`; do not dump secrets.
4. Inspect `gateway.log` for:
   - `Session expiry: N sessions to finalize`
   - `Session expiry done: N finalized`
   - `end_reason=session_reset` in the session DB
   - `Agent idle for ...` or `iteration X/Y` if a run is stale.
5. Query `$HERMES_HOME/state.db`:

```sql
SELECT id, chat_id, thread_id, title, started_at, ended_at,
       end_reason, message_count, expiry_finalized
FROM sessions
WHERE source = 'telegram'
ORDER BY started_at DESC;
```

Also inspect `gateway_routing` for the current routing key. The exact Telegram key includes platform, chat type, chat ID, and sometimes thread ID; do not confuse a topic session with the base group session.

## Corrective change

For a user who does not want automatic expiry:

```bash
hermes config set session_reset.mode none
hermes config check
grep -n -A4 '^session_reset:' "$HERMES_HOME/config.yaml"
```

Do not use `hermes config get` (not present in this CLI), and do not hand-edit the YAML for the user. `idle_minutes` and `at_hour` may remain as dormant values while `mode: none` is active.

## Resume checklist

- Locate the intended historical session ID from `hermes sessions list` or SQLite.
- Prefer the target chat's actual `/resume <session_id>` command path over sending the text through a generic outbound `hermes send`; the latter only sends a Telegram message and may not dispatch it as a user slash command.
- Confirm the inbound `/resume` event in `gateway.log` and verify the target session/routing row.
- If the target session is stale/hung, preserve its transcript and stop/recover the specific run before injecting more prompts.
- If a restart is required, execute it from outside the gateway process. The gateway deliberately blocks self-restart commands. Never restart during a live farm batch.

## Evidence from the incident that motivated this reference

- The configured block had `mode: both`, `idle_minutes: 1440`, and `at_hour: 4`.
- Gateway logs showed daily expiry around 04:00 and finalized sessions with `end_reason=session_reset`.
- A Telegram Tiktok Reg session had a prior session ID and a newer routing entry; the old transcript remained queryable in `state.db`.
- A stale run logged an idle duration measured in hours and `iteration 4/60`; this is a hang/stale-run symptom, not proof that the model simply needed another prompt.
- The setting was changed using `hermes config set session_reset.mode none`, followed by `hermes config check` and a direct YAML readback.

This reference is session-specific evidence; the reusable workflow is in the parent `SKILL.md`.