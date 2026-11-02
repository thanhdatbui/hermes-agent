---
name: tiktok-hermes-cron-safety
description: Phase 9A.x → 9C.x production-safety work in the Taadaa Hermes-cron entrypoint inside the EXACT authority worktree — strict TDD (RED first), NO-LIVE (never touch device/host/workbook/credential), AG Opus exact-byte audit, then an exact-allowlist commit gated on APPROVED (no commit before the verdict). Fail-closed seams F1–F5, wrapper templates + deploy/hash (9B.1), declarative job spec (9B.2), timezone preflight (9B.2b), transaction staging create→pause→edit→verify (9B.3), offline manual-run smoke (9B.4), pilot preflight + one-shot activation permit (9C.1).
---
# TikTok Hermes-Cron Production-Safety Remediation (Phase 9A.x → 9B.x)

- **Troubleshooting Reference**: [references/manifest-identity-mismatch-troubleshooting.md](references/manifest-identity-mismatch-troubleshooting.md)
- **Cron Safety & Queue Starvation**: [references/cron-llm-agent-loop-starvation-and-guard-enforcement.md](references/cron-llm-agent-loop-starvation-and-guard-enforcement.md) — PreToolUse guard & auto-quarantine for `no_agent: True`.
- **Healing Selector Loader Troubleshooting**: [references/cron-dynamic-healing-selector-loader.md](references/cron-dynamic-healing-selector-loader.md)
- **Cohort Validation & Block Index Troubleshooting**: [references/cohort-validation-and-block-index-troubleshooting.md](references/cohort-validation-and-block-index-troubleshooting.md)
- **4 Ca x 2 Phiên Invariants**: [references/manifest-4-block-2-session-invariants.md](references/manifest-4-block-2-session-invariants.md)
- **Cadence 4 Ca x 2 Phiên Spec**: [references/cadence-4ca-2phien-manifest-spec.md](references/cadence-4ca-2phien-manifest-spec.md) — xử lý lỗi `MANIFEST_IDENTITY_MISMATCH` khi source config drift mid-day.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
