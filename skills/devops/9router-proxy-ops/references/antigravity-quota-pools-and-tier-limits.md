# Antigravity Quota Architecture: Pool Separation & Tier Limits

Authoritative operational reference for how Google Antigravity (Gemini Code Assist) allocates, tracks, and isolates quotas between Gemini and Claude models across Starter (Free) and Pro accounts, as handled by OmniRoute (`:20129`) and 9Router (`:20128`).

---

## 1. Upstream Quota Architecture & Dual Windows

Google Antigravity enforces quota via two distinct RPCs:
1. **Rolling 5-Hour Window (`v1internal:retrieveUserQuota`):**
   - Evaluates short-term burst and throughput.
   - Surfaced per-model but grouped internally by family.
2. **Weekly Window (`v1internal:retrieveUserQuotaSummary`):**
   - Evaluates multi-day aggregate quota across 7-day rolling periods (168 hours).
   - Groups models into high-level display buckets: `"Gemini Models"` (`gemini_weekly`) and `"Claude and GPT models"` (`claude_gpt_weekly`).

---

## 2. Model Family Pool Isolation

OmniRoute categorizes Antigravity models into two strictly isolated families (`open-sse/services/antigravityQuotaFamily.ts`):
* **`family:gemini`**: `gemini-3.7-flash-tiered`, `gemini-pro-agent`, `gemini-3.1-pro-*`, `gemini-3.x-flash-*`.
* **`family:claude`**: `claude-opus-4-6-thinking`, `claude-sonnet-4-6`, and `gpt-oss-*`.

### Critical Invariants:
1. **Zero Cross-Contamination:** Gemini and Claude pools are **100% independent**. Exhausting 0% of the Gemini pool does not impact Claude quota, and exhausting Claude does not block Gemini.
2. **Claude Shared Single Pool:** All Claude models (Sonnet, Opus, Opus Thinking) share the **EXACT SAME quota bucket**.
   - In 18,490 simultaneous SQLite snapshots, `claude-sonnet-4-6` and `claude-opus-4-6-thinking` match 100% in `remaining_percentage` and `next_reset_at`.
   - Consuming Sonnet reduces available Opus quota and vice versa.
   - When a 429 / QuotaExceeded occurs on any Claude model, OmniRoute applies cooldown to the entire `family:claude` on that account.
   - Calling **Opus Thinking** consumes tokens and quota roughly twice as fast as Sonnet.

---

## 3. Quota Capacities & Capacity Ratios (Starter vs Pro)

Based on empirical production log audits (`storage.sqlite`, `call_logs`, `quota_snapshots`):

| Metric / Dimension | Account Starter (Free) | Account Google AI Pro | Pro vs Starter Factor |
| :--- | :--- | :--- | :--- |
| **Gemini Pool Capacity** | ~500 – 800 reqs/week | ~10,000 – 15,000+ reqs/week (~1.5B tokens) | **~15× – 20×** |
| **Claude Pool Capacity** | ~50 – 80 reqs/week | ~800 – 1,000 reqs/week | **~10× – 15×** |
| **Gemini : Claude Ratio** | **~8× – 10×** | **~15× – 20×** | — |
| **Burst Resilience (Claude)** | Cạn sau ~30–40 reqs dồn dập | Chịu được tải vừa phải, nhưng cạn nếu cày batch | — |
| **Operational Role** | Phao cứu sinh / Emergency fallback | Workhorse cho Gemini; Claude có kiểm soát | — |

---

## 4. Operational Best Practices for Router Combos

1. **Do not use Claude on Starter accounts for automated pipelines:** With a cap of ~50–80 requests, a single background agent run or review loop can exhaust the Claude bucket for the entire week.
2. **Opus Reservation:** Reserve Claude Opus Thinking for high-complexity architectural reviews or critical gates. Route regular coding turns to Claude Sonnet or Gemini 3.7 Flash High.
3. **Multi-Account Spillover for Claude:** For heavy Claude usage, configure OmniRoute combo targets to cycle across multiple Pro accounts on `claude_gpt_weekly` exhaustion rather than failing over to Starter.

---

## 5. Account Onboarding Requirement & The "Restricted / Business" Trap

### The Symptom:
Accounts added via raw browser OAuth into 9Router/OmniRoute show `testStatus: active` or successful token acquisition, but in `provider_specific_data`:
* `subscriptionTier: "Antigravity (Restricted)"`
* `tier: "standard-tier"` (often mapped to `plan: "Business"` in UI)
* Requests fail with delayed `429 RESOURCE_EXHAUSTED`, `403 PERMISSION_DENIED`, or high-latency timeouts triggering `Semaphore Timeout 30s` in combos.

### Root Cause:
Google Antigravity (Gemini Code Assist) is not a public un-gated API. It requires an explicit user onboarding handshake:
1. **Onboarding Handshake:** Acceptance of Code Assist Terms of Service (ToS) and automatic provisioning of a developer workspace project (e.g. `aicode-consumers` or Cloud Companion Project).
2. **Web OAuth Limitations:** Web OAuth consent only grants token scopes (`cloud-platform`, etc.). When OmniRoute calls `/v1internal:loadCodeAssist`, Google returns no project. When calling `onboardUser` for personal Google accounts (`standard-tier`), Google does NOT auto-create a project (expects BYOP — Bring Your Own Project) and returns `ineligibleTiers`.
3. **The "Restricted" Tag:** OmniRoute's `codeAssistSubscription.ts` flags accounts with `ineligibleTiers` as `(Restricted)`.

### Operational Rule ("Log in Anti first"):
* **Never add raw, un-onboarded Google accounts directly to 9Router/OmniRoute via web OAuth alone.**
* **Mandatory Step:** Log into the official Antigravity client / IDE (or Gemini Code Assist extension) once with the Google account. This triggers Google's native onboarding flow, signs ToS, and provisions the `Antigravity Starter Quota` cloud project.
* Once onboarded, importing the token into 9Router / OmniRoute will cleanly detect `subscriptionTier: "Antigravity Starter Quota"` with active quota for Gemini and Claude.
* Keep any lingering `Restricted` accounts set to `isActive = 0` (isolated from production combos) until properly onboarded in the client.
