# OmniRoute Strategy Tuning: Least-Used, Headroom Pitfall, and Subagent Sticky Budget

## 1. Headroom Strategy Pathology in Large Pools (>15 Accounts)
- **Mechanism**: `orderTargetsByHeadroom` calls `getSaturation()` concurrently (`HEADROOM_SATURATION_FETCH_CONCURRENCY = 5`) for each unique connection to fetch 5h and weekly utilization percentages before ranking.
- **The Pitfall**: For a 20-account pool behind farm mobile proxies, fetching saturation triggers ~40 upstream HTTP calls before dispatching the user prompt. Proxy latency spikes cumulative preflight duration to >30s.
- **Symptom**: Client-side timeout (HTTP 499 / Client Disconnect), request hangs, or Hermes fallback triggers prematurely.
- **Rule**: NEVER use `headroom` on proxy-backed pools with >10 accounts unless a local pre-cached saturation daemon is active.

## 2. Least-Used Strategy with Subagent Sticky Alignment
- **Why `least-used` wins**: Computes ranking in-memory O(1) via `metrics.byTarget[executionKey].requests` without network preflight. Accounts with 0 requests / 100% quota naturally rise to top position.
- **Sticky Round-Robin Limit Alignment**:
  - Subagent tasks (`delegate_task`) run on a hard budget of `<= 15 calls`.
  - Setting `stickyRoundRobinLimit: 15` ensures the subagent's entire lifecycle (read -> patch -> test verify) stays pinned to a single account, achieving 100% Prompt Caching efficiency (Claude / OpenAI / Gemini).
  - Once the subagent finishes or the task boundary changes, `least-used` smoothly shifts the next session/subagent to the next least-utilized account.
- **Fail-Safe De-Pinning**: In `sessionStickiness.ts`, if an account hits `429`, quota exhaustion, or transport unreachability, the sticky binding is automatically cleared (`clearStickyBinding`), failing over instantly without waiting out the 15 turns.

## 3. Account-Tiered Combo Architecture Matrix
| Pool Class | Recommended Strategy | Sticky Limit | Queue Timeout | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Pro Gemini** (`ag-gemini-pool-3`) | `least-used` | `15` | `3000ms` | Maximizes prompt cache, prioritizes fresh accounts, fails over in 3s on proxy drop. |
| **Free Codex & Claude AG** (`codex-terra`, `ag-opus`, `ag-sonnet`) | `least-used` | `15` | `2000ms` | Evens wear across small free quotas while preserving cache across subagent tool rounds. Avoids `cache-optimized` trap (which disables stickiness). |
| **ChatGPT Web** (`chatgpt-web-pool`) | `p2c` | `0` (disabled) | `1000ms` | Randomizes across 27+ sessions based on latency/success rate; prevents Cloudflare/session bans. |
