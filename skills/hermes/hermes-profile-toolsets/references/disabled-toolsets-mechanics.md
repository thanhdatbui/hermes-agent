# disabled_toolsets mechanics — source-verified (2026-08-07, against installed source)

## Where the mechanism lives

| Location | What |
|---|---|
| `hermes_cli/tools_config.py` ~L1646 `_get_platform_tools(config, platform)` | resolves platform's saved toolsets → set of enabled CONFIGURABLE toolset names |
| `hermes_cli/tools_config.py` ~L1904-1912 | `agent.disabled_toolsets` subtracted LAST from the enabled-toolset set → overrides everything, including `hermes tools` picker saves |
| `hermes_cli/tools_config.py` ~L60 `CONFIGURABLE_TOOLSETS` | the only toolset keys the subset-inference loop (L1739-1749) auto-enables |
| `hermes_cli/tools_config.py` ~L118 `_DEFAULT_OFF_TOOLSETS` | `{homeassistant, spotify, discord, discord_admin, video, video_gen, x_search}` — subtracted for default installs |
| `toolsets.py` `TOOLSETS` + `_HERMES_CORE_TOOLS` | toolset→tool definitions; `bundle_non_core_tools` (L666) exists so disabling a BUNDLE name never wipes core |
| `hermes_cli/config.py` `set_config_value` ~L8268-8340 | `hermes config set` value coercion: ONLY `true/false/yes/no/on/off` → bool, digits → int, float → float. **No JSON/YAML list parsing.** |

## Why `hermes config set agent.disabled_toolsets '[...]'` silently fails

`set_config_value` receives the raw string. `_default_value_for_key("agent.disabled_toolsets")` returns the DEFAULT_CONFIG leaf (a list, so not a str → coercion branch runs) — but the JSON string matches none of the bool/int/float branches, so it's stored **as a string**. At runtime: `disabled_set = {str(ts) for ts in "[\"file\",\"terminal\"]"}` → set of single characters → subtraction is a no-op. **Zero error, zero lockdown.** Always verify at resolution level (script) or use the python-yaml fallback.

## Bundle expansion order (why per-name subtraction works)

`platform_toolsets.cli: [hermes-cli]` → no explicit configurable keys → else-branch (L1731-1749): resolve bundle to tool names → reverse-map to CONFIGURABLE_TOOLSETS keys whose static tools ⊆ resolved set → then `enabled_toolsets -= disabled_set`. So `disabled_toolsets` operates on toolset NAMES like `file`, not bundle names — correct.

## Toolset → tools inventory (relevant subset)

| Toolset | Tools | Notes |
|---|---|---|
| `file` | read_file, write_file, patch, search_files | NOT granular — blocking loses read_file too |
| `terminal` | terminal, process | |
| `code_execution` | execute_code | granular, one tool |
| `computer_use` | computer_use | cua-driver GUI control |
| `cronjob` | cronjob | |
| `project` | project_list, project_create, project_switch | GUI-gateway only; harmless to block for CLI |
| `memory` | memory | writes memory store |
| `image_gen` | image_generate | **auto-enabled** (tool in core, not in _DEFAULT_OFF) — must block explicitly |
| `kanban` | kanban_show/list/complete/block/heartbeat/comment/create/link/unblock/... | tools in core → auto-enabled at resolution; check_fn gates schema to HERMES_KANBAN_TASK workers; block anyway |
| `skills` | skills_list, skill_view, skill_manage | skill_manage is a soft-write; keep for skill_view |
| `delegation` | delegate_task | **DO NOT BLOCK on coordinator** — it's the whole point |
| `browser` | navigate/snapshot/click/type/scroll/back/press/get_images/vision/console/cdp/dialog + web_search | click/type = web interaction, not local write |
| `web` / `search` | web_search, web_extract / web_search | pure reads |
| `session_search`, `todo`, `clarify`, `tts`, `vision` | read-only / benign | keep |
| `coding`, `debugging`, `safe`, `search` | — | NOT in CONFIGURABLE_TOOLSETS → never auto-enabled by inference → no need to block |

## Verified final state (coordinator profile, 2026-08-07)

- `disabled_toolsets = [file, terminal, code_execution, computer_use, cronjob, project, memory, image_gen, kanban]`
- Resolution result: enabled = `[browser, clarify, delegation, session_search, skills, todo, tts, vision, web]` → **23 tools**
- Absent: write_file, patch, terminal, process, execute_code, computer_use, cronjob, project_create/switch, memory, image_generate, all kanban_* writes
- Present: delegate_task, session_search, skill_view, skills_list, web_search, web_extract, browser_navigate/snapshot, vision_analyze, todo, clarify, text_to_speech
- Default profile untouched (sha256 `7d78d4c8...` identical pre/post) — write_file/patch/terminal/process/execute_code still PRESENT there (worker capacity intact)

## Verification chain commands

```bash
sha256sum ~/.hermes/config.yaml                       # before AND after
hermes profile list && hermes profile show coordinator
hermes --profile coordinator config check
hermes --profile coordinator config path              # must point into profiles/<name>/
python scripts/verify_profile_tools.py <profile_config_path>   # runtime resolution asserts
hermes -p coordinator chat -q "Reply with exactly: OK"          # real session boot smoke test
```
