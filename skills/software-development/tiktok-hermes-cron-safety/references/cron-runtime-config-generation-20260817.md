# Cron runtime config generation recipe (2026-08-17, live-approval inputs)

When the user approves going live, the operator must generate these inputs BEFORE the
picker/runner can schedule anything. All outputs live OUTSIDE the repo (never commit them):
`D:\Taadaa\runtime\kibe\cron-source\` (inputs + generated config) and
`D:\Taadaa\runtime\kibe\cron-state\` (state JSON + manifests).

## Inputs to the canonical generator (`scripts/generate_cron_source_config.py`)

```
generate_config(projection, assignment, journal, output)
```

1. **safe projection** (`safe_projection.json`): rows with EXACTLY
   `{account_id, machine, serial, row[, target_count, video_available]}` — schema_v1.
   - Build from `taikhoan_run_safe.xlsx` (columns `May | Device ID | ID | Video Đã Đăng`).
   - `row` = PHYSICAL slot within the machine's row group (count ALL rows incl. empty gaps —
     a machine with accounts at rows 1,2,4 gets rows 1,2,4 — user rule: gaps allowed, empty
     rows are skipped at run time).
   - Skip rows with empty account_id (they are excluded from the projection entirely).
   - Strip Excel quote-prefix (`'lipsellczaw` → `lipsellczaw`) and `@` prefix.
   - Serial: prefer canonical device map `Tik1.xlsx` (`Máy | device ID`) per machine; the
     safe workbook serial column may hold junk (dates like `21/07/2026`) — never pass a
     date through as a serial.
   - `target_count`/`video_available` from the `Video Đã Đăng` column
     (`video_count > 0` → available + count; else None/False).

2. **assignment manifest** (`tiktok-feed.json`): schema_v1, `assignment_id` +
   `resources: ["machine:1", ...]`. Only machines in BOTH assignment and projection are used;
   assignment machines missing accounts print a WARNING (máy 75-80 have zero accounts — normal).

3. **journal facts** (`canonical_journal_facts.json`): schema_v1 `{facts: [...]}`; per account
   `{account_id, machine, serial, feed_state, post_state, feed_state_revision, post_state_revision}`
   where the revisions are CONTENT-derived:
   `sha256:...` of `{"account_id": <id>, "state": <state>}` (canonical json).
   The generator re-verifies the content hash — journal `feed_state={"status":"ready"}`,
   `post_state={"status":"due"}` is fine HERE (generator input only).

## State JSON (runtime, DIFFERENT schema from journal)

Written AFTER `generate_config` by reading `feed_state_revisions` / `post_state_revisions`
from the output config, keyed by account_id:

```json
// feed_state.json
{"<account_id>": {
  "account_id": "<id>",
  "last_feed_success_at": null,
  "unresolved_reservation": false,
  "terminal_facts": [],
  "state_revision": "<sha256 from config feed_state_revisions>"
}}

// post_state.json
{"<account_id>": {
  "account_id": "<id>",
  "status": "DUE",
  "video_available": true|false,
  "target_count": <int|null>,
  "state_revision": "<sha256 from config post_state_revisions>"
}}
```

- `state_revision` MUST equal the config's revision byte-for-byte, else picker skips the
  account (`INVALID_FEED_STATE` / `POST_STATE_UNAVAILABLE` → manifest with 0 entries).
- `_feed_decision` on never-success state returns `NEVER_SUCCESS` due → schedulable.

## State/offline root layout (validated by `StatePaths`)

- `offline_root` must be an ANCESTOR of `state_root` (`models.py:414`:
  `off not in resolved.parents` → `INVALID_PATH`). Working pair:
  - `HERMES_CRON_STATE_ROOT = D:/Taadaa/runtime/kibe/cron-state`
  - `HERMES_CRON_OFFLINE_ROOT = D:/Taadaa/runtime/kibe` (parent!)
- Manifests land at `<state_root>/manifests/<day>/<assignment_id>.json` + `ACTIVE.json` pointer.

## env.json (repo runtime/hermes-cron/env.json, created at approval)

Keys (all optional but fail-closed if required key missing): `HERMES_CRON_STATE_ROOT`,
`HERMES_CRON_SOURCE_CONFIG`, `HERMES_CRON_OFFLINE_ROOT`, `HERMES_CRON_OWNER_ID`,
`HERMES_CRON_WORKER_ID`, `HERMES_CRON_FEED_STATE_JSON`, `HERMES_CRON_POST_STATE_JSON`,
`HERMES_CRON_REPORT_JSONL`, `HERMES_CRON_REPO`, `HERMES_CRON_FEED_WORKBOOK`.
**`OWNER_ID` MUST equal `WORKER_ID`** (manifest.py:264) — e.g. both `hermes-cron-kibe`.

Activation permits: `runtime/hermes-cron/permits/tiktok_{picker,runner,watcher}.permit`
(regular non-symlink file; content arbitrary).

## E2E probe sequence (after generating everything)

1. `python scripts/hermes_cron/tiktok_picker.py` (repo cwd; needs `PYTHONPATH` forwarded by
   wrapper — wrapper sets `child["PYTHONPATH"] = str(repo_root())`).
2. Inspect `<state_root>/manifests/<day>/<assignment_id>.json` — `entries` must be > 0.
   If `skipped` all `UNSCHEDULABLE_CAPACITY`/`CAPACITY_EXCEEDED`, today's lane
   (`lane_for_day`: A rows 1-3 even / B rows 4-6 odd) has <3 schedulable accounts per
   machine — see picker-lane gotcha in SKILL.md.
3. Delete `env.json` + any stray `.permit` before running `test_hermes_cron_wrappers.py`.
