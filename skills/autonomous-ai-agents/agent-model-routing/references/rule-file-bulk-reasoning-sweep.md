# Bulk reasoning-effort sweep across rule files (flash/max → flash/high)

When the user changes the worker reasoning level across ALL orchestration rules
(e.g. 2026-08-06: deepseek-v4-flash max → high everywhere, "đổi qua v4 flash high hết"),
sweep these files:

## Scope
- `D:\Taadaa\AGENTS.md` — canonical disk copy, NOT in git. Memory says "Cấm tự sửa
  AGENTS.md" → **get explicit user confirmation to override** before touching it
  (confirmed 2026-08-06 via clarify).
- `D:\Taadaa\HERMES_SUBAGENT_RULES.md`
- Every consumer repo `AGENTS.md` / `CLAUDE.md` under `D:\Taadaa\*`
  (`find -maxdepth 2` catches them; some sit deeper, e.g. `Hermes/apps/desktop/AGENTS.md`).

## Replacement patterns (apply in this order)
| From | To |
|---|---|
| `deepseek-v4-flash/max` | `deepseek-v4-flash/high` |
| `flash/max` | `flash/high` |
| `reasoning_effort=max` | `reasoning_effort=high` |
| `` `deepseek-v4-flash`/`max` `` (backtick form, e.g. AGENTS.md line ~1416) | `` `deepseek-v4-flash`/`high` `` |

## KEEP untouched (Codex side — do NOT sed these)
- `gpt-5.6-luna/max`, `Luna/max`, `Sol/max`, `Terra/high`
- `model_reasoning_effort="max"` (Codex CLI command inside AGENTS.md)

## Workflow
1. Inventory: `find /d/Taadaa -maxdepth 2 \( -name AGENTS.md -o -name CLAUDE.md -o -name HERMES_SUBAGENT_RULES.md \)` excluding `.git|node_modules|.worktrees|*-worktrees|runtime-sync`.
2. Grep-count per file first (`grep -c 'flash/max\|reasoning_effort=max'`) to know the blast radius.
3. Backup each file BEFORE editing: `cp "$f" "$f.flash-high-$(date +%Y%m%d-%H%M%S).bak"`.
4. Edit with **bash `sed -i`**, NOT Python.

## PITFALL: Python `open(f,'w')` → PermissionError on some AGENTS.md (Windows/MSYS)
On this machine several `D:\Taadaa\*/AGENTS.md` throw `PermissionError: [Errno 13]`
from Python `open(f,'w')` even though:
- `os.stat` shows mode `0o100666` (writable)
- `open(f,'r+')` succeeds
- bash `echo test >> file` succeeds

Cause is a Windows/MSYS file-lock quirk (agent/scheduler processes with cwd in those
dirs, or OneDrive sync). Workaround: **do the edit with `sed -i` + `cp` backup in bash**
— bash writes succeed where Python `open(w)` fails. Don't fight it; switch to sed.
(If you accidentally appended a probe line with `echo >>`, remove it with `sed -i '$ d'`.)

## Verify
- `grep -rn 'flash/max\|deepseek-v4-flash/max'` (excl. .git/bak/worktrees) → **0 hits**
- `grep -rn 'reasoning_effort=max'` → **0 hits**
- `grep -rl 'gpt-5.6-luna/max\|Luna/max'` → **still N hits** (Codex untouched)
- Watch for variant spellings (backtick form) that plain `flash/max` sed misses.

## After sweep (companion changes, done in the same operation)
- `hermes config set agent.reasoning_effort high` (config.yaml)
- 9router `settings.providerThinking.commandcode.mode` → `"high"` (see skills
  `9router-proxy-ops` / `hermes-9router-ops`)
- **All open Hermes sessions must `/new`** — reasoning_config resolves at session
  init; a session opened before the change still sends the old effort. Verify the
  session's actual effort via `resolve_reasoning_config(load_config(), model)`.
