# Restoring features Codex removed from the Hermes source tree

Verified 2026-08-05. Scenario: after a Hermes upgrade, `codex` (or another
agent) edited the source tree in `%LOCALAPPDATA%\hermes\hermes-agent` and
REMOVED a feature (here: the desktop `react_to_message` tool + its storage/RPC
stack, along with `open_preview`/`focus_pane`). The frontend (desktop app)
still references the removed backend, so the feature silently dead-ends.

## The KEY discovery: runtime-sync-package-backups

Hermes runtime-sync (the deploy mechanism) keeps timestamped full-package
backups of the running source tree:

```text
%LOCALAPPDATA%\hermes\hermes-agent\runtime-sync-package-backups\<timestamp>\files\
    ├── hermes_state.py
    ├── tui_gateway\methods_session.py   (pre-refactor RPC file)
    ├── tui_gateway\methods_prompt.py    (model-context helper)
    ├── tools\react_to_message_tool.py   (removed tool)
    └── tools\desktop_ui.py              (removed emitter bridge)
```

These backups are a **pre-deletion snapshot** — the best source for restoring
removed code, often better than git history (they match the exact pre-edit
state including local custom patches). Always check them FIRST before
reconstructing from `git log`.

## Diagnose what was actually removed (4 layers)

A desktop feature like message reactions spans 4 layers; removing any one
silently breaks the feature. Check each:

1. **DB layer** — `hermes_state.py` (SessionDB): methods like
   `set_message_reaction`, `get_message_reactions`, `take_unseen_reactions`,
   `latest_message_row_id`, `get_message_role`, plus `REACTIONS_METADATA_KEY`
   and `_encode/_decode_display_metadata`, `_scrub_surrogates`.
   Grep: `grep -n "set_message_reaction" hermes_state.py`
2. **RPC layer** — `tui_gateway/server.py` `@method("message.react")`.
   Grep: `grep -n '@method("message.react")' tui_gateway/server.py`
3. **Tool backend** — `tools/react_to_message_tool.py` + `tools/desktop_ui.py`
   (emitter bridge) + toolset entry in `toolsets.py` + `_wire_desktop_ui()`
   wiring in server.py.
4. **Model context** — `_pending_reaction_notes()` helper + its call inside
   the `prompt.submit` handler, so the model knows when the user reacted
   (feature-gated by `display.message_reactions`).

The frontend check: `grep -rn "message.reaction\|react_to_message" apps/desktop/src/`
— if the renderer still handles the event but the tool is gone, it's dead code.

## Restore procedure

1. Locate backups: `ls runtime-sync-package-backups/*/files/`
2. Extract the removed file from the newest backup:
   `cp <backup>/files/tools/react_to_message_tool.py tools/`
3. Port to the CURRENT architecture:
   - 0.18.2 used `tui_gateway/methods_session.py` + `methods_prompt.py`
     (separate files); 0.20.0 folds all `@method` handlers into
     `tui_gateway/server.py`. Port the RPC as a new `@method("message.react")`
     block in server.py (verify `_sess_nowait`, `_session_db`, `_ok`, `_err`,
     `_db_unavailable_error` exist there).
   - Re-add `_wire_desktop_ui()` (set_emitter bridge) + call it inside
     `_start_notification_poller` next to `_wire_agent_terminal_output()`.
   - Re-add `_pending_reaction_notes()` and splice its call into the
     `prompt.submit` handler right after `run_message` is built (model input
     only, never persisted — cache-safe).
4. DB layer: verify the CURRENT schema still has the columns the restored
   code needs. 0.20.0 schema is in `hermes_state_common.py` (SCHEMA_VERSION 25);
   `display_metadata TEXT` still exists in `messages`. Restored methods call
   `self._decode_display_metadata` / `_encode_display_metadata` / `_scrub_surrogates`
   — if those helpers were also removed, restore them from backup too.
5. Toolset: add the tool name back to `toolsets.py` (e.g. `"react_to_message"`
   in the `terminal` toolset next to `read_terminal`/`close_terminal`).
6. Register: `registry.register(name=..., toolset="terminal", check_fn=...)` —
   the tool file already calls it on import.

## Verify (no pytest needed for DB layer)

```bash
./venv/Scripts/python.exe -c "
import hermes_state
db = hermes_state.SessionDB()   # in temp HERMES_HOME
db.create_session('s1', source='test'); db.append_message('s1','user','hi')
rid = db.latest_user_message_row_id('s1')
print(db.set_message_reaction('s1', rid, '👍', author='user'))
print(db.take_unseen_reactions('s1', author='user'))
"
```

Tool smoke (desktop env):
```bash
HERMES_DESKTOP=1 HERMES_SESSION_KEY=s1 ./venv/Scripts/python.exe -c "
import tools.desktop_ui as d; d.set_emitter(lambda sid,e,p: print(e,p))
import tools.react_to_message_tool as t; print(t.react_to_message_tool('👍'))
"
```

Server RPC check:
```bash
./venv/Scripts/python.exe -c "import tui_gateway.server as s; print('message.react' in s._methods)"
```

## Pitfalls

- **`no such column: display_metadata` in a FRESH temp DB** — the 0.20.0
  `SessionDB.__init__` no longer auto-creates the full schema for a new DB
  (schema split into `hermes_state_common.py`); the REAL state.db has the
  column via migration. Don't conclude the restore is broken from a temp-DB
  test; verify against the real `%LOCALAPPDATA%\hermes\state.db`
  (`PRAGMA table_info(messages)`).
- **conftest.py errors after upgrade** (e.g. `moa_loop._preset_cache` missing)
  are test-infra drift, not your restore — the 0.20.0 refactor didn't update
  conftest. Run targeted direct python smoke instead of pytest.
- **Codex may re-remove the feature on its next run** — if the user wants it
  durable, package it as a plugin (lives outside core; Codex won't touch it)
  rather than re-patching core every time.
- The feature is opt-in via `display.message_reactions` (Settings → Appearance);
  `check_fn` returns False until enabled — that's correct, not a bug.
