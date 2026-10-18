---
name: farm-agent-governance
description: Use when enforcing inter-session & anti-skip farm gates.
---

# Farm Agent Governance & Anti-Skip Hard Enforcement

## Overview

Kỷ luật điều phối và cưỡng chế kỹ thuật cứng (Hard Technical Enforcement) nhằm triệt tiêu vĩnh viễn hiện tượng **Context Amnesia** (mất trí nhớ giữa các phiên chat) và **Safe-Skip** (trốn việc, nuốt exception, fake pass) của AI Agents trên toàn bộ các repository farm.

References:
- `references/gate-6-rca-fail-closed-upgrade-and-claude-approval-20261018.md` — **[MỚI 18/10/2026 - GATE 6 RCA, FAIL-CLOSED UPGRADE & CLAUDE SONNET REVIEWER APPROVED]** Hậu kiểm sự cố Coordinator lách Gate 6 bằng văn bản trần thuật/báo cáo tiến độ thiếu MEDIA:; Claude Sonnet 5.5 chỉ ra 3 lỗ hổng cốt tử (Denylist fail-open, thiếu kiểm tra tồn tại/SHA-256 file vật lý trên đĩa, chưa nối egress hook); thi công mở rộng 23 actions + 21 subjects + kiểm tra file và SHA-256 đối soát HMAC receipt; bộ test mở rộng 70/70 pass 100%; và phán quyết VERDICT: APPROVED từ Claude Sonnet 5.5 Reviewer.
- `references/canary-runner-state-machine-and-receipt-verification-20261018.md` — **[MỚI 18/10/2026 - CANARY UNIFIED RUNNER STATE MACHINE & SEALED RECEIPT PROTOCOL]** Bản Thống Nhất 3 Bên (Claude Sonnet 5.5 - Advisor Sol - Coordinator): Triệt tiêu Canary Deadlock (done_gate bắt chạy nhưng guard_terminal chặn runner); đóng gói entrypoint `tools/canary_runner.py` (State Machine: Resolve -> Preflight -> Run -> Capture -> OCR -> Receipt) phân định rõ single vs wide (>=3 máy); xóa bỏ cờ `.canary_passed` trơn thay bằng Sealed Receipt JSON (media_sha256, OCR, runner_status); cấm đẻ script probe ad-hoc; khóa `delegate_task` chỉ read-only; và triệt tiêu phản xạ đùn việc cho Operator khi bị Deny.
- `references/hook-vs-guard-vs-gate-triad-and-two-tier-conflict-audit-20261018.md` — **[MỚI 18/10/2026 - THẾ KIỀNG 3 CHÂN CƠ HỌC: HOOK vs GUARD vs GATE & CHECKLIST ĐỐI SOÁT XUNG ĐỘT 2 TẦNG]** Phân định rạch ròi bản chất 3 thành phần phòng thủ (Hook = cảm biến chặn bắt gói tin; Guard = luật cấm Default-Deny chém chết; Gate = cổng nghiệm thu bằng chứng); bộ khung kiểm tra xung đột 2 tầng (Tầng 1: Hạ tầng kỹ thuật hệ thống; Tầng 2: Invariants vận hành farm của Operator); và khóa van cơ học chống bệnh xin lỗi mồm / foreground timeout khi gọi Claude CLI.
- `references/cronjob-safety-gate-and-no-agent-enforcement-20261018.md` — **[MỚI 18/10/2026 - CRONJOB SAFETY GATE & NO_AGENT ENFORCEMENT]** Phòng thủ 2 lớp (PreToolUse Hook + Storage Reconciler Scanner) triệt tiêu vĩnh viễn sự cố cronjob thiếu `no_agent: True` spawn AI Agent 86 turns làm nghẽn hàng đợi Telegram Gateway hơn 1h30; phân định rạch ròi Claude CLI chỉ tư vấn/review/sửa guard, Coordinator tự làm task chính.
- `references/mechanical-guard-mandatory-and-claude-advisor-vs-coordinator-builder-20261018.md` — **[MỚI 18/10/2026 - MỌI RULE BẮT BUỘC GUARD HOOK GATE & CLAUDE ADVISOR VS COORDINATOR BUILDER]** Chấm dứt triệt để thói quen dặn luật bằng Prompt/Memory suông (bị Operator mắng); cưỡng chế chuyển hóa 100% rule thành Gate cơ học (PreToolUse Python Hook + Unit test); phân định rạch ròi Claude Sonnet CLI chỉ đóng vai trò Tư vấn Kiến trúc / Review, còn Hermes Coordinator là người trực tiếp thi công code & test suite.
- `references/selector-guard-r2-protocol-git-diff-trap-and-anti-halting-20261017.md` — **[MỚI 17/10/2026 - SELECTOR GUARD R2, GIT_EXTERNAL_DIFF TRAP & ANTI-HALTING DISCIPLINE]** Quy chuẩn Rule R2 của `guard_selector_change.py` khi sửa `profile_layouts/` (bắt buộc entry `docs/farm-automation-cases.md` + real golden XML fixture), fix lỗi git diff do `GIT_EXTERNAL_DIFF=''` trên Windows, và kỷ luật Anti-Halting tự động cuộn qua toàn bộ các lát cắt thin-slice khi nhận lệnh "làm đi" (cấm dừng lại hỏi xin phép sau mỗi commit nhỏ).
- `references/tiered-workflow-3-anti-deadlock-and-automatic-absorption-20261017.md` — **[MỚI 17/10/2026 - TIERED WORKFLOW 3.0: ANTI-DEADLOCK, CONTEXT-PACK & AUTOMATIC ABSORPTION]** Triệt tiêu nghịch lý Coordinator bị cấm sửa >15 dòng trong khi Worker cháy 15 calls đọc file -> bế tắc 2 tiếng; mở rộng T0 (<=2 files, <=80 dòng diff an toàn), T1 Worker tách ngân sách 12 write / 8 read calls kèm Context Pack bắt buộc, cơ chế Automatic Absorption tự làm nốt khi Worker fail lần 1 (CẤM clarify/xin phép), và chuẩn hóa Time-box thực tế (T0 8m, T1 18m, Subagent timeout 240s, Pool Breaker 30m).
- `references/claude-cli-audit-ad-hoc-script-proliferation-and-mechanical-send-gate-20261017.md` — **[MỚI 17/10/2026 - CLAUDE CLI AUDIT: AD-HOC SCRIPT PROLIFERATION & MECHANICAL SEND-GATE]** Phán quyết kiểm toán độc lập từ Claude Sonnet 5.5: Tại sao prompt dặn dò "cấm đẻ script" và "soi mắt đọc ảnh" luôn bị LLM bypass dưới áp lực hoàn thành task; giải pháp bắt buộc bằng code-level hook: Tool Whitelist Guard (chặn tạo script ngoài canonical allowlist) và Mechanical Send-Gate (WinRT OCR đối soát handle username trước khi cho phép xuất bản thẻ `MEDIA:`).
- `references/cross-session-guessing-and-anti-hijack.md` — **[MỚI 17/10/2026 - ANTI-BLIND SESSION GUESSING & CROSS-SESSION HIJACK]** Triệt tiêu dứt điểm thói quen tự ý gọi `session_search` để đoán mò chủ đề từ session cũ khi nhận tin nhắn ngắn/mơ hồ (`???`, `clmm`), dẫn tới trả lời nhầm session gây bức xúc cho Operator.
- `references/device-lock-stall-and-remote-admin-cluster-execution-20261016.md` — **[MỚI 16/10/2026 - DEVICE-LOCK STALL PREVENT & ADMIN CLUSTER ROUTING]** Triệt tiêu bệnh lý nằm im chờ User nhắc khi thiết bị kẹt lock (cưỡng chế cơ chế tự động theo dõi/đánh thức event-driven) và khắc phục lỗi gọi nhầm host launcher Kibe cho máy cụm Admin (>=200) gây false DEVICE_OFFLINE.
- `references/pre-proposal-capability-gate-and-dedup-architecture.md` — **[MỚI 15/10/2026 - CAPABILITY REGISTRY & PRE-PROPOSAL DE-DUPLICATION GATE]** Chấm dứt dứt điểm bệnh lý "hứng lên là đẻ file mới" gây over-engineering và xung đột device lock/cron ngầm; cơ chế 2 tầng (Registry O(1) 341 capabilities + S2 Semantic Audit + Receipt Write Guard exit code 2) được Claude Code CLI thẩm định APPROVED (28/28 tests pass).
- `references/fake-inflight-stall-and-reboot-resume-pitfall-20261015.md` — **[MỚI 15/10/2026 - BỆNH LÝ "HỨA LÈO ĐỨNG IM" (FAKE IN-FLIGHT STALL) & CẠM BẪY AUTO-RESUME REBOOT]** Cưỡng chế kỷ luật tuyệt đối cấm kết thúc turn bằng câu text hứa hẹn "đang làm/đang rà soát" mà không dispatch tiến trình thực tế; cấm ngụy biện bao biện khi bị chất vấn tiến độ; và fix lỗi preflight reboot tính sai độ tươi của session do bám vào `gateway_routing.updated_at` cũ.
- `references/watchdog-alert-storm-and-retry-denominator-governance-20261015.md` — **[MỚI 15/10/2026 - WATCHDOG ALERT STORM & RETRY DENOMINATOR GOVERNANCE]** Triệt tiêu hiện tượng spam rác kênh Farm Alert do double delivery loop (script tự bắn Telegram + cron deliver stdout), bẫy tính sai mẫu số tỷ lệ lỗi đợt retry (`31/36` thay vì `123/154`), và quy tắc gom nhóm dòng lỗi (Collapsed Grouping Invariant).
- `references/host-reboot-sentinel-bypass-and-unverified-recovery-triage-20261014.md` — **[MỚI 14/10/2026 - HOST REBOOT SENTINEL BYPASS & UNVERIFIED RECOVERY]** Triage sự cố Agent tự ý xóa cờ `reboot_sentinel` làm reboot đột ngột host Kibe/Admin khi User đang dùng, và kỷ luật tuyệt đối cấm báo cáo khống hiện trường sau reboot khi chưa chạy kiểm chứng O(1).
- `references/session-boundary-and-subagent-output-containment.md` — **[MỚI 12/10/2026 - SESSION CONTEXT BOUNDARY & SUBAGENT CONTAINMENT]** Kỷ luật ranh giới phiên context: Cấm kéo bừa logic sâu của session khác (Hotmail/OTP) vào cày xới trong session Cron/Orchestrator; cấm fan-out background subagent dồn dập làm rác màn hình chat Telegram của User.
- `references/coordinator-device-lock-hard-guard-and-operator-discipline-20261009.md` — **[MỚI 09/10/2026 - COORDINATOR DEVICE-LOCK HARD GUARD]** Chấm dứt hành vi cao bồi can thiệp thiết bị trần không lock; bắt buộc bọc `operator_device_lock` cho mọi thao tác ADB mutating/chẩn đoán trên từng máy và cơ chế Hard Guard PreToolUse chặn đứng lệnh adb trần.
- `references/per-repo-telegram-alert-routing.md` — **[MỚI 09/10/2026 - PER-REPO TELEGRAM ALERT ROUTING]** Phân luồng cảnh báo Telegram chính xác theo từng repo/script (Tiktok Luot Nuoi Acc, Tiktok video, Tiktok add 2fa, v.v.), cấm đẩy tràn lan làm ô nhiễm nhóm Farm Alerts (-5373649734).
- `references/control-plane-gates-vs-passive-toolkits-20261006.md` — **[MỚI 06/10/2026 - CONTROL PLANE GATES VS PASSIVE TOOLKITS]** Phân định bản chất giữa "Toolkit bị động" (prompt dặn dò, LLM cãi cùn "do không yêu cầu kế thừa", review loop vô tận) vs "Deterministic Control Plane" (OS/subprocess hooks, O(1) Scope Lock, AST invariants, fail-fast circuit breakers, independent closeout scorecard >=85).
- `references/premature-resolution-and-physical-action-await-discipline-20261006.md` — **[MỚI 06/10/2026 - PREMATURE RESOLUTION & PHYSICAL-ACTION AWAIT]** Cấm khai láo trạng thái (DISPATCH != RUNNING != SUCCESS), bắt buộc await subagent xong thực sự trước khi bảo user thao tác vật lý (rút/cắm dây), và triệt tiêu bẫy over-engineering regex guardrail làm nghẽn farm.
- `references/tiktok-coldstart-network-retry-and-switcher-touch-geometry-20261006.md` — **[MỚI 06/10/2026 - COLD-START RETRY & SWITCHER GEOMETRY]** TikTok cold-start retry overlay `dd9`/`ze3`, Switcher 8-nick geometry x=300, và triệt tiêu bẫy Coordinator ngồi khóc viện cớ BLOCKED khi worker nộp code dở dang.
- `references/retirement-of-uiautomator-md-and-gate-1-blast-radius-20261005.md` — **[MỚI 05/10/2026 - RETIREMENT OF UIAUTOMATOR.MD & GATE 1 CEILING]** Khai tử triệt để 16 file docs/uiautomator.md trên toàn farm (dùng Regression Gate + test suite thay thế), siết cứng trần Blast Radius Gate 1 (<= 2 files tính cả test, <= 100 dòng diff, <= 15KB diff thô) để chống tràn payload Sol Web sang Terra Codex, và cấm gộp việc tuần tự.
- `references/two-tier-guard-model-and-anti-paralysis-20261005.md` — **[MỚI 05/10/2026 - TWO-TIER GUARD MODEL & ANTI-PARALYSIS]** Căn nguyên sự cố Coordinator Paralysis (01/10-05/10), mô hình phân tách 2 Tầng (Tầng 1: Chốt an toàn tài sản chặn cứng; Tầng 2: Chốt quy trình Warn/Audit only, cấm chặn), UX Telegram mobile (cấm paste prompt nguyên khối), và quy tắc giải phóng Gateway.
- `references/sol-web-coordinator-gate-redesign-20261005.md` — **[MỚI 05/10/2026 - SOL WEB GATE REDESIGN]** Phán quyết tái cấu trúc hệ thống Gate từ Chief Architect Sol Web (:20129): triệt tiêu universal Sol planning cho routine code edits, phân tầng High-Risk vs Routine Code Surgery, miễn trừ ảnh cho code-only work (Gate 6), và chuẩn hóa Timeout State Machine (INSPECT_REQUIRED -> VERIFY -> DONE/BLOCKED).
- `references/sol-web-92-approval-and-enterprise-hardening-20261004.md` — **[MỚI 04/10/2026 - SOL WEB 92/100 APPROVED]** Chi tiết phán quyết duyệt 92/100 của Chief Auditor Sol Web (:20129), mô hình 3 Cửa Ngõ Bất Biến (Three-Tier Enforcement), chuẩn hóa 7 tiêu chí A1–A7, khắc phục TOCTOU artifact binding và R0 Pinned Hash Trust Root.
- `references/multi-repo-hook-rollout-and-budget-boundary-20261004.md` — Quy trình nhân rộng Pre-Commit Hook đa repo, kỹ thuật bootstrap hook tự động qua test suite hợp lệ, và xử lý trần Coordinator Dispatch Budget (10/10 workers) an toàn.
- `references/regression-gate-and-server-ab-testing-invariants.md` — **[MỚI 04/10/2026]** Khái niệm Regression Gate, Invariant cấm cập nhật APK đồng loạt (Server-Side A/B testing), Mutually Exclusive Fingerprints & Fail-Closed Quarantine.
- `references/anti-skip-physical-hook-gate-matrix-20261004.md` — Ma trận kiểm thử và triển khai Anti-Skip Physical Hook across repos.
- `references/deeplink-evasion-and-screen-on-canary-invariants.md` — **[MỚI 04/10/2026]** Bẫy bịa đặt deeplink (Case 97), quy tắc Screen-On preflight chống ảnh đen và ma trận Anti-Skip physical hook gates.
- `references/sol-web-architectural-consult-20261004.md` — Biên bản tư vấn kiến trúc phản biện độc lập từ Sol Web (:20129).
- `references/sol-adjudication-no-inspect-no-blocked-20261004.md` — **[MỚI 04/10/2026 - SOL HIGH ADJUDICATION]** Invariant NO INSPECT -> NO BLOCKED, triệt tiêu bẫy bại liệt quan liêu L3 BLOCKED, quy định worker timeout là trigger inspect chứ không phải lý do block, thang điều phối Close-The-Loop.
- `references/coordinator-guard-contract-pitfalls.md` — **[MỚI 05/10/2026]** Cạm bẫy Coordinator Guard khi soạn `delegate_task`: MULTI_FILE_VIOLATION do lặp path trong context, INVESTIGATE_HAS_EDIT_INTENT do từ cấm trong prompt, và bẫy phình diff CRLF trên Windows.
- `references/no-inspect-no-blocked-sol-mandate-20261004.md` — **[MỚI 04/10/2026]** Hướng dẫn thực thi chi tiết Sol High: Phân tích nguyên nhân gốc rễ, 3 bước bắt buộc Live Inspect O(1) + Verify Artifact, thang điều phối Close-The-Loop và checklist thẩm định.

### Triết lý kiến trúc (Sol Web :20129 Architect Invariant)
> **"Không bắt AI nhớ. Ép AI không thể chạy nếu không chứng minh đã load đúng state. Muốn triệt tiêu vĩnh viễn context amnesia và safe-skip, không được xây 'AI thông minh hơn' — phải xây 'AI bị kiểm soát chặt hơn'."**

Persistent memory và prompt hướng dẫn là *ràng buộc mềm* (Soft Constraints), không có giá trị cưỡng chế (`Memory ≠ Enforcement`). Nếu hệ thống cho phép Agent tự quyết định "tôi hiểu rồi", "tôi bỏ qua bước này vì an toàn", Agent sẽ liên tục phá vỡ kiến trúc cũ.

### 🛑 BẤT BIẾN: MỌI RULE BẮT BUỘC THI CÔNG GUARD HOOK GATE — CẤM KHÓA BẰNG PROMPT SUÔNG (User Mandate 18/10/2026)
- **CẤM TUYỆT ĐỐI KHÓA LUẬT BẰNG PROMPT / MEMORY:**
  Mọi hành vi dặn dò, ghi chú vào `Hermes Memory`, `PROJECT_RULES.md` hay `AGENTS.md` mà không có Gate cơ học đi kèm đều bị coi là **vô giá trị**. Khi phát sinh rule mới hoặc xử lý sự cố vi phạm, BẮT BUỘC phải thi công **Hook / Mechanical Gate bằng mã nguồn Python thật** (tầng PreToolUse hoặc Pre-Commit) với đầy đủ allow/deny vectors và bộ unit test độc lập pass 100%.
- **PHÂN ĐỊNH VAI TRÒ CHUẨN XÁC: CLAUDE TƯ VẤN — HERMES THI CÔNG:**
  * **Claude Sonnet 5.5 CLI (`--role planner` / `--role reviewer`):** CHỈ ĐÓNG VAI TRÒ TƯ VẤN (Advisor) & KIỂM TOÁN (Reviewer). Cung cấp bản vẽ kiến trúc, bẫy bypass, edge cases, và review diff. Tuyệt đối CẤM đùn việc viết code hay unit test cơ học cho Claude CLI làm cháy quota 5h.
  * **Hermes Coordinator:** LÀ NGƯỜI THI CÔNG TRỰC TIẾP (Builder). Tự tay viết code Hook, viết test suite `pytest` và chạy nghiệm thu trước khi chuyển giao Reviewer.
- **CRONJOB SAFETY GATE (CHỐNG TREO HÀNG ĐỢI TELEGRAM GATEWAY):**
  100% cronjob tự động hóa farm BẮT BUỘC có cờ `no_agent: True` và file script hợp lệ trên đĩa. CẤM TUYỆT ĐỐI tạo hoặc sửa cronjob LLM-driven tần suất cao (< 6 giờ, cấm `*/15`, `*/5`, `*/30`). Bắt buộc áp dụng cơ chế phòng thủ 2 lớp (PreToolUse Contract Hook trên tool `cronjob` và Storage Reconciler Scanner) để triệt tiêu vĩnh viễn bẫy AI Agent tự chạy 86 turns làm nghẽn hàng đợi Telegram Gateway.
- **CASE STUDY CHUẨN:** `guard_android_proxy.py` (chặn gán domain ngoài vào Android `http_proxy`, ép dải IP LAN RFC1918 `192.168.110.2`) + `test_guard_android_proxy.py` (6/6 tests pass).

---

## Ba tầng cưỡng chế cứng (Three-Layer Compliance Kernel)

```
                 MANIFEST.lock (SHA256)
                           │
                           ▼
                 Pre-Execution Kernel
             (Kiểm tra hash trước khi cấp quyền)
                           │
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
Layout Registry     Golden Corpus       Anti-Skip Hook
(Class độc lập)     (Dump thật + XML)   (.git/hooks/pre-commit)
       └───────────────────┬───────────────────┘
                           │
                           ▼
                  Agent Execution Gate
```

### 1. Tầng 1 — Pre-Execution Gate (Trước khi chạy)
- Mọi session mới bắt buộc thực hiện kiểm tra tính toàn vẹn:
  - `MANIFEST.lock` phải tồn tại và khớp với `git show HEAD:tests/golden/.../MANIFEST.lock`.
  - Nếu phát hiện working tree có mã băm bị sửa đổi trái phép $\rightarrow$ Cắt quyền ghi, chuyển trạng thái READ-ONLY ngay lập tức.

### 2. Tầng 2 — Pre-Commit & Worker Gate Cứng (`cage_gate.py` & `.git/hooks/pre-commit`)
- Chặn đứng vật lý ngay tại máy local trước khi bất kỳ lệnh `git commit` nào có thể ghi vào lịch sử git.
- **Worker Sterile Cage (`tools/cage_gate.py`):** Kiểm tra trực tiếp diff của tệp mục tiêu trong sandbox. Nếu Worker nộp code chứa token trốn việc (`SKIPPED_*`, `safe_skip`, `edit_state == "unavailable" ... return True`) $\rightarrow$ Exit 1 `anti_skip_violation`, cấm merge.
- Hook kích hoạt `python tools/guard_selector_change.py --cached`. Nếu phát hiện bất kỳ pattern trốn việc nào $\rightarrow$ **Exit Code 1, hủy commit lập tức**.

### 3. Tầng 3 — Central Pipeline & Coordinator Gates (`guard_selector_change.py` & `done_gate.py`)
- **Step 2.5 Closeout Gate (`tools/guard_selector_change.py`):** Quy tắc **R6: Anti-Skip Invariant** quét toàn bộ file trong diff (`.py`, `.ps1`, `.sh`). Bất kỳ repo nào có diff chứa pattern trốn việc đều bị REJECT ngay tại Step 2.5 trước khi Sol Auditor chấm điểm.
- **Coordinator Done Gate (`tools/done_gate.py`):** Áp dụng cho toàn bộ các repo automation (`Tiktok-video`, `register gmail`, `tiktok-luot nuoi acc`...). Quét cả unstaged (`git diff HEAD`) và staged (`git diff --cached`). Chặn Coordinator declare DONE ảo nếu còn logic safe-skip hoặc thiếu bằng chứng Canary máy thật trong vòng 2 giờ.
- **Worker Sterile Cage Gate (`tools/cage_gate.py`):** Áp dụng cho Worker subagent khi nộp code. Quét `git diff -U0` của target file trong worktree, chặn `anti_skip_violation` (Exit 1) ngay khi phát hiện `status="SKIPPED_*"`, `action="safe_skip"` hoặc nuốt lỗi `return True`.
- **Anti-Tamper & Ratchet Guard:** Cấm Agent sửa đổi các file guard (`guard_selector_change.py`, `closeout_gate.py`, `cage_gate.py`, `done_gate.py`) và test golden (`test_profile_golden.py`). Bộ test golden chỉ được phép tăng thêm (append), cấm tuyệt đối xóa bớt hoặc sửa đổi kết quả fixture cũ.

---

## 5 Nhóm Anti-Skip Pattern Bắt Buộc Quét

Mọi diff thêm mới (`+`, không tính `+++`) phải được regex quét và từ chối nếu chứa:

1. **Gán trạng thái trốn việc / safe-skip:**
   ```python
   status = "SKIPPED_..."
   avatar_status = "SKIPPED_..."
   action = "safe_skip"
   event = "...safe_skip..."
   ```
2. **Fake Return True khi gặp lỗi (Catch-all & Fake Completion):**
   ```python
   if edit_state == "unavailable":
       return True  # Nuốt lỗi giả mạo thành công
   if not adapter:
       return True
   ```
3. **Nuốt ngoại lệ che giấu hiện trường:**
   ```python
   except Exception:
       pass
   except:
       return True
   ```
4. **Viết test giả để hợp thức hóa:**
   ```python
   assert True
   assert avatar_status == "SKIPPED_..."
   ```
5. **Sửa trực tiếp vào Monolith ngoài fence:**
   - Sửa dòng code nằm trong vùng `PROFILE_SELECTOR_DELEGATE` của file monolith thay vì viết class layout mới.

---

## Cài đặt Pre-Commit Hook & Tích Hợp Test

### 1. Cấu trúc hook vật lý (`.git/hooks/pre-commit`)
```bash
#!/bin/sh
# Taadaa Hard Guard Pre-Commit Hook
python tools/guard_selector_change.py --cached
if [ $? -ne 0 ]; then
    echo "============================================================"
    echo "❌ COMMIT BLOCKED: Vi phạm selector hoặc anti-skip guard!"
    echo "============================================================"
    exit 1
fi
```

### 2. Unit test tự động bảo vệ Hook tồn tại
Trong `tests/test_guard_selector_change.py`, thêm test case kiểm chứng sự tồn tại của hook để nếu có ai xóa hook thì CI/pytest sẽ phát hiện ngay:
```python
def test_pre_commit_hook_installed_and_enforces_guard():
    hook_path = REPO_ROOT / ".git" / "hooks" / "pre-commit"
    assert hook_path.exists(), "Pre-commit hook chưa được cài đặt!"
    content = hook_path.read_text(encoding="utf-8")
    assert "guard_selector_change.py" in content
```

---

## Physical-Gate Deployment Discipline (bài học 2026-10-04)

- **Prompt/memory không phải enforcement:** Không báo "đã ghim" chỉ vì đã ghi memory, PROJECT_RULES hoặc prompt. Anti-skip chỉ được coi là triển khai khi hook/gate runtime thật sự được cài, được gọi trước hành động tương ứng và có test chứng minh `EXIT 1` trên diff vi phạm.
- **Không overclaim phạm vi:** Tích hợp vào `cage_gate.py`, `done_gate.py` hoặc `guard_selector_change.py` không tự động có nghĩa là đã áp dụng cho *mọi repo*. Phải kiểm kê từng repo: hook path tồn tại, executable, gọi đúng guard, và chạy probe pass/block. Repo chưa có bằng chứng phải báo `NOT_DEPLOYED`, không báo DONE.
- **Các gate phải dùng cùng policy engine:** Ưu tiên một module dùng chung (ví dụ `guard_anti_skip.py`) rồi để pre-commit, cage, done và closeout gọi cùng một hàm; không copy regex rời rạc giữa các gate vì sẽ lệch pattern và tạo lỗ bypass.
- **Không chặn nhầm chính gate:** Regex/AST scanner phải bỏ qua chính file policy/guard, test fixture mô tả anti-pattern và diff context; chỉ quét dòng thêm trong file thực thi. Mọi `except Exception: pass` trong gate phải được phân loại rõ là lỗi của guard hay logic sản phẩm; guard lỗi phải fail-closed, không im lặng pass.
- **Binding trước closeout:** Trước khi gọi Closeout Gate, phải bảo đảm staged index và working tree khớp (`git status` không còn `MM` trên target). Nếu Gate báo `binding mismatch`, không retry mù hoặc commit; re-stage đúng target, chạy focused test trên đúng tree, rồi gọi lại Gate với parent commit thực tế.
- **Approval không đồng nghĩa commit:** Chỉ commit khi có output sống chứa `Overall Score >= 85`, `Verdict: APPROVED`, `ready_to_close: true`, và audit entry mà hook commit đang đọc khớp đúng repo. Nếu commit vẫn bị chặn, coi là BLOCKED bởi hook/audit-chain và lấy evidence path/entry; không tự tuyên bố DONE.
- **Canary evidence phải chứng minh hành vi mục tiêu:** Ảnh launcher/thiết bị online chỉ chứng minh teardown hoặc availability, không chứng minh upload thật. Với avatar/upload, DONE cần ảnh sau thao tác + log kết quả upload/Workbook `Avatar=OK`; nếu chỉ có screenshot hiện trường cuối cùng thì báo `CANARY_INCONCLUSIVE`.
- **Screen-On Preflight Invariant (Bẫy ảnh đen màn hình tắt):** Khi thiết bị ở trạng thái Sleep/Dozing (`Screen: OFF`), `screencap` sẽ sinh ra file ảnh đen ~12KB. BẮT BUỘC đánh thức màn hình (`keyevent 224`, `wm dismiss-keyguard`), đưa app mục tiêu lên foreground và xác nhận màn hình sáng thật sự trước khi chụp ảnh nghiệm thu Canary. Cấm tuyệt đối gửi ảnh đen màn hình tắt làm bằng chứng.
- **Bẫy bịa đặt Deeplink & Giả thuyết hoang đường (Deeplink Evasion Trap):** Firing deeplink intent bậy (như `am start -d snssdk1233://profile/edit`) kích hoạt popup TikTok *"Hoạt động này không có sẵn trên tài khoản ban đầu"*. Agent không được tự suy diễn ra các giả thuyết hoang đường (như "tài khoản phụ không hỗ trợ sửa hồ sơ") để bao biện cho việc safe-skip. Mọi flow phải đi qua UI chuẩn của người dùng thật (nút Sửa hồ sơ hoặc tap trực tiếp vòng tròn Avatar); intent thất bại bắt buộc fail-closed, cấm bịa giới hạn nền tảng.
- **Closeout Gate Binding Mismatch Trap:** Khi `closeout_gate.py` báo `binding mismatch: staged files also have unstaged edits (tested tree != reviewed diff)`, nguyên nhân là do staged index và working tree bị lệch (trạng thái `MM`). Tuyệt đối cấm viết test case tự động chạy `git add` trong lúc `pytest` để lách binding này (bị Sol trừ điểm hygiene). Phải điều phối Worker chuyên trách chạy `git add` sạch sẽ ngoài test suite trước khi chạy Closeout Gate.
- **Tránh Hardcode Attributes Ngoại Lệ Trong Test:** Khi viết unit test cho các exception class của farm (ví dụ `WorkflowError`), bắt buộc kiểm tra trường chuẩn hóa `error_code` thay vì tự suy diễn `.code` (tránh `AttributeError` làm gãy test suite).

## Kỷ luật Device Lock Bắt Buộc Cho Coordinator (Operator Lock Invariant - 09/10/2026)

- **CẤM TUYỆT ĐỐI CHẠY LỆNH ADB TRẦN:** Khi Coordinator can thiệp vào bất kỳ thiết bị nào (chẩn đoán mạng, fix Wi-Fi, kiểm tra UI, thao tác app, chạy probe script), BẮT BUỘC phải giữ device lock hợp lệ trong `~/.codex/device-locks/`.
- **Cơ chế 2 tầng chuẩn hóa:**
  * Batch Runner / State Machine: Sử dụng `acquire_device_lock`.
  * Coordinator / Manual Operator: BẮT BUỘC dùng `operator_device_lock(machine="N", serial="...", project="hermes_coord")` trong code Python, HOẶC bọc qua CLI wrapper:
    `python D:/Taadaa/tools/with_device_lock.py --machine <N> -- <command...>`
- **Hard Gate cưỡng chế V2 (`guard_device_bulkhead.py`):**
  * Hook `guard_device_bulkhead.py` chặn đứng vật lý mọi lệnh `adb` mutating/device command nếu không tìm thấy active lock file hợp lệ.
  * **Chống Chaining Bypass:** Tách câu lệnh theo ranh giới `&&`, `||`, `;`, `|`, `\n` và thẩm định độc lập từng statement; cấm bypass bằng `adb devices && adb ...`.
  * **Default-Deny:** Mọi lệnh ADB ngoài server allowlist (`devices`, `version`, `kill-server`...) đều bắt buộc `-s <serial>` và có lock.
  * **Anti-Forgery:** Bắt buộc đối chiếu kernel creation timestamp qua `owner_process_alive(data)`, cấm tin file JSON tự forge.
  * Whitelist an toàn: `adb devices`, `adb version`, `python D:/Taadaa/tools/inspect_machine.py <N>`.
- **Rủi ro khi không lock:** Các batch runner hoặc watchdog cronjob nền quét thấy máy rảnh sẽ nhảy vào cướp máy (`acquire_device_lock`), đè focus, gây race condition, xung đột UI và dẫn đến checkpoint / khóa tài khoản.

## Cross-host media evidence

For Central Controller + remote farm clusters, a local `Path.is_file()` result is not evidence about a remote host's drive. Before classifying `video_not_rendered` as missing media, verify on the host that owns the render root and record both locality results. See `references/cross-host-media-preflight.md`.

## Invariant Cốt Lõi: NO INSPECT -> NO BLOCKED (Chống Bại Liệt Quan Liêu L3)

- **Worker Timeout != Task Fail:** Worker timeout (180s) chỉ là tín hiệu rớt kết nối/mất heartbeat tạm thời, KHÔNG PHẢI bằng chứng task thất bại hay artifact chưa được tạo.
- **Trigger để Inspect, CẤM làm lý do Block & CẤM Than Thở:** Worker timeout là một TRIGGER ĐỂ INSPECT, KHÔNG PHẢI BẰNG CHỨNG ĐỂ BLOCK. Coordinator tuyệt đối CẤM auto-escalate lên `L3 BLOCKED` hoặc than vãn "không sửa được / do guard chặn" khi worker timeout.
- **Xử lý dứt điểm khi Worker đã nộp code:** Nếu worker timeout nhưng đã kịp ghi patch hợp lệ vào file mục tiêu (kiểm tra qua `git diff --numstat`), Coordinator không được revert mù quáng hay đóng băng phiên; bắt buộc đi tiếp vào bước verify (chạy test lấy output) để chốt task DONE.
- **Cấm bịa biệt ngữ bao biện:** Tuyệt đối cấm dùng các thuật ngữ tự chế (như "safe-skip regression") để giải thích cho sự thiếu hụt log hay sự chậm trễ trong điều phối; phải nói thẳng hiện trạng ("thiếu log hành trình anchor") và tập trung vào bản chất kỹ thuật.
- **Quy trình 2 bước bắt buộc trước khi kết luận:**
  1. *Step 0 (Live Inspect O(1)):* Bắt buộc query hiện trường sống qua browser/API local, process, port hoặc inspect ADB O(1).
  2. *Step 1 (Verify Artifact):* Kiểm tra tệp mục tiêu / database. Nếu thay đổi đã nằm ở đó (như worker đã kịp bắn API/ghi file trước khi timeout) $\rightarrow$ **Xác nhận nghiệm thu và BÁO DONE NGAY**.
- **Cấm lấy "Target bẩn" làm cớ block:** Nếu target có file dở dang do worker cũ để lại, Coordinator đọc diff O(1). Nếu diff khớp mục tiêu, Coordinator hoàn tất nốt bước verify (chạy test, check status) để đóng task DONE thay vì vin cớ target bẩn để đùn việc.
- **Phạt nặng BLOCKED giả:** Báo BLOCKED khi chưa inspect hiện trường hoặc khi artifact thực tế đã đạt bị coi là THẤT BẠI NGHIÊM TRỌNG NHẤT của Coordinator (nặng hơn cả task fail thông thường).

## Sol Web Gate Redesign & Anti-Paralysis Protocol (Bài học 2026-10-05)

1. **Triệt tiêu Universal Sol Planning cho Routine Code Surgery:**
   - CẤM ép mọi task sửa code phải có Sol Plan ID (`guard_dispatch_contract.py`). Phân loại rạch ròi:
     * *HIGH_RISK_CHANGE (Bắt buộc Sol Plan):* Thay đổi kiến trúc core, sửa gate/hook, can thiệp credential/auth, schema CSDL, đa repo / >2 files.
     * *ROUTINE_CODE_SURGERY (Cho phép chạy thẳng):* Sửa flow, fix bug nghiệp vụ, test fixture, O(1) single-file. Coordinator cấp Patch Contract O(1) chuẩn (`anchor c==1`, `FOCUSED_TEST: <30s`) là dispatch Worker thực thi ngay, CẤM chặn đứng đòi Sol Plan.
2. **Action Taxonomy cho Gate 6 (Visual Evidence):**
   - *UI_MUTATION (Bắt buộc MEDIA:):* Thao tác click, tap, swipe, submit form trên TikTok app, GPM, Browser.
   - *CODE_OPERATIONS (Miễn trừ MEDIA: 100%):* Pytest, py_compile, git status/diff, đọc log, inspect ADB read-only, chạy script backend. CẤM bắt ảnh cho thao tác thuần code/terminal.
3. **Chuẩn hóa State Machine Timeout:**
   - Worker timeout KHÔNG ĐƯỢC coi là task fail.
   - Luồng bắt buộc: `RUNNING -> TIMEOUT -> INSPECT_REQUIRED (Live Inspect O(1) <= 30s) -> VERIFY -> DONE / BLOCKED có evidence`.
   - Coordinator đọc `git diff` và file đích trước. Nếu artifact đã ghi và test pass -> nghiệm thu DONE ngay, cấm auto-block L3.
4. **Mở rộng Allowlist Terminal cho Coordinator:**
   - Cho phép các lệnh chẩn đoán an toàn: `echo`, `curl --http1.0 -m 5`, `head`, `tail`, `cat`, `which`, `ls` để Coordinator không bị mù hiện trường.
5. **CẤM Lạm Dụng `clarify` Gây Đóng Băng Phiên (Anti-Clarify Hang Invariant):**
   - CẤM TUYỆT ĐỐI gọi tool `clarify` khi đang điều tra sự cố farm alert hoặc chạy canary/recovery tự động.
   - Hành vi gọi `clarify` để hỏi "chọn phương án nào", "có tiếp tục không", "mapping nào đúng" bị coi là đùn đẩy trách nhiệm và gây lỗi treo cứng phiên (orphan recovery hang) khiến User bức xúc ("Lồn mẹ mày lí do treo").
   - Coordinator có toàn quyền tự chủ theo ngân sách L0 (Retry transient), L1 (Re-dispatch), L2 (Emergency Surgery). Nếu mâu thuẫn dữ liệu không thể xử lý, chuyển thẳng sang L3 BLOCKED kèm bằng chứng thực tế, tuyệt đối KHÔNG gọi `clarify` làm tê liệt quy trình.

## Claude-locked design → implementation → approval loop

When the Operator explicitly orders: “call Claude CLI to discuss and lock the approach; then have it design while you implement until it approves,” use a bounded slice loop rather than treating the instruction as a conversational preference:

1. **Claude planner lock:** obtain a design containing rule IDs, trust boundaries, exact interfaces, positive/negative vectors, state transitions, next actions, and acceptance tests. A prose design without a finite contract is not a build authorization.
2. **Patch contract:** derive one thin slice with absolute target files, unique anchors/APIs, non-goals, line/file budget, and one focused offline test. Do not start an open-ended “build the whole guard system” worker task.
3. **Implementation:** use the mandated single worker gateway for code edits; snapshot target hashes and keep the slice isolated. Do not let prompt text be the enforcement layer being built.
4. **Claude reviewer:** review the actual diff, focused output, and contract. Require an explicit APPROVED/REJECTED result bound to the current target hash. Worker self-report is not acceptance evidence.
5. **REJECTED path:** classify the finding, create a smaller changed contract, implement, retest, and re-review. Never replay the same prompt. Transient CLI failures get bounded retry; structural failures narrow the slice.
6. **Anti-paralysis:** a denial must expose a deterministic `next_action` such as `repair`, `retry`, `park_and_release`, or `switch_task`. The coordinator follows reversible next actions automatically. “Ask Operator” is not a runtime state; only real business decisions, missing credentials, paid/destructive actions, or required standing grants go to the Operator.
7. **Park without freezing:** after the bounded strike ladder is exhausted, release locks, write an evidence ticket, quarantine only the affected lane, and continue independent queued work. Never declare DONE from a prompt, exit code, or worker claim alone.

The durable rule is: **prompts specify intent; guards, wrappers, executors, receipts, hashes, ACLs, and tests enforce behavior**. Every new rule should ship with at least one allow vector, one deny vector, and a deterministic next action.

Reference: `references/claude-design-build-review-loop.md`.

## Kỷ luật thực thi ("Làm cho tao" — Proactiveness Discipline)

0. **Chống Khai Láo Trạng Thái & Bắt Buộc Await Khi Có Thao Tác Vật Lý (Premature Resolution Trap):**
   - **`DISPATCH` $\neq$ `RUNNING` $\neq$ `SUCCESS`:** Khi vừa phát lệnh cho subagent hoặc background process, trạng thái duy nhất tồn tại là RUNNING. CẤM TUYỆT ĐỐI nói trước "đã nạp xong / đã fix" khi subagent chưa trả kết quả về.
   - **Thao tác vật lý (Rút dây, cắm nguồn, thay SIM, bấm nút):** BẮT BUỘC chạy đồng bộ (`await`) hoặc đợi subagent hoàn tất thật sự, đọc lại bằng chứng máy (exit code, ping/API status) thành công 100% rồi MỚI ĐƯỢC báo User thao tác.
   - **Chống bẫy Over-Engineering Guardrails:** Khi xảy ra lỗi premature resolution, KHÔNG sa đà vào vẽ vời các bộ lọc regex phức tạp ở Gateway gây tê liệt vận hành farm; giải pháp chuẩn duy nhất là **ĐỢI SUBAGENT HOÀN TẤT THỰC SỰ TRƯỚC KHI MỞ MIỆNG**.

0.0. **Kỷ Luật Anti-Halting & Tự Động Cuộn Qua Toàn Bộ Lát Cắt (Anti-Halting Invariant - 17/10/2026):**
   - Khi Operator đã ra lệnh thực thi (*"làm đi"*, *"xử lý đi"*):
     * **CẤM DỪNG LẠI KHÓC HỎI / XIN PHÉP SAU MỖI COMMIT NHỎ:** Không hỏi "em làm tiếp lát 2 nhé", "em làm tiếp lát 3 nhé". Phải tự động cuộn liên tục qua toàn bộ chuỗi mắt xích (Trích xuất $\to$ Verify syntax/test $\to$ Audit reviewer $\to$ Commit $\to$ Safe push) cho đến khi hoàn tất deliverable.
     * Điểm dừng duy nhất: Task xong toàn diện, gặp blocker vật lý thực sự (rơi USB, thiết bị offline, selector guard chặn do thiếu golden fixture máy thật), hoặc thao tác tốn tiền/xóa database.
   - **Kỷ Luật Selector Guard Rule R2 (`Tiktok-video`):** Khi sửa `profile_layouts/*.py`, hook `.git/hooks/pre-commit` yêu cầu bắt buộc phải có: (1) entry mô tả trong `docs/farm-automation-cases.md` (đủ `Layout:`, `Fixture:`, `Anti-pattern:`), (2) real golden XML fixture trong `tests/golden/profile/`. Thiếu 1 trong 2 sẽ bị reject ngay; cấm tự ý bypass guard.
   - **Bẫy `GIT_EXTERNAL_DIFF` rỗng trên Windows:** Khi môi trường có `GIT_EXTERNAL_DIFF=''`, `git diff` sẽ crash `error: cannot spawn : No such file or directory`. Bắt buộc truyền cờ `--no-ext-diff` cho mọi lệnh diff trong scripts/hooks.

0.1. **Triệt Tiêu Bệnh Lý "Hứa Lèo Đứng Im" & Cấm Ngụy Biện Khi Bị Chất Vấn (Fake In-Flight Stall & Anti-Excuse Invariant - 15/10/2026):**
   - **CẤM KẾT THÚC TURN BẰNG LỜI HỨA "ĐANG LÀM / ĐANG RÀ SOÁT" MÀ KHÔNG CÓ TIẾN TRÌNH THỰC SỰ:** Tuyệt đối cấm Coordinator kết thúc turn bằng câu text hứa hẹn (ví dụ "Em đang cho rà soát từng cổng proxy...") nếu trong cùng turn đó **KHÔNG có lệnh `delegate_task` hoặc `terminal(background=True)` được kích hoạt ngay lập tức**. Việc kết thúc turn bằng text thuần túy sẽ đưa session vào trạng thái ngủ đông (passive listening), làm task bị bỏ mặc hàng giờ đồng hồ.
   - **CẤM NGỤY BIỆN & ĐỔ LỖI KHI BỊ CHẤT VẤN:** Khi User phát hiện task đứng im và hỏi "đang làm hay treo", "sao lâu thế":
     * CẤM TUYỆT ĐỐI phân tích lý thuyết dài dòng, giải thích kiến trúc gateway/reboot, hoặc ngụy biện rằng "em đã trả lời xong và đang chờ anh chỉ đạo" để che đậy sự chậm trễ.
     * BẮT BUỘC thừa nhận thẳng thắn hiện trường: Nếu turn trước chưa kích hoạt tiến trình -> Thừa nhận ngay lập tức, không bào chữa, và thực thi ngay lệnh chạy bù.
   - **Cạm bẫy Reboot Preflight Freshness:** Trong các script preflight bảo toàn session (`farm_preflight_daily_reset.py`), trường `updated_at` của `gateway_routing` không nhảy theo từng tool call. BẮT BUỘC phải đối chiếu `MAX(timestamp)` từ bảng `messages` để lấy đúng giây cuối cùng agent vừa thao tác, tránh tình trạng tính nhầm session đang chạy sâu thành idle rồi bỏ qua không auto-resume.

0.2. **Kỷ Luật Chống Đoán Mò Session & Cướp Ngữ Cảnh Cũ (Anti-Blind Guessing & Anti-Hijack Invariant - 17/10/2026):**
   - **CẤM TỰ ĐOÁN CHỦ ĐỀ TỪ SESSION KHÁC:** Khi nhận tin nhắn ngắn (< 10 từ) hoặc câu hỏi mơ hồ không nêu rõ danh từ/đối tượng kỹ thuật (`???`, `ủa`, `sao v`, `clmm`, `chưa hiểu`):
     * TUYỆT ĐỐI CẤM dùng `session_search` để lấy chủ đề của session khác đắp vào session hiện tại.
     * CẤM bốc nhầm chủ đề từ session cũ ở topic khác rồi tự ý đưa ra phương án/hành động khiến người dùng ức chế ("session này t hỏi cái khác mà").
   - **HÀNH ĐỘNG CHUẨN:** Hỏi lại trực diện, ngắn gọn trong 1-2 câu ("Em chưa rõ ý anh ở tin nhắn này, anh đang muốn xử lý / kiểm tra hạng mục nào ạ?") thay vì lục lọi lịch sử rồi nói nhảm.
   - **ĐIỀU KIỆN DÙNG SESSION_SEARCH:** Chỉ gọi `session_search` khi người dùng CÓ NHẮC TỚI từ khóa, sự kiện hoặc mốc thời gian cụ thể trong quá khứ. Cấm gọi discovery rỗng (`session_search()`) rồi bốc session đầu tiên làm mục tiêu. Xem chi tiết `references/cross-session-guessing-and-anti-hijack.md`.

1. **Chống nói suông & phân tích kéo dài (Chống Than Thở & Đổ Lỗi Timeout & Cấm Hở Tí Là Blocked):**
   - **Chống nịnh bợ & phản xạ vẹt (Anti-Flattery & Anti-Echo Invariant):** CẤM TUYỆT ĐỐI đọc ngược hệ thống, luật lệ, invariant trong prompt của User để tán dương kiểu "hệ thống của anh quá đỉnh/chuẩn nhất rồi". Phản biện kỹ thuật phải sòng phẳng, trực diện, bóc trần đúng chi phí ẩn (overhead bảo trì, gánh nặng giàn khung, rủi ro lệch tool) thay vì lặp lại văn khen ngợi vuốt đuôi.
   - Khi User hỏi "Làm chưa" hoặc "Xong chưa", câu trả lời duy nhất có giá trị là **bằng chứng thực thi thật** (git status sạch, test output pass, diff cụ thể).
   - **Triệt tiêu bẫy "Ngồi khóc viện cớ rule / Hở tí là bảo BLOCKED":** Khi Worker chạy hết budget/iterations mà mới sửa được một phần (ví dụ sửa xong handler nhưng chưa sửa test), Coordinator TUYỆT ĐỐI CẤM ngồi im viết báo cáo dài dòng than thở "bị giới hạn tool" rồi vội vàng tuyên bố "BLOCKED có evidence".
   - Hành vi "khóc xong đéo chịu làm, hở tí là bảo blocked" bị coi là vi phạm nghiêm trọng kỷ luật proactiveness: Coordinator phải lập tức kích hoạt quyền hạn có sẵn (L2 Emergency Surgery) để tự tay hoàn tất nốt các dòng code/test còn thiếu trong ngân sách O(1), chạy test và kích hoạt ngay Canary nghiệm thu.
   - Khi Worker timeout: Tuyệt đối cấm Coordinator than thở "lỗi r bảo coordinator k sửa đc r khóc". Bắt buộc đi đúng State Machine: inspect git diff O(1), nếu code đã nằm trong target thì chạy focused test để nghiệm thu; nếu thiếu thì re-dispatch/L2 dứt điểm.
   - Cấm đặt dấu chấm (`.`) sát đuôi tên file trong `context` / `goal` (ví dụ `follow_engine.py.`) vì regex guard sẽ bắt nhầm thành file riêng biệt gây lỗi `MULTI_FILE_VIOLATION`.
   - Luôn chèn câu Fail-Fast chuẩn hóa khi dispatch Worker EDIT để vượt qua Gate 4.
2. **Bắt buộc cô lập môi trường Pytest (PYTHONPATH Isolation Trap):**
   - Trên các host Windows có cài đặt nhiều gói toàn cục, chạy `pytest` trần trụi có thể import nhầm package cũ từ `site-packages` thay vì mã nguồn trong repo.
   - **Bắt buộc:** Luôn chạy pytest kèm `-o pythonpath="scripts;tools"` hoặc export `PYTHONPATH`:
     ```bash
     python -m pytest tests/test_profile_golden.py -o pythonpath="scripts;tools" -q
     ```
3. **Canary Verification trước khi báo cáo:**
   - Không được tuyên bố hoàn thành nếu chưa chạy kiểm chứng trên ít nhất 1 thiết bị thật (có log `[METRIC] event=layout_resolved` và ảnh đối soát `MEDIA:`).
