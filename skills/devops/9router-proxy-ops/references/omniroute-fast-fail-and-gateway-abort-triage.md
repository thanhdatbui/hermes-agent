# OmniRoute Proxy Fast-Fail & Gateway Agent Abort Triage

## Symptoms
- Multiple Telegram Gateway topics/chats simultaneously receive:
  `⚠️ The model provider failed after retries. I kept raw provider details out of chat; check gateway logs for diagnostics.`
- In-flight agent turns with high token counts / long iteration chains are terminated after 2 failed retries.

## Diagnosis Workflow
1. **Check Gateway & Agent Logs:**
   - Search `gateway.log` and `agent.log` around the incident timestamp for provider errors:
     ```bash
     grep -n -C 5 "model provider failed" /c/Users/Kibe/AppData/Local/hermes/logs/gateway.log
     grep -n -C 5 "API call failed" /c/Users/Kibe/AppData/Local/hermes/logs/agent.log
     ```
2. **Identify Fast-Fail vs Quota Exhaustion:**
   - **Proxy Fast-Fail:** Logs show `[Proxy Fast-Fail] Proxy unreachable: http://<proxy-host>:<port> (HTTP 502/503)` followed by:
     `HTTP 503: Service temporarily unavailable: all targets were skipped by pre-dispatch filters (code: ALL_TARGETS_SKIPPED)`.
   - **Quota Exhaustion:** Logs show HTTP 429 quota exhaustion or `VALIDATION_REQUIRED` (403).
3. **Response & Safety Rule:**
   - For transient proxy unreachable/fast-fail blips, OmniRoute automatically resets cooldowns after the timeout (e.g., 5-10s).
   - **CẤM** auto-disable accounts, mutate model locks, or reset OAuth tokens when the failure is a network/proxy fast-fail.
   - Separate LLM provider outages from background automation batch states (e.g. cron watchdogs running in `no_agent` mode without LLMs).
