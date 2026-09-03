# Taadaa opencode-audit wrapper (`invoke-opencode-audit.ps1`)

Path: `D:\Taadaa\tools\invoke-opencode-audit.ps1`

## What it does
Read-only audit of a Taadaa repo via `opencode run --agent taadaa-review --format json`
(prompt template lives in the script). Model cascade strong → weak, advancing only on
quota/capacity-classified failures (regex: quota, rate limit, 429, 502, ResourceExhausted, ...):

- `opencode/nemotron-3-ultra-free` — strongest (NVIDIA), may hit 502 limit
- `opencode/ling-3.0-tiny-free` — stable fallback (**was `ling-3.0-flash-free` until 2026-08-07**)
- `opencode/longcat-2.0-free`
- `opencode/north-mini-code-free`

## Failure modes (exact error strings)
- `OPENCODE_NOT_FOUND` — opencode CLI not on PATH
- `REPO_ROOT_NOT_DIRECTORY`
- `OPENCODE_FREE_MODEL_CATALOG_EMPTY` — `opencode models` returned no `opencode/*-free` / `freemodel/*` lines
- `OPENCODE_MODEL_NOT_ALLOWED: allowed models: ...` — `-Model` not in the `$models` allowlist (lines ~66-73)
- `OPENCODE_FREE_MODEL_UNAVAILABLE_IN_CATALOG` — allowlist models absent from live `opencode models` output
- `OPENCODE_AUDIT_FAILED_NON_QUOTA_EXIT_<code>` — opencode exited non-zero without quota pattern
- `OPENCODE_AUDIT_MODEL_UNAVAILABLE` — whole cascade exhausted on quota failures

## Model catalog renames (verified 2026-08-07)
`opencode models | grep ling` → only `ling-3.0-tiny-free` remains; `ling-3.0-flash-free` is gone.
OpenCode free IDs get renamed/dropped without warning. Before trusting any `opencode/*-free` id:
`opencode models | grep <slug>`. When a rename lands, update BOTH the allowlist array AND the
`-Model` invocation — not just one.

## Verify recipe (after allowlist edits)
```bash
powershell -ExecutionPolicy Bypass -File "D:\Taadaa\tools\invoke-opencode-audit.ps1" \
  -RepoRoot "D:\Taadaa\automation-core" -Prompt "test" \
  -OutputDirectory "$TMP/opencode-test" -Model "opencode/<new-model>"
```
- The gate passes EARLY: `OPENCODE_MODEL=<model>` prints before the agent run starts, so a
  MODEL_NOT_ALLOWED failure shows up in seconds.
- A full run takes ~5-8 min (real agent, tool calls). Exit 0 = report written + all
  `OPENCODE_AUDIT_*` lines printed.
- `-Prompt "test"` is fine for allowlist verification — a non-audit prompt may fail differently,
  but any failure other than MODEL_NOT_ALLOWED / catalog errors is acceptable proof of the fix.

## Gotchas
- **Report JSONL is UTF-16LE** (`Tee-Object` default encoding). `tail`/`grep` in bash show
  `\u0000` between every char. Read with PowerShell `Get-Content`, or convert
  (`iconv -f UTF-16LE -t UTF-8`).
- **Parsing the `$models` literal for ad-hoc verification**: regex `\$models\s*=\s*@\((.*?)\)`
  stops at the FIRST `)` — which is inside the `# strongest (NVIDIA)` comment. Anchor the end
  to a closing paren on its own line: `\$models\s*=\s*@\((.*?)\r?\n\)`, then extract quoted ids
  with `'([^']+)'` matches.
- The gate is `$models -notcontains $Model` — the `-Model` arg must match the allowlist EXACTLY
  (same casing, full `opencode/` prefix).
- `opencode models` output includes ANSI color codes; the script strips them
  (`\x1b\[[0-?]*[ -/]*[@-~]`) before matching `^(?:opencode/.+-free(?:$|[-:])|freemodel/.+)$`.
