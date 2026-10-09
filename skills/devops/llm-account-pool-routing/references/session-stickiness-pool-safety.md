# Session Stickiness vs Round-Robin & Pool Resilience (2026-09-11)

Xác minh từ code `C:\Users\Kibe\OmniRoute\open-sse\services\` + Claude CLI (6 turns).

## 1. Round-robin per-request = die acc hàng loạt
- Cùng 1 conversation (cùng Session ID, context dài dần) mà mỗi turn nhảy 1 acc khác nhau (khác token, khác proxy IP) = footprint "bot farm" cho Google Fraud Detection → chain ban.
- Mất prompt cache: mỗi acc nạp lại 100% context → tốn quota 5-10x.

## 2. Session stickiness = bảo vệ (không phải reorder nguy hiểm)
- File `open-sse/services/combo/sessionStickiness.ts`: BẬT mặc định (`disableSessionStickiness=false`).
- Key = SHA-256 tin nhắn user đầu tiên (16 hex), namespace = combo name. TTL 15 phút, max 500 entries LRU.
- 3 gate trước khi reuse pin: (a) headroom > 0.15, (b) không terminal (`credits_exhausted/banned/expired/rateLimitedUntil>now`), (c) không `isAccountQuotaExhausted`.
- Fail → `clearStickyBinding` → rebind ở request tiếp theo. `recordStickyBinding` sau mỗi success.
- Kết luận: 1 task/worker = 1 acc xuyên suốt đến khi xong hoặc cạn quota mới đổi. Đây là hành vi user thật.

## 3. quota-share KHÔNG dùng được cho combo user
- `quota-share` chỉ cho internal auto-minted `qtSd/` combos (`quotaShareStrategy.ts` header). Combo user dùng `reset-aware` cho Antigravity pool (weight 35% 5h + 65% 7d), `reset-window`, `p2c`, `least-used`, `cache-optimized`.
- `fallbackOnlyOnQuotaExhaustion` chỉ có tác dụng với strategy `priority`, per-target.

## 4. Resilience defaults (bảng key_value `resilienceSettings`)
- `connectionCooldown.oauth: base 5s x2^level, maxBackoffSteps 8` → 5s→10s→20s→… cách ly acc lỗi trong RAM O(1), không HTTP probe.
- `providerCooldown: enabled, 30s–1800s`. `comboCooldownWait: enabled, maxWait 90s, maxAttempts 5, budget 300s`.
- `waitForCooldown: enabled, maxRetries 3, maxRetryWait 30s`.
- Acc lỗi bị phạt cooldown tăng dần → request sau tự né sang sibling khỏe, không chờ xoay lâu.

## 5. Checklist pool Gemini an toàn
- `max_concurrent` per connection = 1–2 (DB `provider_connections`; fail-open null = unlimited — phải chuẩn hoá, đã thấy lẫn lộn None/3/8).
- Giữ `disableSessionStickiness=false`, `disablePromptCacheAffinity=false` cho worker pool (ngược với safety-first priority pool thuần — ở đó affinity có thể reorder và cần opt-out per-combo sau regression test).
- Nâng cao: `promptCacheAffinity` (cache-optimized rendezvous), `context_cache_protection`, `failureTracker` (3 fail liên tiếp tự xả pin), `zeroLatencyOptimizations`, `reasoningTokenBuffer` (default true), `universalHandoff`.
- Tách Tier: Tier1 Gemini pool tự xoay nội bộ + gating chỉ failover Claude/Free khi cạn sạch quota (tránh đốt Claude vì nghẽn tạm thời). Nếu gắn `fallbackOnlyOnQuotaExhaustion=true` lên Tier1 ref trong `omni-worker` phải đọc `combo.ts` quanh `stopProtectedPriorityTarget` trước — semantics trả 503 dừng luôn thì KHÔNG gắn.
