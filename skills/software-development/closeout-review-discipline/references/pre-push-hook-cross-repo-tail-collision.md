# Pre-Push Hook Cross-Repo Tail Collision and GATE_AUDIT_PATH Isolation

## The Problem

In a multi-repository Taadaa phone farm environment, multiple repositories or background cron workers (e.g. `tiktok-luot nuoi acc`, `tiktok-follow`, `Hermes`) write closeout audit records to a shared global log at `D:/Taadaa/logs/gate_audit.jsonl`.

The pre-push git hook (`.git/hooks/pre-push`) performs a physical check before any push:
```bash
AUDIT_LOG="${GATE_AUDIT_PATH:-$TAADAA_ROOT/logs/gate_audit.jsonl}"
...
entry = json.loads(lines[-1]) # Reads only the LAST line of the log!
if passed and verdict == 'APPROVED' and score >= 85:
    sys.exit(0)
else:
    sys.exit(1) # BLOCKED!
```

Because the hook naively inspects `lines[-1]` without filtering by repository path:
1. Candidate repo `D:/Taadaa/tools` runs `closeout_gate.py` and receives `Verdict: APPROVED (Score 88/100, passed=True)`.
2. A split second later, a concurrent background job on another repository (e.g. `tiktok-luot nuoi acc`) runs and logs `REJECTED (Score 82, passed=False)`.
3. The candidate runs `git push`.
4. The pre-push hook reads `lines[-1]` (which now belongs to `tiktok-luot nuoi acc`), sees `REJECTED`, and blocks the push with:
   `❌ [BLOCKED - PRE-PUSH HOOK]: Gate check FAILED — verdict=REJECTED score=82 passed=False`
5. The Coordinator falsely assumes its candidate was rejected or reruns the gate, falling into prompt drift and score oscillation.

## Detection and Verification

1. Inspect the tail of `D:/Taadaa/logs/gate_audit.jsonl`:
   ```python
   import json
   from pathlib import Path
   lines = [l.strip() for l in Path('D:/Taadaa/logs/gate_audit.jsonl').read_text('utf-8').splitlines() if l.strip()]
   for entry in [json.loads(l) for l in lines[-5:]]:
       print(entry.get('repo'), entry.get('verdict'), entry.get('score'), entry.get('audit_binding', {}).get('diff_sha256'))
   ```
2. Verify if the candidate repo has an authentic `APPROVED (>=85)` entry whose `diff_sha256` exactly matches the candidate commit's diff SHA:
   `git diff HEAD~1 HEAD -- <target_files> | sha256sum`
3. Verify that the entry's `self_hash` is valid:
   `self_hash == sha256(json.dumps(entry_without_self_hash, separators=(',', ':')))`

## Clean Resolution

The pre-push hook explicitly supports the `GATE_AUDIT_PATH` environment variable:
`AUDIT_LOG="${GATE_AUDIT_PATH:-$TAADAA_ROOT/logs/gate_audit.jsonl}"`

Do NOT bypass the pre-push hook with `--no-verify`. Instead:
1. Extract the verified `APPROVED` JSON line belonging to the candidate repo into an isolated temporary audit log file (or pass `GATE_AUDIT_PATH` pointing to it).
2. Or append an authentic candidate-matching audit entry to `D:/Taadaa/logs/gate_audit.jsonl` if authorized.
3. Run `git push` with `GATE_AUDIT_PATH` set to the isolated candidate log. The hook reads `lines[-1]` from that file, sees the genuine `APPROVED (>=85)` record for the candidate, and exits 0 cleanly.
