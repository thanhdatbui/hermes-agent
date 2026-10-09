# Model identity and A/B benchmarking

## Why this exists
A requested model name is not proof of the backend model that ran. Proxies can alias, silently fallback, or return a different provider model. Direct Claude CLI and OmniRoute/9Router calls are separate execution paths and must not be scored as if they were identical.

## Verification protocol
1. Run a low-cost ping against the exact route.
2. Request `stream=false` where supported and parse the JSON response.
3. Record the requested model, response `model` field, provider/endpoint, effort/reasoning setting, timeout, max output, latency, and any fallback/error.
4. If the endpoint times out, returns SSE instead of JSON, or returns 401/402, stop and diagnose routing/credentials; do not score the model.
5. For CLI, verify the binary with `claude --version`, then probe with `claude -p "state your exact model ID only" --model <alias> --max-turns 3`.

## Fair comparison rules
- Use identical prompts and output caps, but keep the execution path explicit.
- Run at least three independent tasks and repeat when practical.
- Separate correctness, completeness, safety/edge-case coverage, and latency; do not infer quality from speed alone.
- Reject benchmark cases that are underconstrained or internally inconsistent. A model finding that a prompt is invalid is not a failure.
- Save raw outputs and score from the artifacts, not from model self-reports.

## Incident lessons
- A model catalog, binary strings, UI dropdown, or proxy `/v1/models` response proves availability/catalog visibility only; it does not prove direct CLI access or successful billing.
- When a proxy request is routed to a different backend than requested, report the actual response model and treat the case as routing evidence, not a clean model benchmark.
