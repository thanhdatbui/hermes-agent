# OmniRoute Proxy Hotspotting & Combo Timeout Exhaustion Runbook

## 1. Proxy Hotspotting (Account Concentration on Single Egress Port)
In `~/.omniroute/storage.sqlite` (`proxy_assignments` join `proxy_registry`), multiple accounts across multiple providers (e.g. Antigravity, Codex, ChatGPT Web) can unintentionally be assigned to the same proxy port (e.g. `test.taadaa.click:5113` holding 10 accounts).

### Symptom
When a 4G dongle/modem drops or redials:
1. `[Proxy Fast-Fail] Proxy unreachable: http://test.taadaa.click:<port>` triggers for accounts using that port.
2. If the active account in the first tier of a combo uses that port, the request stalls until `targetTimeoutMs` expires (e.g., 30,000ms for Antigravity).

## 2. Cascading Timeout Exhaustion across Combo Tiers
When users ask: *"Why didn't the system automatically rotate to other accounts/proxies in the pool?"*
The system DOES attempt fallback, but fails due to aggregate timeout exhaustion:
1. **Tier 1 (Antigravity)**: Uses 30s waiting on the unreachable proxy.
2. **Tier 2 (Codex / Terra)**: Skipped immediately or in rate-limit cooldown.
3. **Tier 3 (ChatGPT Web / Sol High)**: Waits 15s before timing out (504 Gateway Timeout).
4. **Client Gateway Abort**: Hermes Gateway retry budget is exhausted before OmniRoute's combo loop can traverse to candidate accounts assigned to healthy proxy ports (e.g. `10001-10007` or `5101-5112`).

## 3. Demystifying "all 1 active accounts cooling down" in Codex Logs
In OmniRoute (`src/sse/services/auth.ts`), when a combo defines a model with a pinned `connectionId` (`forcedConnectionId`), the candidate array `connections` is pre-filtered:
```typescript
if (forcedConnectionId) {
  connections = connections.filter((conn) => conn.id === forcedConnectionId);
}
```
When that specific account enters a cooldown/lockout, the log output prints:
`codex | all ${connections.length} active accounts cooling down for model ${requestedModel}`
Even though the database contains 16+ active Codex accounts, `connections.length` equals `1` because of the explicit connection pinning in the combo definition.
