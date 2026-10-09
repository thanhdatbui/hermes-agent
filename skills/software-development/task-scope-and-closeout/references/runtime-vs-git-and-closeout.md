# Runtime-vs-Git and Closeout Reference

## Decision table

| Observation | Session class | Required evidence | Git closeout |
|---|---|---|---|
| Claude Desktop model/advisor selector changed and read back in app | `RUNTIME_CONFIG` | Fresh app screenshot/OCR or authoritative UI readback | Not required by default |
| Hermes skill/rule markdown changed in canonical repo | `DOC_POLICY` | Exact file diff, scope, optional focused policy check | Only if publication/commit is requested |
| Production source/test changed for a requested feature/fix | `CODE_CANDIDATE` | Bound repo, exact files, focused test, reviewer gate | Required when user requests done/closeout |
| Only unrelated repositories are dirty | `NO_CANDIDATE` | No current-session candidate exists | Do not guess or sweep |

## Bounded closeout receipt

```text
session_class: RUNTIME_CONFIG | DOC_POLICY | CODE_CANDIDATE | NO_CANDIDATE
repo: <canonical repo or NONE>
base: <actual base or NONE>
files: [<exact paths>]
gate_status: NOT_APPLICABLE | PASS | REJECTED | TRANSIENT
commit_required: yes | no
evidence_paths: [<fresh artifact paths>]
```

## Failure pattern to avoid

A user may close a session after changing only an app setting and a policy document. Do not enumerate every dirty Taadaa repository, choose a guessed `HEAD~1`, or run a reviewer against an arbitrary repo. That converts a completed runtime/docs task into a false blocker and may expose unrelated work. Bind current-session ownership first; if it cannot be bound, report `NOT_APPLICABLE — no code candidate`.

## Media evidence reminder

A path being present, a screenshot being recent, or a worker claiming success is not enough. Before emitting `MEDIA:`, open/read the exact artifact, confirm it shows the target app and result, and reject wrong-foreground, stale, blank, or unrelated captures.
