# Recipe: propagate a scope-lock / mandatory rule block across a Taadaa repo fleet

Condensed from the 2026-08-22 run that pushed `## Task Contract and Scope Lock (MANDATORY)`
to all 33 repo-root rule files under `D:\Taadaa` and repaired a corrupted literal path in
the root `AGENTS.md`. Use this as the skeleton; adjust TARGETS / block / repair tokens.

## Allowlist shape
Exact paths only — root `AGENTS.md` plus per-repo `AGENTS.md` and `PROJECT_RULES.md`.
32 of the 33 targets lacked the marker; root already had it (repair was the only change there).

## Hard constraints honored
- Backups + SHA-256 baseline live OUTSIDE `D:\Taadaa` (`C:\Users\Kibe\scope-lock-op\backup\`).
- Original EOL preserved per file (31 CRLF, 1 LF = `AI-Tools/AGENTS.md`).
- Existing bytes before the appended block unchanged (prefix == backup[:len]).
- Root lines 1533-1534 repaired to literal
  `D:\Taadaa\runtime\kibe\cron-state\manifests\<ngày>\active_manifest.json`
  (corruption had split the path with a stray LF + BEL 0x07).
- Distinct backup basenames: `relpath '/' -> '__'` so duplicate `AGENTS.md` names don't clash.
- Nothing committed/pushed; no source/test/config touched.

## Step skeleton (run as file-based script, not terminal heredoc)
1. `backup_dir` outside fleet; for each target write a `path.replace('/','__')` copy and
   record `baseline_sha256.json`.
2. Extract canonical block BY BOUNDARY from source: `start = idx(marker line)`;
   `end = next line starting with b'### '`; `block = b'\n'.join(lines[start:end])`
   (strip one trailing blank). Never use hardcoded indices like `[67:99]` — the wrapping
   bullet pushes past them and captures the next subsection.
3. Repair (idempotent): `if data.count(old_tok)==1: data = data.replace(old_tok, new_tok)`,
   assert `b'\x07' not in data`. Prove scope with `data.replace(new_tok, old_tok) == backup`.
4. Append to each subdir target: `eol = b'\r\n' if b'\r\n' in b else b'\n'`;
   `block_eol = block.replace(b'\n', eol)`;
   `out = b + (eol if not b.endswith(b'\n') else b'') + eol + eol + block_eol + eol`.
5. Verify with `scripts/verify_append_outside_d.py` (byte-exact: `cur[len(base):]` ==
   `eol+eol+block_eol+eol`; marker==1; prefix unchanged; EOL class preserved; target-only
   walk finds 0 non-target markers).

## Gotchas that burned this run
- Terminal `python3 - <<'PY'` with bytes literals (`b'...D:\Taadaa\nuntime...'`) raises
  `SyntaxWarning: invalid escape sequence '\T'` and produces non-matching tokens. Write the
  script via `write_file`, then `python3 C:/Users/Kibe/.../x.py`. Also avoids the `&&`
  backgrounding guard (use the `workdir` param instead of `cd /d/Taadaa && ...`).
- `search_files` (rg) fails on `/d/Taadaa/...` (`IO error os 2/3`); use `read_file` with
  `D:/...` forward slash or terminal `grep`/`python` with Windows paths.
- A verify that compares a CRLF target's appended block to a hardcoded LF literal FAILS on
  embedded `0x0A` — rebuild the expected block per file EOL.
