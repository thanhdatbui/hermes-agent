# Third-party TikTok downloader repo canary

Use this reference when evaluating an external downloader without touching the production consumer.

## Acceptance matrix

Evaluate two independent capabilities:

| Capability | Required evidence | Interpretation |
|---|---|---|
| Profile discovery | A public profile returns concrete `/@handle/video/<id>` URLs; record candidate count and deduplicated IDs | Required for a profile-based source pool |
| Direct download | A concrete public video URL produces a file outside production; file is >1 KiB and `ffprobe` reads container and duration | Confirms only single-URL download |

Do not promote a repo unless both rows pass. A direct-download pass must never be reported as profile-discovery success.

## Isolation recipe

1. Capture production `git status --short --branch` and a process list before the test. Preserve pre-existing dirty files exactly.
2. Clone each candidate under a temporary root outside the production repository.
3. Create one venv per candidate. Install only that candidate's dependencies. If a browser binary is missing, install it or point the candidate to an already-installed browser **inside the temporary test command**; never modify the production venv.
4. Use a temporary output directory. Do not pass production `state.db`, workbooks, manifests, ledgers, cookies, browser profiles, proxy-auth, tokens, or API keys.
5. Run one bounded profile probe and one bounded direct-URL probe. Close browser/process resources in `finally`/context-manager cleanup.
6. Re-check production git status, process list, and output location after the probe.

## Evidence schema

Keep a small redacted result object with:

```json
{
  "repo": "owner/name",
  "revision": "short-sha-or-release",
  "profile": {
    "status": "OK|BLOCKED|ERROR",
    "candidate_count": 0,
    "sample_ids": ["redacted-or-public-id"]
  },
  "direct": {
    "status": "OK|BLOCKED|ERROR",
    "bytes": 0,
    "container": "mp4",
    "duration_seconds": 0
  },
  "isolation": {
    "production_git_unchanged": true,
    "production_state_written": false,
    "output_outside_production": true,
    "matching_processes_left": false
  }
}
```

Never include cookie values, `msToken`, `X-Bogus`, `X-Gnarly`, proxy credentials, browser storage, full request headers, or response headers in the evidence. Keep only status, redacted error class, byte count, duration, and paths outside production.

## Blocker classification

- `PROFILE_DISCOVERY_BLOCKED_CAPTCHA`: challenge/puzzle appears; do not automate solving or bypass it.
- `PROFILE_DISCOVERY_EMPTY_OR_INVALID`: profile endpoint returns empty/malformed data or no concrete video URLs.
- `DIRECT_DOWNLOAD_BLOCKED`: concrete URL cannot be resolved/downloaded.
- `SETUP_BLOCKED`: dependency/browser missing. Fix setup in the temporary venv and retry once; do not encode a setup failure as a permanent capability claim.

Report the blocker phase, not a generic "repo failed". Keep the production pipeline untouched until a candidate passes both canaries and a separate integration plan is approved.
