# Hermes delegation timeout and aggregate-load tuning

Use this when Telegram/Gateway reports that an agent is inactive while the current tool is `delegate_task`, or when several sessions may be spawning workers at once.

## Read the diagnostic correctly

A message such as:

```text
Agent inactive for 30 min — no tool calls or API responses.
The agent appears stuck on tool delegate_task
(1804s since last activity, iteration 3/100).
```

contains two independent limits:

- `iteration 3/100` is the agent/delegation API-tool loop count. Because 3 is far below 100, `max_iterations` did **not** fire.
- `1804s since last activity` crossed the Gateway inactivity timeout. The Gateway activity tracker is refreshed by tool calls, API calls, and stream deltas. A parent waiting without any of those can time out even though its configured iteration ceiling is much larger.

Hermes defaults observed in the gateway source are normally:

- `agent.gateway_timeout: 1800` seconds (30 minutes)
- `agent.gateway_timeout_warning: 900` seconds (15 minutes)
- `0` means no timeout

After a timeout or interrupted `delegate_task`, treat child state as **unknown**, not completed and not safely absent. Reconcile the exact scope—worker/session/process/lease/tool events and working-tree changes—before dispatching a replacement.

## Distinguish three sources of pressure

1. `delegation.max_iterations`: work budget for one child; a ceiling, not a concurrency setting.
2. `delegation.max_concurrent_children`: per-parent child fan-out. The default may allow several children for each active parent.
3. `max_concurrent_sessions`: Gateway-wide active session cap. If unset/unbounded, many Telegram topics or desktop sessions can each spawn their own allowed children.

Therefore, “I spawned too many agents” can be an **indirect load cause**—Cockpit/provider/transport saturation—but it is not proven merely by an inactivity message. Confirm aggregate sessions, live children/processes, recent delegation artifacts, and provider errors before assigning causality.

## Safe tuning pattern

For long coding workers on a shared desktop, start conservatively:

```yaml
agent:
  gateway_timeout: 7200          # example: 2 h inactivity
  gateway_timeout_warning: 3600  # warn halfway

delegation:
  max_iterations: 100
  max_concurrent_children: 1
max_concurrent_sessions: 3
```

These are tuning examples, not universal constants. Choose the session cap from machine/provider capacity. Prefer a finite timeout (typically 3600–7200 seconds) over `0`; unlimited mode can hide a genuinely hung tool forever.

Apply settings through the CLI, never by hand-editing YAML:

```bash
hermes config set agent.gateway_timeout 7200
hermes config set agent.gateway_timeout_warning 3600
hermes config set delegation.max_concurrent_children 1
hermes config set max_concurrent_sessions 3
hermes config check
```

Keep `delegation.max_iterations` separate from timeout tuning. Raising iterations does not keep a silent Gateway turn alive.

## Restart and verification gate

Gateway config changes require a Gateway restart. Before restarting:

1. Check for in-flight Hermes sessions/children and exact-scope jobs that a restart could interrupt or orphan.
2. If work is active, save the config but defer restart; report that the new values are not active yet.
3. When safe, restart the Gateway and verify its status.
4. Read back only the non-secret keys and run one bounded delegation smoke task.

A backup of `config.yaml` is useful before multi-key tuning, but all actual edits should still go through `hermes config set`.

## Common misdiagnoses

- `iteration 3/100` does not mean Hermes stopped at three calls; it means the inactivity timer fired during the third iteration.
- A `Result unavailable` receipt is not proof that the worker completed or even that it never started.
- Recent worker summaries show activity history, not necessarily concurrent overload.
- Do not immediately spawn a replacement into the same files after a timeout; reconcile first.
