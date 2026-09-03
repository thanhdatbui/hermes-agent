# Kanban Role Mapping + profile wiring (source-verified v0.18.2)

Session evidence (2026-08-15, Taadaa Hermes setup task): how Kanban orchestration
roles bind to profiles, and how a minimal profile config resolves at runtime.

## Kanban role mapping location

- Root config `kanban.orchestration.roles` — **does NOT exist by default**; the
  `kanban` top-level key is absent from a fresh config.yaml (verified: root had no
  `kanban` key, so the whole subtree had to be created).
- Role entry shape used and verified:
  ```yaml
  kanban:
    orchestration:
      roles:
        build_script:
          candidates:
            - profile: taadaa-build-script
              model: deepseek-v4-pro
          toolsets: [file, terminal, code_execution]
        fix_automation:
          candidates:
            - profile: taadaa-fix-automation
              model: deepseek-v4-flash
          toolsets: [file, terminal, code_execution]
  ```
- `profile.yaml` description field is surfaced to the kanban decomposer for
  role-based routing (hermes_cli/profiles.py:640-652) — `--description` on
  `profile create` is the right way to seed it; `description_auto: false` means
  human/CLI-authored, not LLM-generated.

## Kanban toolset check_fn (new discovery)

- `kanban` toolset tools ARE in `_HERMES_CORE_TOOLS`, and the real schema is
  **check_fn-gated to `HERMES_KANBAN_TASK`** workers — a session not running as a
  Kanban task won't even see the board tools.
- **Worker vs coordinator posture (2026-08-15 fix)**: for the COORDINATOR, block
  `kanban` in `agent.disabled_toolsets` anyway (belt-and-suspenders). For WORKER
  profiles that receive kanban tasks, `kanban` must NOT be in `disabled_toolsets`:
  `_compute_tool_definitions` (model_tools.py) appends `kanban` to the enabled set
  when `HERMES_KANBAN_TASK` is set, but the `disabled_toolsets` subtraction runs
  LAST and strips it again → the worker silently loses
  `kanban_complete/block/heartbeat/create`. Measured on taadaa worker profiles:
  7 tools / 0 kanban_* (bug) → 18 tools / 11 kanban_* (fixed).
- Correct verification for workers is `get_tool_definitions(enabled_toolsets=…,
  disabled_toolsets=…, quiet_mode=True)` with `HERMES_KANBAN_TASK=1` —
  `_get_platform_tools` + `resolve_toolset` alone never model the kanban re-add.
  Use `scripts/verify_kanban_worker_tools.py` (kanban lifecycle PRESENT,
  delegate/memory ABSENT); `verify_profile_tools.py` asserts the coordinator
  posture and FAILS on workers.
- Plugin-warning noise: importing `hermes_cli.tools_config` while the default
  profile has `autonomous-ai-agents/kanban-claude-lane` / `kanban-codex-lane`
  plugins prints `unknown kind 'integration'` warnings. Cosmetic — does NOT affect
  runtime tool resolution of OTHER profiles (verified exact resolution despite the
  warnings).

## Surgical edit pattern (single entry, e.g. remove one toolset)

- Set `os.environ["HERMES_HOME"] = r"C:\Users\<user>\AppData\Local\hermes\profiles\<name>"`,
  then `cfg = load_config(); cfg["agent"]["disabled_toolsets"].remove("kanban"); save_config(cfg)`.
- `save_config` writes via `utils.atomic_yaml_write` (temp+fsync+os.replace;
  UTF-8/allow_unicode; sort_keys=False; IndentDumper) — same formatting hermes
  itself produces. `set_disabled_toolsets.py` (plain `yaml.safe_dump`) is fine
  for (re)setting the whole list, but reflows the file; prefer the API for
  one-entry edits.
- Read-back proof: deep-diff `yaml.safe_load` before/after and assert ONLY the
  intended path changed. **Normalize diff-path prefixes**: a `deep_diff` that
  emits `.agent.disabled_toolsets` (leading dot) false-positives as an
  "unintended diff" and rolls back a correct write — compare `p.lstrip(".")`.
  Auto-restore baseline bytes on any unintended diff (never leave a half-applied
  config).

## Runtime resolution order (verified by reading tools_config.py)

1. `platform_toolsets.cli` explicit list → `has_explicit_config=True` → direct
   membership of configurable toolsets only (no subset-inference leak).
2. Composite/plugin toolsets merged; `_DEFAULT_OFF_TOOLSETS` subtracted.
3. `no_mcp` sentinel in the toolset list → all MCP servers disabled even with
   `include_default_mcp_servers=True` (verified: with_mcp == without_mcp).
4. `agent.disabled_toolsets` subtracted LAST → overrides everything above.

Net result for the verified minimal profile:
`_get_platform_tools(cfg,'cli',include_default_mcp_servers=False)` →
exactly `{code_execution, file, terminal}`.

## Verification commands that passed (exit 0)

- `hermes profile list` → default ◆ + 2 new profiles with correct models
- `hermes profile show <name>` → Model `X (custom:9router)`, Skills 0, Gateway stopped
- `hermes -p <name> config check` → "Config version: 33 ✓"
- `hermes -p <name> config path` → `...\profiles\<name>\config.yaml`
- Semantic root diff (yaml dict, excluding `kanban`): `[]` — nothing else changed

## Repo-untouched evidence nuance

Plan baseline vs execution porcelain hashes differed (32794B → 1806B) purely due
to `permission denied` on `.tmp-pytest-agent-loop/` during `git status
--porcelain` — the tracked `git diff | sha256sum` (78545B) and `git diff
--name-status` (1063B) matched baseline exactly. Tracked-diff hashes are the
stable repo-untouched proof on a shared dirty worktree; porcelain is not.
