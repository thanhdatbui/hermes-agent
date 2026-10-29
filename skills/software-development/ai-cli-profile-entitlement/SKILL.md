---
name: ai-cli-profile-entitlement
description: "Use when headless AI CLI fails to inherit IDE subscription."
---
# AI CLI Profile & Entitlement Governance

## 1. When to Use
Use when configuring, debugging, or running headless AI developer CLIs (such as Antigravity `agy.exe`, Gemini Code Assist CLI, Codex CLI) in multi-account or multi-profile sandbox environments where the CLI binary fails to inherit the paid subscription (Pro/Google One AI) that the full GUI IDE possesses, resulting in 429 quota exhaustion (`RESOURCE_EXHAUSTED`).
- Reference: `references/antigravity-entitlement-protocol.md` (Protobuf structure, credit types, onboarding metadata, and local adapter injection).
- Reference: `references/headless-cli-bootstrap-and-device-auth.md` (Autonomous Python bootstrap, Windows PATH shims, and background device OAuth polling for vendor AI CLIs like Qoder/Claude Code).

## 2. Core Problem: Headless CLI vs GUI IDE Divergence
When developer tools package an IDE extension alongside a native CLI binary:
1. **The GUI IDE Client:** Uses a language server + extension bootstrap (e.g., `extension.js`, Node.js IPC). It attaches proprietary headers, session tokens, and explicitly injects paid credit types (e.g., `enabledCreditTypes: ["GOOGLE_ONE_AI"]` / `CreditType.GOOGLE_ONE_AI = 1`).
2. **The Headless CLI Binary:** Often shares the underlying Protobuf schema but lacks the GUI bootstrap flow. In headless execution (`agy -p ...`), it sends vanilla requests without the credit flags, causing upstream servers (e.g. Google Cloud Code API) to classify requests as Free Tier (`currentTier: free-tier` vs `paidTier: g1-pro-tier`) and trigger daily quota limits (~50 reqs/day).

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
