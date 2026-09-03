# 9Router Plan-Review Routing — Session Evidence

**Session:** 2026-09-03 (Farm Alert Machine 10 tiktok-follow fix)

**Route Used:** `plan-review` via 9Router (port 20128)

**Model Identifier:** `plan-review` (served by 9Router, not session model)

**Transport:** HTTP POST to `http://127.0.0.1:20128/v1/chat/completions` with `Authorization: Bearer <9router_api_key>`

**Payload:** `model: "plan-review"`, `stream: false`, `tools: []`, `tool_choice: "none"`, `temperature: 0.1`, diff-scoped payload (git diff of follow_runner/flows/ and follow_runner/tests/ only)

**Response:** Parseable format:
```
VERDICT: APPROVED

FINDINGS:
[Detailed findings...]
```

**Verification Checks Performed:**
1. Requested model `plan-review` → 9Router returned parseable verdict → ✓
2. 9Router served the requested route (no silent downgrade to Luna/Flash) → ✓
3. Verdict bound to exact staged candidate bytes (git diff) → ✓

**Anti-Pattern Avoided:** Did NOT use `cx/gpt-5.6-luna` or `ag/gemini-3.7-flash-high` (session/implementation models) as auditor. Worker/subagent audit is diagnostic only, never satisfies plan-review gate.

**Fallback Route:** `plan-review-hard` (available on 9Router, not needed this session).

**Key Learning:** For TikTok follow runner fixes (core, lock, recovery, UI navigation), `plan-review` via 9Router is the correct route. It returns concise parseable verdicts. Always verify the route identity by checking the response contains `VERDICT: APPROVED|REJECTED|BLOCKED` format.

**Next Session:** When user asks for plan review on similar farm automation work, route to `plan-review` via 9Router first. If auth/transport fails, record exact error and try `plan-review-hard`. Never silently use session model.