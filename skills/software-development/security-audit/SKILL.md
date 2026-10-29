---
name: security-audit
description: "Vulnerability review and security audit for web apps, APIs, PHP/Python services, and vibe-coded projects. Use when auditing codebases, checking git diffs for security holes, or reviewing payment/auth workflows."
version: 1.0.0
platforms: [windows]
metadata:
  hermes:
    tags: [security, audit, vulnerability, web, owasp, auth, php, python]
---
# Security Audit Skill

Defensive, source-first security audit workflow derived from Cloudflare's security-audit framework and tailored for web applications, APIs, PHP monoliths, and vibe-coded systems.

## Trigger Conditions
Use this skill when:
- User asks to "audit security", "kiểm tra bảo mật", "review lỗ hổng" for a repo, module, or git diff.
- Reviewing sensitive features: authentication, payments, wallet balances, webhooks, third-party API integrations, file uploads, or admin controls.
- Preparing to deploy or merge changes to production.

## Operational Modes
1. **Focused Diff Review (Default / Recommended)**: Audit only the changed files (`git diff`) or a single targeted file/controller. Fast, low token overhead, zero context bloat.
2. **Feature Flow Audit**: Audit a specific end-to-end flow (e.g. checkout, login, withdrawal, webhook).
3. **Full Codebase Audit**: Performed on explicit request. Runs multi-stage recon and hunting across all endpoints.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
