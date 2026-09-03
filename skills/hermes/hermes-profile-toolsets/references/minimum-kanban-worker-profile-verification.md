# Minimum Kanban worker-profile verification

Condensed reusable recipe from a two-flow Hermes setup. Use when adding native
`kanban.orchestration.roles` bindings without creating another orchestrator or
adding a Hermes fallback chain.

## Minimum configuration shape

- Root config owns only the intended role keys under
  `kanban.orchestration.roles`.
- Each role has a bounded `candidates` list and an explicit toolset pin such as
  `file`, `terminal`, `code_execution`.
- Each worker profile owns its model/provider and CLI allowlist, includes
  `no_mcp`, disables unrelated capabilities, and does **not** disable `kanban`.
- Keep expensive/external CLI auditors outside worker candidates when stock
  Hermes profiles cannot truthfully represent that CLI/OAuth lane. Report this
  separation rather than pretending it is native routing.

## Effective-role proof

For every intended `current_step_key`:

1. Resolve `resolve_workflow_step_policy(task)` from the live root config.
2. Assert exact profile, model, sorted toolsets, and candidate count.
3. Probe nearby generic roles (`planner`, `worker`, etc.) and assert they remain
   unresolved unless deliberately configured. This catches broad routing
   hijacks.

## Effective worker-schema proof

A dispatcher with role-level toolsets passes those toolsets directly to the
child; profile `platform_toolsets.cli` is only the fallback path. Therefore:

1. Set `HERMES_KANBAN_TASK` to a harmless sentinel.
2. Use the resolved role policy toolsets as `enabled_toolsets`.
3. Use the assigned profile's `agent.disabled_toolsets` as the subtraction set.
4. Call `get_tool_definitions(..., quiet_mode=True,
   skip_tool_search_assembly=True)`.
5. Require implementation tools plus `kanban_complete`, `kanban_block`, and
   `kanban_heartbeat`.
6. Require `delegate_task`, `memory`, and board-routing tools such as
   `kanban_list` to be absent.

This catches the common bug where a worker profile disables `kanban`: runtime
adds it for task lifecycle, then disabled subtraction removes it again.

## Configuration and repository gates

- Use official profile/config APIs and atomic writes.
- Deep-diff parsed YAML before/after and allow only intended paths.
- Assert no `fallback` fields were introduced when fallback is out of scope.
- Confirm provider entries use `key_env` references and no inline keys.
- Run `hermes config check` on root and every profile.
- Preserve a dirty repo with before/after HEAD, tracked-diff hash, and
  name-status hash. Porcelain is secondary on noisy shared worktrees.

## Two-stage live smoke

For each profile, resolve the live runtime provider from that profile and make a
harmless exact-token request using its configured model. Record configured
model/provider, resolved runtime, HTTP status, response model, exact-token
match, latency, and whether usage metadata exists. Never print the secret.

If HTTP 200 returns empty visible content with a very small output cap, retry
once with a realistic cap (for example 256). Reasoning models may consume a tiny
budget before emitting text. Treat persistent empty content, non-2xx, timeout,
or malformed JSON as transport/runtime failure—not an audit verdict.

## Independent audit fallback labeling

Attempt the requested premium CLI auditor read-only. If authentication/quota is
unavailable, label that as transport/auth failure and use the approved independent
review fallback. Do not claim premium-auditor availability, and do not map 401,
429, timeout, or empty output to APPROVED/REJECT. A final gate requires a
parseable first-line verdict from the fallback reviewer plus fresh config,
schema, tests, smoke, and repo-preservation evidence.
