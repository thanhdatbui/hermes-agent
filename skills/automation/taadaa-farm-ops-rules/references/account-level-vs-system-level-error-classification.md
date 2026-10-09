# Account-Level vs System-Level Error Classification for Farm Alerts

## Problem (2026-09-08)
User presented a Zalo screenshot showing 80+ machines with Google/Gmail login error "Please try again or log in with a different method". Many machines stuck on the same error. User asked: "cái này có gửi farm alert k?"

This error was **NOT** sent as a farm alert because it's account-level, not system-level. But the existing rules (Section 14: P0 Auth/Login Alert) don't explicitly distinguish these two classes — only "session loss / account kicked" triggers P0. Rate-limit blocks are a separate category that should NOT trigger individual machine alerts.

## Classification Matrix

| Class | Examples | Alert? | Action |
|-------|----------|--------|--------|
| **System / Script Failure** | ATX crash, script exit non-zero, device offline, USB disconnect, script hang | YES (P0 or batch aggregate) | Fix script/device |
| **Session Loss / Account Kicked** | Login screen detected mid-session, "Đăng nhập vào tài khoản hiện có", checkpoint | YES (P0 — immediate, bypass batch threshold) | Rescue account ASAP |
| **Account-Level Rate-Limit / Block** | "Please try again or log in with a different method" (different_method), rate_limited, captcha, too many attempts | **NO individual alert** | Batch aggregate; troubleshoot at workbook level (check pass, proxy, IP) |
| **Account-Level Auth Error** | Wrong password, "Tài khoản không tồn tại", email not found | **NO individual alert** | Update workbook; not a system failure |
| **Transient / Environmental** | Network blip, proxy lag, animation frame drop, temporary UI lag | **NO** (Silent Skip) | Self-heals in next run |

## Key Rule: "Different Method" Error (`error_different_method` / `rate_limited`)

**Code location:** `social_reg_v1.py:1789` (`detect_after_continue`) and `social_reg_v1.py:4545` (`_classify_post_auth`).

**What it is:** TikTok blocks the email/login attempt due to rate-limiting or suspicious activity detection. The email itself may be valid, but TikTok refuses to proceed.

**Why it does NOT warrant a farm alert:**
1. It's triggered by the **account's history** (wrong passes, rapid attempts, IP changes), not by script/device failure
2. When many machines show it simultaneously, the root cause is typically **shared proxy/VPN IP being flagged** or **batch login pattern detected by TikTok**
3. Fixing requires account-level investigation (check workbook passwords, verify proxy mapping, test login manually), not code/device intervention

**What TO do instead:**
1. Record in batch summary as `error_different_method` / `rate_limited`
2. Aggregate: if >=10-15% of batch hits this → flag as **fleet-wide pattern** but route to **account hygiene** workflow, not farm alert
3. Investigate root cause: proxy IP reputation, account-specific rate-limit, workbook password accuracy
4. If the same email rate-limits across multiple runs in a day → mark account for cooldown (don't re-run)

## Decision Flowchart for Alert Decision

```
Error detected on machine M<N>:
  │
  ├─ Is it a script/device/system failure? (ATX crash, exit code != 0, device offline)
  │   YES → FARM ALERT (system class)
  │
  ├─ Is the account being kicked / session lost mid-operation?
  │   YES → P0 FARM ALERT (bypass batch threshold, immediate)
  │
  ├─ Is it "different method" / rate_limited / captcha / too many attempts?
  │   YES → NO individual alert. Record in batch summary. If fleet-wide (>=10-15%),
  │         escalate to ACCOUNT HYGIENE workflow (not farm alert)
  │
  ├─ Is it wrong password / account not found?
  │   YES → NO individual alert. Update workbook. Check for stale credentials.
  │
  └─ Is it transient (network, proxy, animation lag)?
      YES → NO alert (Silent Skip, auto-release device lock)
```

## Anti-Pattern: Sending Farm Alert for Account-Level Errors
- **Don't** send a P0 alert when "different method" appears on N machines — it's not an emergency
- **Don't** treat every login-adjacent error as "session loss" — session loss means the account WAS logged in and got kicked, not that a fresh login attempt was blocked
- **Don't** keep re-running the same account on the same machine when rate-limited — it makes the block worse
