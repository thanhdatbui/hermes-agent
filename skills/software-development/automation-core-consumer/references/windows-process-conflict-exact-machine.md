# Exact Windows process-conflict detection by machine

## Problem class

A consumer may supplement shared device locks with a read-only scan for older runners that do not participate in the lock store. A naive aggregate check such as:

```python
f"--machine {machine}" in wmic_stdout and "tiktok_workflow" in wmic_stdout
```

is unsafe:

- machine `1` prefix-matches `--machine 11` and `--machine 12`;
- the workflow marker can occur in one process record while the machine argument occurs in another;
- an ordinary `SKIPPED_LOCKED` result then falsely looks like a real target conflict and prevents all device work.

## Correct invariant

Classify busy only when one process command line contains BOTH:

1. the expected runner marker (for example `tiktok_workflow`); and
2. an exact machine argument for the target:
   - `--machine 1`
   - `--machine=1`

The number must have an argument boundary after it. Machine `1` must not match `10`, `11`, `12`, or `100`.

Parse records/lines independently. Do not search the complete WMIC output as one string.

A suitable argument expression is conceptually:

```regex
(?<!\S)--machine(?:=|\s+)1(?=\s|$)
```

Escape/interpolate the numeric target safely. If the WMIC format can wrap long command lines, use a structured process source (for example WMI/psutil) rather than weakening the boundary rule.

## Minimum TDD matrix

Before production code, add a regression and observe RED:

| Command-line fixture | Query | Expected |
|---|---:|---:|
| `... tiktok_workflow ... --machine 11 ...` | 1 | false |
| `... tiktok_workflow ... --machine 12 ...` | 1 | false |
| `... tiktok_workflow ... --machine 1 ...` | 1 | true |
| `... tiktok_workflow ... --machine=1 ...` | 1 | true |
| marker on record A, `--machine 1` on unrelated record B | 1 | false |

Keep the existing failure policy explicit: if this compatibility scan cannot run, shared-core lock state remains authoritative; do not manufacture a busy result from unparseable aggregate text.

## Live-run diagnosis

When production returns `SKIPPED_LOCKED` unexpectedly:

1. Parse running commands and count the exact target machine, not a substring.
2. Inspect both canonical aliases: `machine_<N>.lock.json` and `serial_<serial>.lock.json`.
3. Confirm whether startup artifacts were created.
4. If exact process count, both aliases, and artifact count are all zero, classify the run as pre-start/no-device-action and fix the detector before retrying.
5. Re-run the canonical production entrypoint only after focused/full offline gates and a fresh exact preflight.

Never delete or force-release a foreign/retained lock to work around a detector bug.
