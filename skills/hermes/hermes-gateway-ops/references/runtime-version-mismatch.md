# Runtime core/plugin mismatch checklist

Use this as a compact incident recipe; do not copy credentials or full config into evidence.

## Symptom

Gateway may remain alive while Telegram is unavailable after Desktop/restart. Typical evidence:

- `No adapter available for telegram`
- adapter import fails because it imports a symbol absent from `gateway.authz_mixin`
- core metadata and plugin files come from different releases

A previously running adapter can mask the mismatch because its module is already in memory; the failure appears on the next cold import.

## Safe Windows sequence

1. Check the live Gateway command line and active runtime root. Distinguish it from the source checkout.
2. Enumerate farm processes before restart. A live feed/upload/reg/render batch is a hard restart blocker; do not pause cron or kill farm processes for this repair.
3. Read the installed Hermes version from runtime metadata. Compare:
   - active runtime: `plugins/platforms/telegram/adapter.py`
   - venv artifact: `venv/Lib/site-packages/plugins/platforms/telegram/adapter.py`
   - matching core: `gateway/authz_mixin.py`
4. If the venv adapter is the compatible artifact, copy it to the active runtime path. Remove only Telegram/Gateway-related `__pycache__` directories.
5. Verify byte equality/hash and cold-import with the venv Python. Do not treat an import through an unrelated outer Python as proof.
6. Verify `hermes gateway status` and the newest startup block. Required lines are Telegram polling connection, `✓ telegram connected`, `Gateway running with 1 platform(s)` (or the actual count), and `set_my_commands OK`. Required negative checks are no adapter-unavailable, missing-symbol, or plugin-load errors.
7. If restart is necessary, invoke it from an external shell/service context after the farm is idle; an in-Gateway restart can be refused to avoid killing its own parent.

## Incident lessons

- Resetting the machine does not reconcile a mismatched core/plugin pair.
- Do not blame an unrelated application commit without source evidence.
- Runtime repair and source-repository hardening are separate tasks; report which one was actually performed.
- Keep the final report short: purpose, runtime paths changed, evidence, and blocker.
