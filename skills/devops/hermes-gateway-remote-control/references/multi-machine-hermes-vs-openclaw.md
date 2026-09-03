# Multi-machine control: Hermes vs OpenClaw

## Decision rule

- **OpenClaw** has a first-class `Gateway + Node` topology: one Gateway owns sessions, channels, auth, and state; each remote machine runs a paired Node for local execution.
- **Hermes** has a messaging Gateway plus a configurable terminal backend. Its SSH backend runs the agent's shell commands on a remote host, but it is **not** a native multi-machine Node-pairing layer.

Therefore, “one agent controls two machines” means different things:

| Requirement | Hermes | OpenClaw |
|---|---|---|
| One bot/session, run commands on one remote host | Gateway + `terminal.backend: ssh` | Gateway + node also works |
| One bot/session, choose between two remote hosts | Add an explicit host router (MCP/tools/scripts), or run isolated Hermes instances | Pair two Nodes; route tool calls by node |
| Two independent agents | Two Hermes profiles/gateways, or two machines | Two Gateways/agents |
| Shared conversation/state | Keep one Gateway as the state owner | Keep one Gateway as the state owner |

## Hermes recommended topology

```text
Telegram
   |
Hermes Gateway (one host, always online)
   |-- SSH/tool router --> machine A
   `-- SSH/tool router --> machine B
```

Do not describe `terminal.backend: ssh` alone as “two-machine support”: the standard backend has one configured SSH host (`TERMINAL_SSH_HOST`, user, port, key). To select A or B per call, expose two named tools/scripts or an MCP server, for example `run_on_machine_a` and `run_on_machine_b`, each with a fixed allowlisted SSH target. Keep the model-facing names explicit so it cannot accidentally run a command on the wrong host.

If only one remote host is needed, the standard configuration is:

```yaml
terminal:
  backend: ssh
  persistent_shell: true
```

with secrets/connection values supplied through the environment (`TERMINAL_SSH_HOST`, `TERMINAL_SSH_USER`, optional port/key). Use `hermes config set` for non-secret settings; never put keys/passwords in `config.yaml`.

## Separate Hermes instances

Use separate profiles/gateways when each machine must have its own working directory, credentials, approvals, or Telegram identity. Do not run two polling gateways against the same Telegram bot token: use one central router or separate bot tokens. Do not live-share/copy the same `state.db`, `sessions/`, `auth.json`, or `.hermes` state between active machines; concurrent writes can corrupt or race session state.

A practical split is:

```text
Bot A -> Hermes profile/gateway A -> machine A
Bot B -> Hermes profile/gateway B -> machine B
```

This gives isolation, not one shared conversation. If a single Telegram bot and shared context are required, keep one Gateway and add the two-host router instead.

## Session and state invariants

- One Gateway owns the Telegram channel and session history.
- `/new` resets a conversation; it does not create a second execution host.
- SSH terminal execution changes **where shell commands run**, not where Hermes session state lives.
- A remote SSH sandbox/session may sync Hermes state back on teardown for supported backends, but that is not a live multi-writer state-sharing mechanism.
- Two agents writing the same repo concurrently need separate worktrees/branches or a serialized queue; do not rely on shared `.hermes` state to coordinate them.

## Security and verification

- Prefer LAN/Tailscale/VPN or SSH; do not expose the Gateway or unrestricted SSH unnecessarily.
- Give each host a distinct name and fixed target; verify `hostname`/machine identity before allowing destructive commands.
- Verify actual execution with a harmless probe such as `hostname && pwd`, and record the returned host in the result.
- For OpenClaw, pair/approve each Node and verify node status; Nodes are peripherals and do not run the Gateway service.

## Sources

- Hermes configuration / SSH backend: https://hermes-agent.nousresearch.com/docs/user-guide/configuration
- Hermes messaging gateway: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/
- OpenClaw remote access: https://docs.openclaw.ai/gateway/remote
- OpenClaw nodes: https://docs.openclaw.ai/nodes
