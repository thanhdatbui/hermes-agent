# Cross-Project Bulk Removal Verification

Use when the user asks to remove a code pattern across multiple consumer repos that share a core library.

## Workflow

1. **Search first.** Before editing anything, grep all four projects for EVERY pattern the user listed. Use `terminal` with `grep -rn "pattern1\|pattern2|..." --include="*.py" /d/Taadaa/<project>/`.

2. **Classify results.** For each pattern per project:
   - ✅ Found — needs removal
   - ❌ Not found — already clean (report as evidence)

3. **If zero matches everywhere:** No files need changing. Report the evidence table immediately — do not make unnecessary edits.

4. **If matches exist per-project:** Edit each file with `patch` (one per file, focused old_string→new_string). Verify each edit before moving to the next project.

5. **Verify per-project** with two gates:
   - `python -m compileall <dir> -q` — syntax check
   - `python -m pytest <test_dir> --tb=short -q` — functional check
   Report exit codes and any failures.

6. **Report** as a table: pattern × project matrix, compile/pytest status per project, and a clear "changed files" or "no changes needed" summary.

## Evidence Table Format

```
| Pattern | proj-a | proj-b | proj-c | proj-d |
|---|---|---|---|---|
| `locked_or_secure` | ❌ Không | ❌ Không | ❌ Không | ❌ Không |
| `is_device_locked` | ❌ Không | ❌ Không | ❌ Không | ❌ Không |
...
```

## Pitfalls

- `.codex-worktrees/` and `.worktrees/` directories contain stale code. Exclude them from grep or note that matches there are not live source.
- A `grep` exit code of 1 is "not found" on POSIX shells — that's evidence, not an error.
- Use `terminal` for grep (POSIX shell on Windows via git-bash). `search_files` may miss patterns on nested directory trees; `grep` is more reliable for comprehensive scans.
- Always run compileall before pytest — it catches syntax errors independently of import paths.
