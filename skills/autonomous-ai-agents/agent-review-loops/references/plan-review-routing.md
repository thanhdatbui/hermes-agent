# Plan-review routing and downgrade checks

Use this reference for any plan/code-review gate in Taadaa.

## Route selection

- Ordinary or single-repository review: call `plan-review` through the configured 9Router HTTP endpoint.
- Core, lock, recovery, state-machine, or similarly sensitive review: call `plan-review-hard` through 9Router.
- A delegated worker is an implementation role, not an audit role. Never treat a worker or the session implementation model as the plan-review gate.

## Required request contract

Send the named model identifier in the request body and use the configured 9Router transport. Require:

```json
{"stream": false, "tools": [], "tool_choice": "none", "reasoning_effort": "high"}
```

Pass the exact candidate bytes or staged tree hash, not a stale worktree summary. Keep the API key in the Authorization header and never print it.

## Acceptance checks

Before accepting a verdict, record:

1. requested model identifier (`plan-review` or `plan-review-hard`);
2. transport endpoint and HTTP result;
3. exact staged tree/file hashes reviewed;
4. first non-empty verdict line and findings;
5. whether the router actually served the named review route.

A parseable `APPROVED` from the wrong model is not approval. If 9Router maps the named route to an unsupported implementation model, returns a provider/model compatibility error, or otherwise silently downgrades, classify it as `BLOCKED_AT_REVIEW` (or use the documented audit fallback) rather than calling the result a plan-review verdict.

## Closeout scope rule

When the user says `chốt phiên`, review only the original deliverable's frozen allowlist. Do not send stale remediation candidates, old rejected branches, or unrelated dirty files to the reviewer. If the original deliverable is already committed and remote-verified, stop without another review loop.

## Compact report

Report in Vietnamese: `Route → verdict → candidate hash/tree → test result → blocker/remote`. Do not paste the full English review body unless the user asks for it.
