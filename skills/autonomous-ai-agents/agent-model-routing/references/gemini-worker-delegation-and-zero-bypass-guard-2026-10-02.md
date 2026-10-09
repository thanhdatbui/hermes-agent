# Gemini Sub-Agent Delegation & Zero-Bypass Guard Architecture (2026-10-02)

## 1. Context & The Incident of 2026-10-01
On October 1st, 2026, during high-cadence Taadaa Farm operations (80-160 devices), the theoretical "pure multi-agent ladder" (Sol Plan -> Luna Worker implementation in sterile cage) suffered catastrophic operational paralysis:
- **6 fatal timeouts on Luna Worker**: Each Luna session timed out at 480s (totaling ~48 minutes wasted idle time).
- **Tool call budget blowout**: Over 50% of Luna workers blew past normal bounds, running up to 42 tool calls wandering the codebase.
- **Root cause of Luna paralysis**: Luna High (`cx/gpt-5.6-luna-high`) spent 25-40s per turn generating deep reasoning tokens. On ambiguous briefs or large files, 12-15 iterative tool turns easily exceeded the 480s gateway timeout.
- **Root cause of Guard bypass**: `guard_dispatch_contract.py` parsed `payload.get("args")`, while Hermes wire protocol transmitted `payload.get("tool_input")`, allowing unanchored dispatches to bypass Gate 2/Gate 4 silently.

Meanwhile, when Gemini Coordinator directly hotfixed field issues:
- **MTTR (Mean Time to Recovery)**: 1-2 minutes per incident.
- **Quality at Closeout**: 100% of pushed sessions (195937, 195917, 195849, 190402, 173858) scored APPROVED >= 85/100 from Sol Reviewer via `closeout_gate.py`.

## 2. User Directive & Architectural Consensus (2026-10-02)
User directive:
1. **Coordinator direct fix restricted to small scope (T1)**: Exactly 1 file, cumulative diff <= 15 lines, focused test < 30s.
2. **Hard mandate to spawn sub-agent on hard cases (T2)**: Multiple files (>= 2), diff > 15 lines, or core architecture (watchdog, device locks, database schema). Coordinator MUST NOT attempt complex multi-file surgery in the primary session to prevent context bloat and hallucination.
3. **Switch Sub-Agent Worker from Luna to Gemini**: Replace `cx/gpt-5.6-luna-high` with `ag-gemini-pool-3` (via custom:omni `:20129`).

## 3. Worker Model Comparison: Luna High vs Gemini Pool 3

| Metric | Luna High (`cx/gpt-5.6-luna-high`) | Gemini Pool 3 (`ag-gemini-pool-3`) |
|---|---|---|
| **Turn Latency** | 25–40s / turn (heavy reasoning) | **1–3s / turn (lightning fast)** |
| **End-to-End Task Time** | 300–480s (often timing out) | **30–45s (5–8 calls completed)** |
| **Account Pool & Quota** | Codex pool (prone to 429 & queue delays) | **49-account Gemini pool (ample zero-cost quota)** |
| **Failure Mode** | Overthinking & wandering files | Hasty edits without bounds (mitigated by Guard) |
| **Mitigation Applied** | N/A | **Hard Scope Lock + Ceiling 15 calls + Sandbox roots** |

## 4. Active Delegation Configuration (`config.yaml`)
```yaml
delegation:
  model: ag-gemini-pool-3
  provider: custom:omni
  child_timeout_seconds: 180    # Fail-fast at 3 minutes instead of hanging 8 minutes
  reasoning_effort: medium      # ⚡ CRITICAL USER MANDATE: Bắt buộc để medium, TUYỆT ĐỐI CẤM tự ý đổi sang low/high/max
  max_iterations: 15            # Guard ceiling matches Hermes iteration ceiling
  max_concurrent_children: 6
```

> **CRITICAL REASONING INVARIANT (User Directive 2026-10-02):**
> Khi cấu hình model delegation hoặc OmniRoute: **REASONING BẮT BUỘC ĐỂ MEDIUM**. Tuyệt đối không tự ý chế sang `low` (mất khả năng suy luận cơ bản) hoặc `high`/`max` (gây ngâm turn overthinking). User cực kỳ dị ứng việc agent tự ý đổi cấu hình reasoning mà không hỏi.

## 5. Zero-Bypass Guard Safeguards & Claude CLI SRE Hardening (Hermetic Certified)
1. **Wire Protocol Compatibility**: Both `tool_input` and `args` are checked fail-closed; invalid payloads reject with `PAYLOAD_UNPARSEABLE`.
2. **Gate 2 Anchor Check ($c == 1$)**: Anchor MUST exist exactly once in target file (`grep -o | wc -l == 1`). 0 hits or >= 2 hits rejected before worker spawns.
3. **Gate 4 Worker Call Ceiling**: Tool call #16 is blocked unconditionally by the guard (`BUDGET EXHAUSTED`), enforcing fail-fast.
4. **Coordinator Write Ledger & Terminal Lockdown (Claude CLI SRE Audit)**:
   - T1: Cumulative limit of 1 file and <= 15 lines diff across the entire coordinator session.
   - Shell Metacharacter Blocking: BẮT BUỘC áp dụng `_SHELL_METACHAR_RE` trên terminal Coordinator, chặn tuyệt đối chuỗi nối lệnh (`;`, `&&`, `||`, `|`, `$`, `` ` ``).
   - `.git/**` Lockdown: Cấm tuyệt đối patch/write_file hoặc terminal trỏ vào `**/.git/**` (bảo vệ `.git/config` chống hook backdoor).
   - Gỡ bỏ các công cụ nguy hiểm khỏi Coordinator terminal allowlist: `claude`, `cp`, `taskkill`, `python <script.py>` tùy ý, và `pytest` không có node_id.
5. **Closeout Gate Cryptographic Binding (Chống Giả Mạo `closeout_passed`)**:
   - `closeout_passed` KHÔNG ĐƯỢC dựa vào chuỗi stdout suông (tránh giả mạo `echo 'Verdict: APPROVED'`).
   - Phải đọc trực tiếp từ `D:/Taadaa/logs/gate_audit.jsonl` (khớp timestamp <= 60s, exit code 0, score >= 85, verdict APPROVED).
   - Gắn chặt với SHA-256 hash của git diff lúc closeout. Khi chạy `git commit`, guard kiểm tra diff hiện tại phải khớp đúng hash đã được duyệt (chống sửa code sau closeout).
   - Chặn tuyệt đối các cờ bypass commit: `--no-verify`, `--amend`.
6. **Outcome Verification Gates (Non-negotiable)**:
   - **Real Device Canary**: Must run on >= 1 idle farm phone, producing `MEDIA:<path>` photo + WinRT OCR proof.
   - **Closeout Gate**: `closeout_gate.py` requires Sol Reviewer score >= 85/100 before any git push.
