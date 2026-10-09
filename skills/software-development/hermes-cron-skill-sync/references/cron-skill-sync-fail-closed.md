# Cron Skill Sync: Fail-Closed Recovery Checklist

## Incident signature

- The scheduler reports `ok`, but no Git commit or remote update exists.
- A wrapper prints `SYNC_ERROR` but still exits 0.
- A PowerShell sync script has an unconditional early `exit 0`.
- Runtime-local skills and repository skills are separate trees, so creating a skill locally does not publish it automatically.
- A broad runtime copy creates hundreds of unrelated skill diffs.
- GitHub push protection rejects an unpushed commit containing a token.

## Bounded recovery

1. Stop broad sync attempts and preserve unrelated dirty worktree changes.
2. Inspect the intended skill paths only; do not reset, clean, or stash-drop unrelated work.
3. Create a small allowlist/manifest for the skill(s) requested in the current task.
4. Export only those paths, excluding `.env`, auth files, curator state, caches, locks, and generated files.
5. Run `git diff --check` and a focused secret scan over the candidate paths.
6. If a secret is found, redact the file and remove the secret from every unpushed commit that contains it. Rotate/revoke the provider credential separately; never publish the value.
7. Stage only the allowlisted paths and commit them.
8. Let the pre-push hook run normally. Do not insert synthetic audit records or bypass the hook.
9. Push and verify the remote SHA. Only then report `SYNCED`.
10. Make the no-agent wrapper return the child exit code; silence only a real no-change result.

## Evidence standard

A successful cron tick is proven by all of:

- wrapper exit code 0;
- commit SHA created for the intended paths;
- push exit code 0;
- remote branch contains that SHA;
- no secret-scan or pre-push rejection.

`last_status=ok`, a printed success word, or a local commit alone is insufficient.
