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
- Reference: `references/dispatch-receipt-enforcer-r3-architecture.md` (Receipt Enforcer R3: exact tool_call_id matching, allowlist status, NFKC normalization, & non-blocking truth labeling).
- Reference: `references/gate-b-planner-and-dispatch-contract-o1.md` (Gate B Planner Architecture: Gemini Web primary with Claude CLI fallback & Contract O(1) for Workers).
- Reference: `references/gate-b-planner-and-anti-overengineering-gate-c.md` (Gate B Planner & Anti-Overengineering Gate C: 90s timeout, no-sha256 CRLF-normalized anchor, Qoder T0 primary, & independent applied verification).
- Reference: `references/zero-overengineering-bulkhead-clamp-and-adb-false-positive-20261029.md` (Zero-overengineering bulkhead auto-clamp, ambiguous adb false-positive fix, & step-by-step invariant).
- Reference: `references/crystallize-fix-invariant-and-ratchet-amendment-architecture-20261029.md` (Crystallize fix invariant at closeout Step 2.6, reverse_diff regression proof, & ratchet amend_rule for false-positive recovery).
- Reference: `references/crystallize-fix-invariant-and-watchdog-compliance-20261030.md` (Invariant crystallization at Step 2.6, reverse_diff verification, ratchet amend_rule, monotonic integrity, & watchdog compliance monitoring).
- Reference: `references/unified-pipeline-gate-abc-canary-closeout-lifecycle-20261030.md` (Unified pipeline lifecycle: Gate A-B-C decoupled from Gate 6 Canary Evidence & Closeout Gate authority).
- Reference: `references/unified-pipeline-gate-1-to-6-and-confirm-enforcement-20261030.md` (Unified pipeline Gates 1-6 automation, anti-false-reject post-patch check, & strict confirm enforcement).
- Reference: `references/unified-pipeline-s0-s5-architecture-and-reviewer-loop-20261030.md` (Unified pipeline S0..S5 full-spectrum gate integration, multi-stage rollback, baseline content drift audit, & one-shot reviewer prompt patterns).
- Reference: `references/unified-pipeline-end-to-end-canary-and-context-injection-20261030.md` (Unified pipeline end-to-end canary proof, target-file context forwarding in Gate B S1, & strict non-empty anchor prepend invariants).
- Reference: `references/multi-file-batch-rollback-and-baseline-drift-audit-20261030.md` (Multi-file batch rollback & baseline content drift audit architecture across S2/S3/S4).
- Reference: `references/closeout-v2-o1-hard-replacement-and-legacy-scorecard-retirement-20261030.md` (Closeout v2 O(1) hard replacement, retirement of legacy 3,000-line LLM scoring closeout_gate to _retired/, and direct forwarder lock-in).
- Reference: `references/gate-compliance-14-gates-watchdog-architecture-20261030.md` (Gate compliance watchdog expanded to 14 gates: Pipeline A-B-C, Canary Gate 6, Patch Surgery, Safety Valve, & GPM Proxy monitoring).
- Reference: `references/local-automation-anti-overengineering-hmac-elimination.md` (Local automation anti-overengineering: HMAC debt elimination, TLIS v1 local integrity standard, & reviewer paranoid threat model calibration).

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
