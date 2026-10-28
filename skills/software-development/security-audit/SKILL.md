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

## 6-Phase Audit Workflow

### Phase 1: Reconnaissance (Attack Surface & Trust Boundaries)
- Map public entry points (`routes/`, `controllers/`, `ajax/`, `api/`).
- Identify user-controlled inputs (`$_GET`, `$_POST`, `$_REQUEST`, request bodies, query params, headers).
- Identify external sinks: database queries, subprocess calls, HTTP requests (`curl`, `requests`), file operations.
- Map privilege boundaries: Guest vs Authenticated User vs Admin.

### Phase 2: Hunting (High-Impact Vulnerability Classes)

#### 1. Injection & Data Exposure
- **SQL Injection**: Check if queries use parameterized/prepared statements (PDO/ORM) or raw string concatenation.
- **Command Injection**: Detect unsafe `exec`, `shell_exec`, `system`, `passthru`, `subprocess.Popen(..., shell=True)`.
- **SSRF**: Detect arbitrary URL fetching via `curl`, `httpx`, `requests` without allowlist/private IP blocking (127.0.0.1, 10.x, 169.254.x).

#### 2. Authentication & Authorization (IDOR & Broken Access Control)
- **Session & Privilege Hijacking**: Ensure admin actions check `session['is_admin']` or JWT claims server-side.
- **Insecure Direct Object Reference (IDOR)**: Verify that updating/viewing resources checks `resource.user_id == current_user.id`.

#### 3. Business Logic & Race Conditions (Critical for Payments/Wallets)
- **Double Spending / Balance Drain**: Financial transactions (wallet deduction, order checkout) MUST use database row locking (`FOR UPDATE` / atomic transactions).
- **Webhook Spoofing**: Ensure payment callbacks verify cryptographic signatures (HMAC-SHA256, secret token) before crediting balance.

#### 4. Credential & Secret Exposure
- Detect hardcoded API keys, JWT secrets, database passwords, or proxy credentials in source code.
- Ensure debug modes and verbose error logs are disabled in production.

### Phase 3: Validation & False-Positive Elimination
- **Rule of Real Exploitation**: A theoretical code smell is NOT a finding unless an attacker can reach the sink with untrusted input under realistic conditions.
- Trace data from Source (input) -> Sanitizer/Validator -> Sink (execution). If fully neutralized, discard as false positive.

### Phase 4: Minimal Effective Patch
- Provide the smallest code delta (<= 15 lines per fix) that neutralizes the vulnerability without breaking business functionality.
- Do not refactor unrelated code.

### Phase 5: Structured Finding Report
Format every confirmed finding as:
- **Title**: Vulnerability name (e.g. `[HIGH] IDOR in Order Cancellation API`)
- **Location**: `path/to/file:line_number`
- **Impact**: Concrete risk to business/user (data leak, money loss, server takeover)
- **Exploitation Path**: How untrusted input flows from Source to Sink
- **Remediation**: Exact before/after code diff
