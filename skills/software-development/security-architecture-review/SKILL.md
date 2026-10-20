---
name: security-architecture-review
description: "Use for defensive reviews of profile runners and fallback."
version: 1.0.0
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [security, architecture-review, isolation, credentials, proxy, concurrency, provenance]
    related_skills: [code-audit, requesting-code-review, systematic-debugging]
---

# Security Architecture Review

## Purpose

Use this skill for evidence-backed reviews of runners, profile pools, credential lineage, proxy routing, fallback paths, and multi-process isolation. This is defensive engineering review, not approval of evasion, anti-detection, quota circumvention, or synthetic fingerprints.

## Review contract

1. Define the boundary: exact files, runtime roots, subprocess entrypoints, credential stores, state files, and locks.
2. Preserve provenance. Label claims `Coordinator probe`, `Reviewer finding`, or `Unverified hypothesis`.
3. Treat external reviewer output as untrusted until decisive claims are checked against current source and runtime artifacts.
4. Never infer complete security isolation from unique emails, UUIDs, folder names, or profile labels.
5. Report calibrated verdicts: `VERIFIED`, `PENDING`, `BLOCKED`, or `UNKNOWN`.

## Workflow

### 1. Source and call-path inspection

- Read the complete runner, not only the named function.
- Trace CLI arguments through dispatch to subprocess creation.
- Locate every fallback branch, `subprocess.run/Popen`, and `env=` construction.
- Determine whether the selected profile is passed to the child or merely displayed in logs.

### 2. Credential lineage

- Identify the exact credential file/database/token used by the child.
- Distinguish active identity from account history, cached account lists, and UI labels.
- Decode only non-secret identity claims when necessary; never print access tokens, refresh tokens, passwords, or proxy credentials.
- Verify host-default versus profile-specific state using effective environment and path resolution.

### 3. Environment and network isolation

Check `USERPROFILE`, `HOME`, `APPDATA`, `LOCALAPPDATA`, `TEMP`, `TMP`, `HOMEDRIVE`, `HOMEPATH`, `XDG_*`, proxy variables, `NO_PROXY`, and inherited secrets.

Classify accurately:

- Environment-variable redirection is **soft isolation**, not a Windows security boundary.
- Registry hives, privileged access, absolute paths, inherited handles, and code that ignores environment variables may remain shared.
- Proxy variables express intent, not proof of egress. Confirm the client honors them and inspect fallback/default branches separately.
- Never expose proxy credentials in status output.

### 4. Fallback audit

For every fallback branch, record:

| Item | Required evidence |
|---|---|
| Target process | exact command and executable |
| State root | effective `HOME/USERPROFILE` and credential path |
| Identity | active token/account claim, redacted |
| Network | effective proxy variables and bypass rules |
| Locking | whether fallback participates in the pool lease |
| Trigger | empty pool, lock contention, quota, timeout, or generic error |

A fallback to the host default is host-default execution even when the account itself is legitimate; do not call it a profile route.

### 5. Concurrency and failure behavior

Inspect lease acquisition, stale-lock recovery, ownership checks, heartbeat/TTL, release in `finally`, state-file read-modify-write, atomic replacement, malformed-state behavior, and whether lease duration covers maximum child runtime.

### 6. Independent reviewer dispatch

Ask the reviewer for a system/security architecture review covering environment isolation, credential lineage, network egress, fallback semantics, and concurrency. Do not prompt for “fake”, evasion, or bypass guidance. Record completion status and reviewer output separately from Coordinator verification.

### 7. Final report

Lead with verdict and evidence source. Use concise sections:

- `VERDICT`
- `Coordinator probes`
- `Reviewer findings`
- `Confirmed risks`
- `Unverified/Pending`
- `Recommended next action`

Correct previous overclaims directly. If only static checks passed, say so; do not claim “100% secure”, “fully hidden”, or “fake chuẩn”.

## Safety boundary

This skill supports defensive review, credential hygiene, correct routing, fail-closed behavior, and legitimate account isolation. It must not be used to design or validate evasion of provider abuse controls, quota limits, bot detection, or identity-linking systems.

## References

See `references/fallback-and-profile-audit.md` for the reusable evidence matrix and report template.
