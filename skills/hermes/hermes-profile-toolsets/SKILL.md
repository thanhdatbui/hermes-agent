---
name: hermes-profile-toolsets
description: "Create & verify Hermes profiles with toolset lockdown — agent.disabled_toolsets read-only coordinator (2-profile anti-self-write setup), runtime tool verification."
version: 1.0.1
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [hermes, profiles, toolsets, disabled_toolsets, lockdown, read-only, coordinator, delegation]
    related_skills: [hermes-agent, hermes-multi-deploy, hermes-orchestration-dispatcher]
---

# Hermes Profile Creation & Toolset Lockdown

Create isolated Hermes profiles (`~/.hermes/profiles/<name>/` — or `%LOCALAPPDATA%\hermes\profiles\<name>\` on Windows) and lock them down by disabling write/exec toolsets via `agent.disabled_toolsets`. Primary use case: the 2-profile anti-self-write design — a **read-only coordinator** session that cannot write files/run code, forcing it to delegate (`delegate_task`) to a **worker** running in the default profile.

**Rule of thumb for the lockdown list** — disable every toolset that can write/execute; keep every toolset that is read-only plus `delegation` (delegate_task is the whole point of a coordinator):

```yaml
agent:
  disabled_toolsets:
    - file            # write_file + patch (also removes read_file/search_files — accepted trade-off)
    - terminal        # terminal + process
    - code_execution  # execute_code
    - computer_use    # desktop GUI control
    - cronjob         # scheduled jobs
    - project         # workspace switching (project_create/switch)
    - memory          # memory writes
    - image_gen       # image_generate — auto-enabled by subset-inference, NOT default-off!
    - kanban          # coordinator ONLY. Worker profiles (dispatcher-spawned, HERMES_KANBAN_TASK) must NOT disable kanban — the runtime auto-append is undone by the disabled-subtraction that runs last (see references/kanban-roles-and-profile-wiring.md)
```

## Verified mechanics (source-verified against hermes_cli)

- `agent.disabled_toolsets` is a **list of toolset NAMES** in `config.yaml`. In `hermes_cli/tools_config.py::_get_platform_tools` it is subtracted from the enabled-toolset set **AFTER** bundle expansion (`hermes-cli` → individual configurable toolsets), so it works correctly per toolset name and overrides everything else (incl. `hermes tools` picker).
- **`hermes config set` CANNOT write list values.** `set_config_value` (`hermes_cli/config.py`) only coerces bool/int/float. A JSON string `'["file","terminal"]'` is stored as a plain string → at runtime `{str(ts) for ts in <string>}` iterates CHARACTERS → silent no-op (nothing disabled, no error). Use the python yaml fallback below on the PROFILE config.
- `file` is NOT granular: `{read_file, write_file, patch, search_files}` in one toolset. Blocking it costs read_file/search_files. Decision: block anyway — keeping `file` lets the coordinator self-write, defeating the whole design. Coordinator verifies via worker reports, `session_search`, skill_view, web/browser.
- `agent.disabled_toolsets` is subtracted **LAST** in `_get_platform_tools` (hermes_cli/tools_config.py ~1904-1912) → it overrides every earlier branch (subset-inference, composite expansion, plugin auto-enable). You do NOT need to enumerate every toolset in `platform_toolsets`; a short `platform_toolsets.cli` allowlist + a comprehensive `disabled_toolsets` gives airtight resolution.
- `no_mcp` in `platform_toolsets.<platform>` disables ALL MCP servers **even when `include_default_mcp_servers=True`** — verified on v0.18.2: `_get_platform_tools(cfg,'cli',include_default_mcp_servers=True)` still returned only the allowlisted toolsets. Use it when a minimal profile must not inherit MCP servers.
- `custom_providers[].models` is a DICT `{model: {context_length}}` at runtime — `_normalize_custom_provider_entry` (hermes_cli/config.py:4911-4937) converts list input to the dict shape, so write the dict shape directly (matches what `hermes` itself writes; avoids the provider showing "(0) models"). `key_env` holds an env-var NAME (e.g. `NINEROUTER_API_KEY`) — not a secret, safe to write; NEVER write `api_key` inline in a profile config.
- Traps: `image_gen` is auto-enabled by static subset-inference (its one tool `image_generate` is in `_HERMES_CORE_TOOLS` and image_gen is NOT in `_DEFAULT_OFF_TOOLSETS = {homeassistant, spotify, discord, discord_admin, video, video_gen, x_search}`). `coding`/`debugging`/`project`/`safe`/`search` are NOT in `CONFIGURABLE_TOOLSETS` → they do NOT leak via subset-inference; no need to block.
- **Kanban worker exception (source-verified `model_tools.py::_compute_tool_definitions`)**: when `HERMES_KANBAN_TASK` is set the runtime appends `kanban` to the enabled set, but the `disabled_toolsets` subtraction runs LAST and strips it again → the dispatcher worker loses `kanban_complete/block/heartbeat/create`. Keep `kanban` OUT of `disabled_toolsets` on any profile that receives kanban tasks (workers). Coordinator still disables it.
- Toolset changes apply to **new sessions only** (prompt-cache invariant) — `/reset` or a fresh session.
- **Surgical single-entry edits use the OFFICIAL API, not the dump script**: set `os.environ["HERMES_HOME"] = <profile home>` (Windows: `%LOCALAPPDATA%\hermes\profiles\<name>`; `get_hermes_home()` in hermes_constants.py reads it), then `cfg = load_config(); cfg['agent']['disabled_toolsets'] = …; save_config(cfg)`. `save_config` writes via `utils.atomic_yaml_write` (temp+fsync+os.replace; UTF-8/allow_unicode; sort_keys=False; IndentDumper) — same formatting hermes itself produces. Reserve `set_disabled_toolsets.py` (plain `yaml.safe_dump`) for (re)setting the whole lockdown list.

## Steps

1. **Snapshot default profile integrity**: `sha256sum ~/.hermes/config.yaml` (before AND after — proof default untouched).
2. **Create profile** (inherits model/provider/.env/SOUL.md/skills/delegation/approvals from active profile):
   ```bash
   hermes profile create coordinator --clone --description "Coordinator: read-only, delegates workers"
   # --no-skills for empty; --clone-all for full state copy; alias wrapper created (e.g. coordinator.bat)
   ```
3. **Set `agent.disabled_toolsets`** — official CLI can't (see above), so use the bundled script:
   ```bash
   python scripts/set_disabled_toolsets.py <profile_config_path> [toolset ...]
   # e.g. C:\Users\<user>\AppData\Local\hermes\profiles\coordinator\config.yaml
   ```
   This is the sanctioned fallback: yaml.safe_load → modify ONLY the profile's config → yaml.safe_dump(sort_keys=False, allow_unicode=True). Never hand-edit the DEFAULT config; default's `hermes config set` is the only path there.
   For **minimal standalone profiles** (worker lanes, no coordinator clone): `hermes profile create <name> --no-skills --no-alias --description "..."` creates the dir but NO `config.yaml` (verified v0.18.2). Author the profile config from scratch with `utils.atomic_yaml_write` (repo `utils.py:227` — temp+fsync+os.replace, `IndentDumper`, `sort_keys=False`): `_config_version: 33` (matches root; `config check` shows "Config version: 33 ✓"), `model.provider`/`model.default`, `custom_providers` (dict-shape `models`), `platform_toolsets.cli` allowlist (+ `no_mcp`), `agent.disabled_toolsets`. `load_config` deep-merges with `DEFAULT_CONFIG` (hermes_cli/config.py:7093-7107), so a minimal config parses fine and missing keys fall back to defaults — no migration required.
4. **Verify chain** (all PASS required):
   - `hermes profile list` (◆ marks active) + `hermes profile show <name>` (path/model/skills/.env)
   - `hermes --profile <name> config check` (version ✓, no errors); `hermes --profile <name> config path` routes to profile file
   - **Runtime tool resolution** — the real proof (not grep): `python scripts/verify_profile_tools.py <profile_config_path>` — calls `_get_platform_tools(cfg, "cli")` + `resolve_toolset()` and asserts write tools ABSENT / read+delegate PRESENT. Exit 0 = lockdown intact. For exact-allowlist profiles, assert `set(tools) == {file, terminal, code_execution}` (and also run with `include_default_mcp_servers=True` to prove `no_mcp` holds).
   - `sha256sum ~/.hermes/config.yaml` unchanged; optionally re-resolve DEFAULT profile and confirm write_file/patch/terminal still PRESENT (worker unaffected).
   - Smoke test a real boot: `hermes -p <name> chat -q "Reply with exactly: OK"` — must return the answer, not a tool error.
   - **Two-stage smoke for routed worker profiles:** first resolve the profile through `resolve_runtime_provider()` and issue one harmless authenticated request using the configured profile model; assert HTTP 200, the returned `response_model`, and an exact token. If a reasoning model returns HTTP 200 with empty `content` at a tiny output cap, retry once with a realistic cap (for example 256) before classifying the route — the first response may have spent the budget before emitting visible text. Keep the retry bounded and report both attempts.
   - **Repo-untouched evidence** (when the plan demands "don't modify the repo"): capture BEFORE/AFTER `git rev-parse HEAD`, `git branch --show-current`, `git diff | sha256sum`, `git diff --name-status | sha256sum`, `git status --porcelain | sha256sum` and show they're identical. Note: dirty worktrees from OTHER workstreams make `--porcelain` hashes noisy (`permission denied` on `.tmp-pytest-agent-loop/` changes them); the tracked `git diff` hash is the stable signal.

## Pitfalls

- **`hermes config set agent.disabled_toolsets '["a","b"]'` silently does nothing** (string stored → char-iteration no-op). Always python-yaml or verify after.
- **Do not disable `delegation`** on the coordinator — `delegate_task` is how it hands work to the worker profile. Worker = default profile via plain `hermes` (no `-p`).
- **Remaining soft-writes if `skills`/`browser` kept**: `skill_manage` (writes SKILL.md) and `browser_click`/`type` (web interaction, not local write). Documented trade-offs; add `skills`/`browser` to the list for absolute strictness.
- **YAML dump drops comments** in the cloned config — cosmetic only, runtime only cares about parseable structure.
- **YAML re-serialization changes byte size** even when semantics are identical (IndentDumper + allow_unicode reflow: observed root 19448→18513 bytes after adding kanban roles). Prove semantic preservation with a dict-level diff (`yaml.safe_load` before/after, compare every key EXCEPT the intended new subtree) — never claim byte-identity after a structured write; only raw-bytes copy gives that.
- **`git status --porcelain` hashes are NOT a stable repo-untouched signal** on a shared dirty worktree: a `permission denied` on one subdir (e.g. `.tmp-pytest-agent-loop/`) changes the porcelain output (observed 32794B→1806B between plan-baseline and execution). Tracked `git diff | sha256sum` + `git diff --name-status` + HEAD are the reliable before/after pair; porcelain is only meaningful when the tree is clean.
- Profile dirs are per-profile isolated: sessions, skills, memories, cron. `--clone` copies skills → coordinator gets 100+ skills; `--no-skills` gives a bare profile.
- On Windows the venv python is `%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\python.exe` (has yaml + hermes_cli importable with `sys.path.insert(0, <hermes-agent dir>)`).
- **`kanban` in `disabled_toolsets` on a worker profile is a lifecycle-breaking trap**: `HERMES_KANBAN_TASK` auto-appends the toolset but the disabled-subtraction undoes it. Verify with `get_tool_definitions(..., quiet_mode=True)` + `HERMES_KANBAN_TASK=1` (model_tools.py), NOT just `_get_platform_tools`/`resolve_toolset` — the latter never model the kanban re-add.
- **Role-level toolsets can restore worker lifecycle — account for both paths.** `_default_spawn` may pass `kanban.orchestration.roles.<step>.toolsets` directly as `--toolsets`; then `model_tools` appends `kanban` under `HERMES_KANBAN_TASK`. A helper that inspects only profile `platform_toolsets.cli` is therefore insufficient whenever a role-level pin exists. Final verification must use the effective role policy toolsets plus the profile's disabled list, and assert `kanban_complete`, `kanban_block`, and `kanban_heartbeat` present while board-routing tools such as `kanban_list` remain absent.
- **`verify_profile_tools.py` asserts the COORDINATOR posture** (`kanban_*` in must_be_ABSENT). Do NOT use it as-is on worker profiles — use `scripts/verify_kanban_worker_tools.py` (kanban lifecycle PRESENT under `HERMES_KANBAN_TASK`, delegate/memory ABSENT), passing/equating the role-level pin when one exists.
- **Self-verifying edit scripts: normalize diff-path prefixes.** A `deep_diff` emitting `.agent.disabled_toolsets` (leading dot) false-positives an "unintended diff" against `p == "agent.disabled_toolsets"` and rolls back a correct write — `p.lstrip(".")` before comparing.
- **`search_files` (ripgrep) fails on MSYS `/d/…`/`/c/…` absolute paths** on this host (os error 3) while terminal `ls`/`grep` work; pass native `C:\…` or repo-relative paths, and switch tools instead of retrying the same failing path (loop warning fires after 3-4).

## Support files

- `scripts/set_disabled_toolsets.py` — set the lockdown list on a profile config (parameterized)
- `scripts/verify_profile_tools.py` — runtime tool-resolution verification (write-absent / read-present asserts) — COORDINATOR posture
- `scripts/verify_kanban_worker_tools.py` — runtime verification for dispatcher worker profiles (kanban lifecycle PRESENT under `HERMES_KANBAN_TASK`; delegate/memory ABSENT)
- `scripts/write_profile_config.py` — author a minimal STANDALONE profile config.yaml from scratch (bare `profile create` writes no config; use when building worker-lane profiles)
- `references/disabled-toolsets-mechanics.md` — source-verified internals: line numbers, full toolset→tools inventory, traps, final verified 23-tool coordinator inventory
- `references/kanban-roles-and-profile-wiring.md` — kanban.orchestration.roles schema, kanban toolset check_fn (HERMES_KANBAN_TASK), runtime resolution order, repo-untouched evidence nuance
- `references/minimum-kanban-worker-profile-verification.md` — end-to-end minimum setup gate: exact role resolution, role-level toolset pin vs profile fallback, lifecycle-schema proof, bounded live smoke, repo preservation, and honest audit-fallback labeling
