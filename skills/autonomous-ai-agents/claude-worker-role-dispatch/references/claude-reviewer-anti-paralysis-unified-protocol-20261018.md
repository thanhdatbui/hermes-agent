# Claude Reviewer & Coordinator Unified Agreement (Anti-Paralysis Protocol)

*Recorded on: 2026-10-18*  
*Participants: Claude Code CLI (Sonnet 5.5 - Reviewer) and Hermes Coordinator*

---

## 1. Overview of the 3 Incidents
1. **Premature Push:** Pushing commit `2e9b9ae` before running `closeout_gate.py` for Sol review (which scored 74/100 REJECTED due to fixed coordinate taps `tap(540, 1400)` & `tap(60, 140)`).
2. **Blind Evidence Delivery:** Emitting `MEDIA:post-published-surface.png` claiming successful publication while the image actually displayed a context action menu ("Ghim lên đầu / Đặt ở chế độ riêng tư / Chia sẻ") overlaying an old video tile.
3. **Stale Idempotency Receipt:** Machine 79 skipped `MEDIA_PUSH` and `POST` because a stale receipt existed from the previous day's run, producing a false-positive `SUCCESS` report.

---

## 2. Key Synthesis: The Danger of Naive Mechanical Controls
Naive mechanical enforcement creates a **Paralysis Trap**:
- Static push block at $\ge 85$ causes infinite score-chasing or premature `BLOCKED` paralysis.
- Blind negative keyword vetoes cause false-positive stalls on harmless text.
- Global permission revocation paralyzes farm watchdogs and safety cleanup.

---

## 3. Final Unified Protocol Architecture
Every workflow must terminate in one of three deterministic states: `PUSHED`, `PUSHED_GRACE`, or `DEFERRED`.

### A. Session Close Gate (Grace Band + 3-Strike)
- $\ge 85$: Normal push.
- $80 - 84$: Strike 1-2 remediation $\rightarrow$ re-review.
- After Strike 3 and score is $80 - 84$ with 100% tests passing: `PUSHED_GRACE` (auto-pushed with debt logged to ledger).
- $< 80$: Maximum 3 strikes, then `DEFERRED` (commit kept local, handoff documented, session exits cleanly).
- Cap of 2 Grace pushes per repository per 7 days.

### B. Self-Healing Evidence Gate
- **4-Stage Inspection:** File existence/mtime $\rightarrow$ Negative keyword scan $\rightarrow$ Dual-signal false-positive guard (UI XML dialog node verification) $\rightarrow$ Bounded self-healing ($\le 3$ retries via semantic back/close).
- **Sensitive Screen Ban:** No automated back on Post, Payment, or OTP screens.
- **Graceful Unverified State:** If unresolved after 3 attempts, mark `EVIDENCE_UNVERIFIED` and escalate to human review without freezing the session or device.

### C. Action-Scoped Sanction Ledger
- Inviolate actions: Watchdogs, lock releases, and health cleanup are never blocked.
- 4-Tier Sanction:
  - L0: Log and warning.
  - L1: Auto-tag report as `UNVERIFIED`.
  - L2: Lock specific claim/push action until independent verification.
  - L3: Handoff code editing for that scope to an isolated worker.
- Self-Redemption: Penalties degrade after 2 consecutive verified successes.
