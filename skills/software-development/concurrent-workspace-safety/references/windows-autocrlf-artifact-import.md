# Windows `core.autocrlf` exact-byte import recipe

Use this when importing already-committed LF artifacts into a Windows worktree whose global Git config has `core.autocrlf=true`.

## Evidence sequence

```bash
# Before merge: preserve exact bytes outside the repository
python -c "from pathlib import Path; import hashlib; ..."

# After merge: compare raw bytes to the commit blob
python -c "from pathlib import Path; import subprocess, hashlib; p='path'; a=Path(p).read_bytes(); b=subprocess.check_output(['git','show','HEAD:'+p]); print(len(a), len(b), hashlib.sha256(a).hexdigest(), hashlib.sha256(b).hexdigest(), a==b)"
git ls-files --eol -- <allowlist>
```

If the worktree is CRLF-expanded while `git show` and the preserved copy are identical LF bytes, copy the preserved bytes back **only** for the exact allowlist. Then refresh Git's stat cache:

```bash
git update-index --really-refresh -- <allowlist>
git status --short --untracked-files=all
```

The refresh is important: after raw-byte restoration, Git may keep stale index stat information and report the exact-byte files as modified. Verify both raw equality and the final status path set; do not stage solely to make status look clean.

Run the canonical suite, focused nodes, compile gate, and `git diff --check`. If an immutable adopted artifact has pre-existing trailing whitespace, preserve its hash and report the exact warning; run a second diff-check excluding that immutable path and require it to pass.

## Failure interpretation

- **Commit blob == preserved bytes, worktree differs only by CRLF:** checkout normalization; restore exact bytes, not a product change.
- **Commit blob != preserved bytes:** source drift; stop and reconcile before merge/push.
- **Raw bytes equal but status says modified:** refresh the index stat cache with `git update-index --really-refresh`; this is bookkeeping, not a reason to stage or amend.
- **Unrelated dirty paths change:** stop; preserve them and investigate concurrent drift rather than normalizing broadly.
