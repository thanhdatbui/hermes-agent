---
name: mechanical-guidance-gate-design
description: "Use when designing mechanical gates to prevent agent loops."
---
# Mechanical Guidance Gate Design (Anti-Whining & Action Mandate)

## 1. When to Use
Use when creating, modifying, or reviewing mechanical enforcement gates (hooks, gates, runtime fences). Enforces actionable unblocking paths (Auto-Rewire / Active Pivot).
- Reference: `references/pre-tool-auto-rewrite-and-24h-heartbeat-architecture.md`
- Reference: `references/auto-rewire-and-auto-clamp-architecture.md`
- Reference: `references/user-sudo-override-and-investigate-read-only-deadlock-triage.md`
- Reference: `references/dispatch-worker-timeout-and-deadlock-prevention-20261025.md`
- Reference: `references/gate-compliance-audit-desync-and-test-pollution-invariants.md`
- Reference: `references/active-pivot-auto-rewire-architecture.md`
- Reference: `references/multi-repo-regression-gate-hierarchy.md`
- Reference: `references/o1-process-verification-and-closeout-operational-decoupling.md`
- Reference: `references/canary-gate-auto-wiring-vs-memory-enforcement-20261028.md`
- Reference: `references/prompt-contract-desync-and-scanner-false-positive-triage.md`
- Reference: `references/observability-watchdog-vs-bureaucratic-blocking-gate-pruning.md` (Observability watchdogs retention vs bureaucratic blocking gate & local hash chain pruning).
- Reference: `references/auto-wiring-and-guidance-boundary-matrix-20261026.md` (Auto-Wiring vs Fail-Fast decision matrix for investigate budget & GuardGate guidance).
- Reference: `references/idle-window-evaluation-bias-and-closeout-boundary-discipline.md` (Idle-window evaluation bias & zero-block action mandate hierarchy).
- Reference: `references/cowboy-coordinator-boundary-and-idle-evaluation-invariants.md` (Cowboy Coordinator Gate 3/6 boundary violations).
- Reference: `references/user-sudo-override-and-gate-abc-discipline.md` (User Sudo Override protocol, Pipeline A-B-C stages, & anti-idle-window invariants).
- Reference: `references/dispatch-receipt-enforcer-and-claim-boundary.md` (Dispatch Receipt Enforcer: post-turn mechanical truth labeling against LLM completion bias & false dispatch claims).

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
