# Multi-session & per-channel binding — source dive (Hermes 0.18.2, 2026-08-08)

Where the behavior lives in the install tree (`$HERMES_HOME/hermes-agent`, i.e.
`C:\Users\Kibe\AppData\Local\hermes\hermes-agent`):

## Session keying

- `gateway/session_context.py` — `set_session_vars(...)` sets ContextVars for
  `_SESSION_PLATFORM`, `_SESSION_CHAT_ID`, `_SESSION_THREAD_ID`, `_SESSION_USER_ID`,
  `_SESSION_KEY`, etc., plus `set_session_cwd(cwd)` via `agent.runtime_cwd`.
  Gateway dispatch (`gateway/run.py::_set_session_env`) calls it WITHOUT `cwd` →
  all gateway sessions share the global `terminal.cwd` (bridged to TERMINAL_CWD).
  **There is no built-in per-chat workdir pin.**
- `plugins/platforms/telegram/adapter.py`:
  - `thread_id` read from `message.message_thread_id`; used when
    `is_topic_message or is_forum_group`.
  - DM Topics: `_dm_topics` map (topic_name -> thread_id) populated from
    `config.extra.dm_topics` (`[{chat_id, topics:[{name, thread_id, icon_color}]}]`).
    `ensure_dm_topic()` CREATES a topic via the Bot API and persists
    (`_persist_dm_topic_thread_id`) when missing — so DM threads are first-class.
  - Session source: `chat_type` becomes `"forum"` for supergroups with thread_id,
    else `"group"`; private stays `"dm"` — thread_id appended to the SessionSource.

## Per-channel overrides

- `gateway/config.py` — `ChannelOverride` dataclass: `model`, `provider`,
  `system_prompt`. Config path: `gateway.platforms.<name>.channel_overrides[channel_id]`.
  Docstring: "Enables different channels (e.g. Discord #daily vs #dev) to use
  different models and personas without running separate gateway instances."
- `gateway/run.py` — override lookup ordered by `chat_id`, then `thread_id`
  (~L2447-2484); model resolution priority: session `/model` → channel_overrides →
  global default (~L3789).
- **Session-creation caveat:** the override system_prompt is baked into a session
  at creation. Changing config does not rewrite an existing session's prompt —
  user must `/new` in the channel.

## Slash commands in messaging

- `/new`, `/model [provider:model]`, `/personality`, `/retry`, `/undo`, `/status`,
  `/whoami`, `/stop`, `/approve`, `/deny`, `/sethome`, `/compress`, `/title`,
  `/resume`, `/sessions`, `/usage`, `/insights`, `/reasoning`, `/voice`,
  `/rollback`, `/background <prompt>`, `/reload-mcp`, `/update`, `/help`.
- `/topic` dispatcher exists (`canonical == "topic"` → `_handle_topic_command` in
  `gateway/run.py`, incl. `_ensure_telegram_system_topic`) for topic-enabled chats;
  it is NOT in the registered bot command menu the way the core list is — treat it
  as impl detail unless a doc says otherwise.
- Destructive `/new` confirm: users can opt out (`approvals.destructive_slash_confirm`
  in config.yaml); the gateway logs `User opted out of destructive slash confirm`.

## Verification probes

```bash
# bot online + round-trip
grep -E "Connected to Telegram|telegram connected" $LOCALAPPDATA/hermes/logs/gateway.log | tail
# session created for a chat/group
grep -oE "telegram:(group|forum|dm):[0-9-]+" $LOCALAPPDATA/hermes/logs/gateway.log | sort -u
# providers/models visible in /model == your config providers (custom_providers list)
python -c "import yaml; c=yaml.safe_load(open(r'C:\Users\Kibe\AppData\Local\hermes\config.yaml')); print([p.get('name') for p in c.get('custom_providers',[])], c.get('model'))"
```

## Model-switcher note

`/model` shows providers with counts like `9router (2)` — the `(N)` is the number
of models/entries that provider exposes (autodiscovery), not a ranking. To switch
a session: `/model <provider>:<model>`; to return, `/model` again and pick.