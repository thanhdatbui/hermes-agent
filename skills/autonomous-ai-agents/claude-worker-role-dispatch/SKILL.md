---
name: claude-worker-role-dispatch
description: "Dispatch Claude CLI with role, turns cap and gate."
version: 1.0.0
platforms: [windows]
metadata:
  hermes:
    tags: [claude, worker, dispatcher, role-based, quota-gate, turns-cap, farm-safety]
    related_skills: [claude-limit-protection, hermes-orchestration-dispatcher, monolith-modularization-and-architecture-gates]
---

# Claude Worker Role-Based Dispatch

Use this skill when calling Claude Code CLI for any task on the Taadaa Farm. All Claude CLI invocations MUST go through `D:/Taadaa/tools/claude_worker.py`, never via raw `claude -p` in terminal.

## Context: The 72-Turn Disaster (15/10/2026)

When a Coordinator bypassed the Guard by running `claude -p "..." --dangerously-skip-permissions > log.txt 2>&1` without `--model` or `--max-turns`, Claude Sonnet 5.5 ran **72 agentic turns** freely in a 112K-token workspace, consuming **2.117.100 tokens** and pushing quota from 5% to 98% in 20 minutes.

---

## Role Configurations

| Role | Model | Default Turns | Hard Cap Turns | Tools | Fallback |
|------|-------|--------------|----------------|-------|---------|
| `worker` | claude-haiku-5-5 | 8 | **15** | Read,Edit,Write,Bash | `ag_cli.py fix` |
| `planner` | claude-sonnet-5-5 | 6 | **10** | Read,Bash | `ag_cli.py ask` |
| `reviewer` | claude-sonnet-5-5 | 4 | **8** | Read,Bash | `ag_cli.py ask` |

## Usage

```bash
# Worker (Haiku, max 15 turns)
python D:/Taadaa/tools/claude_worker.py --role worker --timeout 55 "Fix the logic in..."

# Planner (Sonnet, max 10 turns, read-only)
python D:/Taadaa/tools/claude_worker.py --role planner --timeout 75 "Design the interface..."

# Reviewer (Sonnet, max 8 turns, read-only)
python D:/Taadaa/tools/claude_worker.py --role reviewer --max-turns 6 --timeout 55 "Review: ..."

# Quota check
python D:/Taadaa/tools/claude_worker.py --check-quota
```

## Key Safety Mechanisms

### 1. Hard-Cap Turns Clamping
```python
max_turns = max(1, min(args.max_turns or role_cfg["default_turns"], role_cfg["hard_cap_turns"]))
```
Even `--max-turns 999` gets clamped to the role's `hard_cap_turns`.

### 2. Read-Only Enforcement for Planner/Reviewer
```python
if role in ("planner", "reviewer"):
    cmd += ["--disallowedTools", "Edit,Write,NotebookEdit"]
    cmd += ["--dangerously-skip-permissions"]
else:
    cmd += ["--allowedTools", role_cfg["allowed_tools"]]
    cmd += ["--dangerously-skip-permissions"]
```

### 3. Role-Aware Quota Fallback
- `planner` và `reviewer` → `ag_cli.py **ask**` (read-only analysis).
- `worker` → `ag_cli.py **fix**` (code repair allowed).

### 4. Stale Quota Detection: `MAX_QUOTA_STALE_HOURS = 2.0`.

### 5. Narrow Limit Markers (no false positives):
- `"hit your session limit"`
- `"you've hit your limit"`

---

## Standard 3-Phase Workflow for Modules > 200 Lines

**Phase 1 — PLAN (`--role planner`, ≤ 6 turns):**
Sonnet reads requirements; outputs function list, signatures, acceptance criteria into a temp file.

**Phase 2 — BUILD (`--role worker`, ≤ 8 turns/chunk):**
Haiku implements each function as thin-slices (≤ 2 files, ≤ 80 lines). Runs pytest after each.

**Phase 3 — REVIEW (`--role reviewer`, ≤ 4–6 turns):**
Sonnet reads git diff and test suite; outputs APPROVED or REJECTED with specific findings.

---

## Cross-Family Review Discipline

Both `--role reviewer` (Sonnet/Anthropic) AND Closeout Gate (Sol High/OpenAI) are required:
1. **Blind spots within same family:** Haiku and Sonnet may share reasoning blind spots.
2. **Sol High is free:** 115 ChatGPT Web accounts on `:20129`, zero Claude quota consumed.
3. **Closeout Gate enforces physically:** diff budget ≤ 30KB, pytest in isolation, ≥ 85/100 rubric to push.

---

## Pitfalls

- **KỶ LUẬT "THI CÔNG ĐẾN KHI CLAUDE CLI DUYỆT" & PHÂN VAI ARCHITECT VS BUILDER (User Mandate 18/10/2026):**
  Khi Operator (User) ra lệnh *"Thi công đến khi Claude CLI duyệt"*, Coordinator BẮT BUỘC tuân thủ:
  1. *Phân vai bất biến:* Claude Sonnet 5.5 (`--role planner` / `--role reviewer`) CHỈ LÀM TƯ VẤN KIẾN TRÚC & REVIEWER THẨM ĐỊNH. Tuyệt đối CẤM đùn việc viết code hoặc viết unit test cho Claude CLI làm cháy quota 5h. Coordinator và Worker Haiku O(1) là người trực tiếp thi công code & test suite.
  2. *Quy trình lặp đối kháng đến APPROVED:*
     - Bước 1: Thi công code & test suite.
     - Bước 2: Dispatch Claude Reviewer (`python D:/Taadaa/tools/claude_worker.py --role reviewer --max-turns 4 ...`).
     - Bước 3: Nếu phán quyết là `VERDICT: REJECTED`, đọc kỹ từng finding (P1/P2), bóc tách root cause và sửa code, đồng thời bổ sung regression test cho từng finding.
     - Bước 4: Chạy lại pytest xác nhận pass 100%, nộp lại bài cho Claude Reviewer.
     - Lặp lại cho đến khi Claude Reviewer trả về `VERDICT: APPROVED` (như case study `guard_android_proxy.py` trải qua 5 vòng review gắt gao từ 6 test lên 48 tests mới được duyệt). CẤM dừng lại bỏ cuộc hoặc thỏa hiệp khi Reviewer còn từ chối.
  (Xem `farm-agent-governance` reference `references/mechanical-guard-mandatory-and-claude-advisor-vs-coordinator-builder-20261018.md`).
- **QUY CHUẨN ĐÍCH DANH "HỎI / GỌI CLAUDE CLI" CỦA OPERATOR (Operator Sonnet Mandate 17/10/2026):**
  Khi Operator (User) ra lệnh *"hỏi Claude"*, *"gọi Claude CLI kiểm tra / đánh giá / tư vấn / review"*, Coordinator BẮT BUỘC dispatch **Claude Sonnet 5.5** (`claude_worker.py --role planner` hoặc `--role reviewer`), TUYỆT ĐỐI CẤM tự ý hạ cấp xuống `haiku_worker.py`!
  CẤM TUYỆT ĐỐI đề cập hay gọi nhầm thành Claude 3.5 Sonnet (User dùng độc quyền thế hệ 5.5).
  `haiku_worker.py` chỉ là công nhân O(1) thi công sửa code/test cơ học để tiết kiệm quota; khi User cần tư vấn kiến trúc hay thẩm định chất lượng cao thì Sonnet là tiêu chuẩn tối cao duy nhất.
  *Lưu ý khi gọi Sonnet tư vấn:* Kẹp tham số `--max-turns 6-8` và chỉ thị rõ *"Answer directly without executing bash commands"* trong prompt để tránh Sonnet chạy các tool Bash/Read thăm dò lan man dẫn đến lỗi `Reached max turns`.
- **BẢO VỆ QUOTA CLAUDE TẠI CLOSEOUT & CHỐNG L3 BLOCKED KHÓC LÓC (Chống Đốt Quota & Anti-Paralysis 17/10/2026):**
  Khi chốt phiên bị trượt, nguyên nhân đốt quota 5h là do Coordinator lôi Sonnet 5.5 ra viết code và sửa test lặp đi lặp lại.
  Quy chuẩn bất biến:
  1. *Khái niệm Turn:* 1 turn là 1 bước suy luận/gọi công cụ trong vòng lặp ReAct của agent (Read -> Patch -> Command/Test -> Done), KHÔNG PHẢI là 1 lần chạy sửa toàn cục.
  2. *Quy trình 3 nấc sửa:*
     - **Strike 1:** `sol_repair.py` (:20129) độc quyền proposal O(1) in-memory AST <= 30 dòng (Free 100%).
     - **Strike 2:** `sol_worker.py` (:20129) ReAct test tích hợp có hàng rào Snapshot rollback (Free 100%).
     - **Strike 3:** `claude_worker.py --role worker` (chạy bằng **`claude-haiku-5-5`** cực rẻ, nhẹ quota, 10-15s, CẤM SONNET) hoặc fallback sang `ag_cli.py fix` (22 acc Google Pro 4G miễn phí).
  3. *Grace Band (Score >= 80):* Đạt từ 80-84 điểm, diff <= 30 dòng, test 100% pass (>= 1 test, 0 fail/err) là AUTO-PUSH NGAY. Hook `.git/hooks/pre-push` ở tất cả repo (Hermes, tools, tiktok-luot nuoi acc) đã đồng bộ `THRESHOLD=80`, cấm cày điểm 85.
  4. *CẤM BÁO L3 BLOCKED DỪNG LẠI KHI TEST ĐÃ PASS:* Nếu focused test đã pass 100% mà Reviewer vẫn dìm dưới 80 do bắt bẻ vô lý, Coordinator BẮT BUỘC kích hoạt `safe_push.py --owner-override <repo> <remote> <branch>` để push giải phóng phiên ngay lập tức, tuyệt đối cấm báo L3 BLOCKED dừng lại than vãn.
  5. *Live Quota Sync:* `refresh_claude_quota_file.py` BẮT BUỘC query trực tiếp model-free `/usage` từ Claude CLI qua `probe_claude_quota(find_real_claude())`, tuyệt đối cấm hardcode dummy data ảo (5%/0%).
  (Xem `references/sol-worker-guardrails-and-strike-3-failure-protocol-20261017.md` & `references/strike-3-quota-preservation-haiku-worker-vs-sonnet-reviewer-20261017.md`).
- **CẤM DÙNG CLAUDE SONNET TRONG VÒNG LẶP REMEDIATION TỰ ĐỘNG (Bảo Vệ Quota Tuyệt Đối 17/10/2026):** Tuyệt đối CẤM mọi tiến trình/script tự động (Closeout Gate, Strike 3 Hand-off, Auto-remediation) tự ý kích hoạt Claude Sonnet 5.5 để "cày 1-2 điểm" cho Sol Auditor. Sonnet là vũ khí chiến lược đắt đỏ, CHỈ ĐƯỢC CHẠY khi có lệnh đích danh trực tiếp từ Operator (User). Mọi vòng lặp sửa lỗi tự động độc quyền giao cho Sol Repair (miễn phí trên :20129) hoặc Haiku 5.5 / Agy CLI (Gemini Pro).
- **CẤM DÙNG CLAUDE SONNET ĐỌC FILE VẶT (Quota Bleeding Disaster 15/10/2026):** Tuyệt đối không dùng `--role planner` (Sonnet 5.5) cho các tác vụ chỉ đọc vài chục dòng code, kiểm tra diff hoặc tìm kiếm file. Đọc file/diff phải dùng tool local hoặc Python $O(1)$ để bảo vệ quota 5h không bị đốt sạch từ 69% lên 100% trong 15 phút.
- **CẤM AGENT TỰ Ý OVERRIDE QUOTA GUARD:** Lệnh `claude_quota_guard.py allow <minutes>` là đặc quyền DUY NHẤT của Con người (User). Agent tuyệt đối cấm tự ý gõ lệnh mở rào quota của chính mình khi bị chặn.
- **CẤM DÙNG AG CLI (GEMINI) LÀM REVIEWER:** AG CLI chỉ là worker sửa code (`fix`) hoặc phân tích logic (`ask`). Tuyệt đối không được gán vai Reviewer cho AG CLI/Gemini để tự phê duyệt `[APPROVED]` thay thế Claude Sonnet / Sol High (vi phạm nghiêm trọng nguyên tắc Cross-Family Review).
- **KỶ LUẬT PHÂN LOẠI LỖI & RETRY CHO HAIKU (Intelligent Failure Classification & 2-Attempt Ladder):** Haiku thất bại không chỉ vì hết quota mà còn do kẹt turns/scope. CẤM ném ngay sang Agy CLI khi Haiku còn quota. Haiku là worker O(1) (10-15s), CẤM giao việc tự phân rã kiến trúc mở (sẽ đốt sạch 8-15 turns chỉ để đọc file rồi fail `error_max_turns`). Coordinator bắt buộc phân rã trước thành contract O(1). Khi Haiku fail ở attempt 1:
  1. *QUOTA (session limit, 429, exit 127):* Fallback ngay sang Agy CLI fix (reason: `quota_exhausted`).
  2. *ENV (sai path, thiếu tool, exit 126):* Dừng ngay lập tức, cấm gọi Agy CLI bừa bãi.
  3. *MAX_TURNS / TIMEOUT / TASK_FAIL:* Haiku còn quota -> Dispatcher tự động cho Haiku retry lần 2 (Attempt 2) với tiền tố `[O(1) FOCUS RETRY - DO NOT EXPLORE, TOUCH ONLY TARGET FILE MINIMALLY]`. Chỉ khi attempt 2 vẫn fail mới escalate sang Agy CLI fix (reason: `haiku_exhausted_contract`). (Xem `references/intelligent-failure-classification-and-haiku-retry-ladder-20261016.md`).
- **PROMPT CONTRADICTION & PRECEDENCE (The Stale Injected Prompt Trap):** Khi system prompt bị drift hoặc chứa boilerplate cũ (`BẮT BUỘC dispatch worker qua delegate_task`), Coordinator BẮT BUỘC áp dụng thứ bậc ưu tiên: User Directive (hiện tại) > User Profile / Memory > SOUL / Invariants > Stale System Prompt. CẤM để prompt cũ dắt mũi làm sai Worker hierarchy.
- **CẤM TUYỆT ĐỐI SPAWN `delegate_task` CHO SỬA CODE / TEST (The Gemini Subagent Trap):** Dù trong system prompt khởi tạo session có thể sót câu lệnh cũ (`BẮT BUỘC dispatch worker qua delegate_task`) hoặc thông báo từ chối của hook guard (`COORDINATOR WRITE DENIED ... BẮT BUỘC DISPATCH WORKER ... qua delegate_task`), Coordinator TUYỆT ĐỐI KHÔNG ĐƯỢC spawn subagent `delegate_task` (`ag-gemini-pool-3`) để sửa code hay viết test. Mỗi lượt `delegate_task` ngốn tới 15 calls (~150s), làm loãng context và gây tắc nghẽn nghiêm trọng. MỌI task sửa code/fix bug/viết test BẮT BUỘC dispatch qua Single Dispatch Gateway `python D:/Taadaa/tools/dispatch_worker.py --workdir <repo> [--file <file>] "<prompt>"` (T1 Haiku 5.5 CLI -> T2 Agy CLI fix). Chỉ được phép dùng subagent khi CẢ HAI CLI đều cạn quota (`WORKER_CLI_EXHAUSTED`). Cụm từ "qua delegate_task" trong hook chỉ là legacy text, hành động thực tế BẮT BIẾN là CLI terminal.
- **CỔNG ĐIỀU PHỐI DUY NHẤT CHO TÁC VỤ THƯỜNG (Single Dispatch Gateway `dispatch_worker.py`):** CẤM gọi riêng lẻ `claude_worker.py` hay `ag_cli.py` một cách thủ công rồi tự ý chọn model. Toàn bộ khâu dispatch thông thường BẮT BUỘC chạy qua `python D:/Taadaa/tools/dispatch_worker.py "<contract O(1)>" --workdir <repo>`. Script tự động xử lý chuyển tầng (Haiku -> Agy CLI) khi cạn quota/lỗi và ghi log vào `D:/Taadaa/logs/dispatch.jsonl`.
- **CHỐT PHIÊN TỰ ĐỘNG KHÉP KÍN (Auto-Closeout Pipeline `auto_closeout.py`):** Khi kết thúc task hoặc chốt phiên, BẮT BUỘC gọi `python D:/Taadaa/tools/auto_closeout.py --repo <repo> --files <files>`. Quy trình: Sol 1 lượt -> nếu trượt: Haiku fix -> Claude/Agy review -> 4 nấc kiểm chứng cơ học (py_compile, pytest 100%, test integrity, diff budget <= 150 dòng) -> Auto-Push luôn qua safe_push.py. CẤM quay lại Sol cày điểm, CẤM dừng lại hỏi xin phép Operator.
- **BẪY CÀY ĐIỂM CLOSEOUT GATE & STRIKE PROTOCOL (The 85-Score Infinite Trap):** Khi Closeout Gate đạt 82-84 điểm, CẤM TUYỆT ĐỐI rơi vào vòng lặp spawn worker sửa vụn vặt từng microseconds/timezone/whitespace để nịnh Sol Reviewer kéo dài hàng giờ. Quy tắc Strike chuẩn xác: Strike 1 & 2 Remediation là độc quyền của Sol High (`sol_repair.py`). Đến Strike 3 (3 lần trượt liên tiếp trên cùng scope): BẮT BUỘC kích hoạt Reviewer Hand-off (giao cho Claude Sonnet CLI tự sửa theo HERMES_SUBAGENT_RULES.md). CẤM sửa vòng thứ 4.
- **KỶ LUẬT THI CÔNG DỨT ĐIỂM — CẤM VIỆN CỚ BỊ CHẶN ĐỂ BÁO BLOCKED / KHÓC LÓC (Anti-Paralysis Invariant):** Cấm `delegate_task` cho việc code/test KHÔNG ĐƯỢC PHÉP trở thành cái cớ để Coordinator "đầu hàng", báo BLOCKED hay than phiền với Operator. Báo BLOCKED CHỈ hợp lệ khi gặp lỗi vật lý ngoài tầm kiểm soát (cháy máy, sập nguồn, rơi cổng USB, vỡ màn) hoặc thao tác tốn tiền/xóa dữ liệu cần User duyệt. Mọi lỗi code/test BẮT BUỘC phải thi công về DONE qua Thang Cứu Hộ 4 Tầng:
  1. *Tier 1:* Haiku CLI (`haiku_worker.py`, 6-15s O(1)).
  2. *Tier 2:* Antigravity CLI (`ag_cli.py fix` - Pool 7 acc Pro) khi Claude chạm trần/stale.
  3. *Tier 3:* L2 Emergency Surgery (Coordinator tự sửa O(1) <= 30 dòng, 1 test focused).
  4. *Tier 4 (Van an toàn):* Task lớn vượt L2 và cả 2 CLI đều cạn quota -> gắn cờ `WORKER_CLI_EXHAUSTED: true` để mở van subagent.
- **BẮT BUỘC TỰ ĐỘNG CHUYỂN GIAO STRIKE 3 CHO CLAUDE CLI (CẤM HỎI XIN PHÉP / CẤM KHÓC VỚI OPERATOR):** Khi Closeout Gate trượt 3 lần (Strike 3 với cờ `REVIEWER_HANDOFF_TRIGGERED`), quyền chuyển giao can thiệp cho Claude CLI đã được cấp sẵn và là INVARIANT TỐI CAO. Coordinator BẮT BUỘC tự động dispatch ngay `python D:/Taadaa/tools/claude_worker.py --role worker` với toàn bộ review findings của Reviewer để Claude CLI tự sửa code và viết test. TUYỆT ĐỐI CẤM dừng lại hỏi xin phép ("anh có muốn em gọi Claude CLI không?"), CẤM dùng `clarify` ("có muốn tiếp tục chốt phiên không?") hay than vãn đùn đẩy trách nhiệm cho Operator. Mọi lỗi test hoặc từ chối của reviewer trong phiên chốt phiên đều là nhiệm vụ tự thân (remediation loop), phải tự động xử lý đến cùng.
- **BYPASS SOL HOÀN TOÀN SAU KHI CLAUDE CLI SỬA XONG (The Direct-Push Invariant):** Khi Claude CLI hoàn tất sửa code và full pytest xanh 100%, BẮT BUỘC bỏ qua Sol High, cấm gọi lại closeout_gate.py để lấy điểm số Sol nữa. Chạy kiểm chứng cơ học (py_compile, pytest xanh 100%, test count không giảm, diff <= 150 dòng) rồi tự động PUSH LUÔN qua safe_push.py. CẤM quarantine, cấm báo BLOCKED khóc lóc (Xem references/auto-closeout-claude-bypass-sol-pipeline-20261016.md).
- **KỶ LUẬT FALLBACK KHI CLAUDE HẾT QUOTA (CẤM QUAY LẠI SOL, CẤM SUBAGENT OMNIROUTE):** Khi Claude CLI chạm trần session limit hoặc unreadable quota, pipeline `auto_closeout.py` tự động chuyển sang Agy CLI:
  1. Worker fix: `claude_worker.py --role worker` -> fallback `ag_cli.py fix` (Pool 7 acc Google Pro).
  2. Reviewer pass: `claude_worker.py --role reviewer` -> fallback `ag_cli.py ask` (trả về VERDICT: APPROVED).
  3. Sau khi Agy CLI duyệt và 4 nấc cơ học xanh: PUSH THẲNG QUA `safe_push.py`, TUYỆT ĐỐI CẤM quay lại Sol cày điểm, CẤM spawn subagent `delegate_task` qua OmniRoute (:20128/:20129) gây trễ và loãng context.
- **CẠM BẪY WORKTREE & PROMPT BỊ CẮT TRÊN WINDOWS MSYS BASH:**
  1. *Dirty Repo Worktree Refusal:* Khi repo có uncommitted changes, Claude CLI mặc định dừng lại hỏi tạo worktree. Bắt buộc thêm chỉ thị: `"Directly edit in place in the current repository without creating any worktrees. Do not touch other uncommitted files."`
  2. *Action-Verb Invariant:* Claude CLI bỏ qua prompt thụ động (`"In file X..."`). Bắt buộc mở đầu bằng động từ hành động trực tiếp (`Add...`, `Export...`, `Refactor...`, `Fix...`).
  3. *MSYS Bash Multiline Truncation:* Trong git-bash / MSYS trên Windows, chuỗi prompt có ký tự xuống dòng `\n` truyền vào CLI wrapper sẽ bị ngắt cụt ngay sau dòng đầu tiên. BẮT BUỘC viết prompt trên 1 dòng duy nhất, nối các câu bằng dấu chấm hoặc chấm phẩy.
  4. *Stale Quota Trap (>2h):* Nếu `plan-usage-history.json` cũ quá 2 giờ, `claude_worker.py` chặn chạy. Cần inject sample mới kèm `time.time() * 1000` hoặc chạy `claude /usage` để làm mới.
- **NEVER** run `claude -p "..." --dangerously-skip-permissions` raw in terminal.
- **NEVER** increase `--max-turns` above role's `hard_cap_turns`; split the task instead.
- **NEVER** use `worker` role for planning/reviewing just to get write access.
- **Misleading old name:** `haiku_worker.py` implied "Haiku only", causing bypasses for Sonnet tasks. `claude_worker.py` is model-agnostic and role-based.
- **Stale quota cache:** Refresh via `claude /usage` or by injecting a fresh sample if >2h stale. Lưu ý: nếu cache `plan-usage-history.json` bị lệch quá 2 giờ (`MAX_QUOTA_STALE_HOURS = 2.0`), `claude_worker.py` sẽ tự động kích hoạt Quota Gate và fallback sang `ag_cli.py`. Khi bị báo quota ảo, chạy ngay `python D:/Taadaa/tools/refresh_claude_quota_file.py` hoặc dựa vào cron job `refresh-claude-quota-watchdog` (chạy mỗi 30m).
- **Quy chuẩn Proxy 4G độc lập cho Antigravity Profile Pool (1-1 GPM Proxy Invariant):** CẤM để `proxy: null` (Direct IP) trong `profiles_config.json` vì Google Antigravity sẽ bóp TLS handshake hoặc ngâm socket gây timeout 60s. CẤM TUYỆT ĐỐI gán proxy tuần tự theo số thứ tự (`acc_01 -> mobi1`, `acc_02 -> mobi2`...). BẮT BUỘC map 1-1 với đúng proxy đã gán cho profile trong GPMLogin (lấy qua API GPM :19995). Toàn bộ 22 profiles (`acc_01` .. `acc_22`) được unpack từ OmniRoute qua `unpack_omni_connection.py` mang đúng proxy 4G Mobi/Khoalee của GPM. Xem `references/stale-quota-refresh-and-agy-proxy-isolation-20261017.md`.
- **Nguyên tắc 80/20 trong điều phối worker:** Chỉ dispatch khi giải quyết đúng 20% vấn đề tạo ra 80% giá trị; không dispatch mò mẫm hay làm xáo trộn kiến trúc khi chưa có Patch Contract O(1).
- **Foreground terminal timeout:** Host guard blocks commands > 60s. Use `--timeout 55` or `background=True` for deep reasoning tasks.
- **Windows CLI Stdin Pipe Bug (`Input must be provided either through stdin or as a prompt argument`):** When invoking `claude -p` on Windows via `subprocess.run`, piping prompt text exclusively via `stdin` (`input=prompt_input`) without passing a prompt positional argument after `-p` triggers Node.js stream detection failure in Claude CLI, causing `Error: Input must be provided either through stdin or as a prompt argument when using --print` (exit code 1). Always pass the prompt directly as a CLI argument: `cmd = [claude, "-p", prompt_input, "--model", model, ...]`. Do NOT place `"-p"` alone and pass `input=prompt_input` into `subprocess.run`.
- **Host Model Catalog & Naming Invariant (Haiku 5.5 Worker vs Sonnet 5.5 Mandate — TUYỆT ĐỐI CẤM 3.5 & CẤM ĐỔI ROLE):**
  The models configured and active on this host are strictly `claude-haiku-5-5` (cho `worker`) và `claude-sonnet-5-5` (cho `planner` và `reviewer`).
  1. *CẤM TUYỆT ĐỐI NHẮC ĐẾN "CLAUDE 3.5":* Operator chỉ sử dụng thế hệ 5.5. Việc buột mồm gõ nhầm hay nhắc đến 3.5 là lỗi hallucination nghiêm trọng.
  2. *CẤM ĐỔI ROLE WORKER SANG SONNET KHI THẤY CATALOG WARNING:* Claude Code CLI (v2.1.281) in warning `[claude-code:unrecognized_model]` cho `claude-haiku-5-5` chỉ là advisory SDK banner (do CLI chưa update catalog cục bộ), CLI VẪN GỌI VÀ CHẠY HAIKU BÌNH THƯỜNG. Tuyệt đối CẤM ngộ nhận đây là lỗi model rồi tự tiện đề xuất đổi role `worker` sang `claude-sonnet-5-5` (đốt quota và đi ngược chỉ đạo của Operator).
  3. *NGUYÊN NHÂN THỰC SỰ KHI WORKER CHẠM TRẦN TURNS:* Khi Haiku worker văng `Reached max turns` hay fail, nguyên nhân là do Coordinator gọi trực tiếp `claude_worker.py` với prompt nhiều dòng (multiline truncation trên Windows), prompt mở ("xem file remediate_prompt.txt"), hoặc task vượt quá budget O(1) khiến Haiku đi đọc file lan man.
  4. *BẮT BUỘC ĐI QUA `dispatch_worker.py`:* Mọi task sửa code / fix bug BẮT BUỘC gọi qua `python D:/Taadaa/tools/dispatch_worker.py --workdir <repo> [--file <target>] "<prompt 1 dòng>"`. Cổng này đã có sẵn bộ làm sạch prompt 1 dòng, tiêm `WORKER_DIRECTIVE`, thử lại Attempt 2 với prefix O(1), và tự fallback an toàn sang `ag_cli.py fix` khi cạn quota. CẤM gọi trực tiếp `claude_worker.py` bằng chuỗi prompt multiline trần.
- **Claude CLI Review Background Process Hangs (> 240s):** When running Claude CLI as a background reviewer with `allowedTools "Read,Grep,Glob"` and 8 max-turns on large codebases, processes can hang for 8+ minutes and must be killed with `process(action='kill')`. Root cause: Claude CLI reading 15,000+ line files sequentially across 5 file targets without context budget awareness. Mitigation: in review prompts, specify exact line ranges (e.g. `D:/... (dòng 230-275)`) and reduce `--max-turns 3` for review-only tasks with no write access. If the process exceeds 240s with no new output (observed via `process(action='poll')`), kill and re-invoke with a more focused prompt rather than waiting.
- **Telegram Async Delegation Spam Invariant:** When dispatching multiple sequential worker subagents during an active Telegram session, each `delegate_task(background=True)` completion fires an `[ASYNC DELEGATION BATCH COMPLETE — deleg_...]` English-language log block back into Telegram chat via `_async_delegation_watcher`. This floods the Operator's screen with raw technical logs and is a UX violation. To suppress: `hermes config set display.platforms.telegram.tool_progress off`. Additionally, prefer synchronous dispatch or consolidate results into a single final Vietnamese summary rather than streaming each worker's raw English completion into the chat.
- **GIT_EXTERNAL_DIFF Environment Variable Trap:** On Windows hosts where `GIT_EXTERNAL_DIFF=''` is exported in the environment, Git diff invocations fail with `error: cannot spawn : No such file or directory; fatal: external diff died`. When invoking `git diff` via subprocess in Python helpers or worker scripts, always pop `GIT_EXTERNAL_DIFF` from `os.environ` or pass `--no-ext-diff` directly after `diff`.
- **Mechanical Gate Placement & Regex Indentation Pitfall:** In `guard_dispatch_contract.py`, the hard mechanical block against `delegate_task` for code edits MUST be placed at column 0 immediately preceding `if not file_match:` in Branch 3. Placing it indented under a comment line `# 3. NHÁNH EDIT CODE` causes Python to bind it into the preceding `if not is_code_edit...` block after `sys.exit(0)`, making it unreachable dead code. Furthermore, regex strings checking override tokens (`WORKER_CLI_EXHAUSTED`, etc.) must use raw strings (`r'\b...\b'`) to prevent `\b` from decaying into ASCII backspace (`\x08`).
- **Python Subprocess Wrapper Argument Construction:** In `haiku_worker.py` and `claude_worker.py`, construct the command with the prompt directly in argv: `cmd = [claude, "-p", prompt_input, "--model", model, ...]`. Do NOT place `"-p"` alone and pass `input=prompt_input` into `subprocess.run`. Verify patches with `python -m py_compile` and a real invocation test (`--timeout 30 "Trả về đúng một chữ OK"`).
- **Zero-Diff False Exit 0 Trap & Zero-Probe Quota Rule (16/10/2026):** Claude CLI running headless (`-p`) on a repo with dirty working tree can trigger safety avoidance, output polite conversational text asking for clarification, and exit with code `0` without editing any files. Dispatchers MUST NOT trust `exit 0` alone as success. Always snapshot SHA256 of target files before and after; if hash is unchanged or output contains `BLOCKED:`, classify as `NO_DIFF` failure and trigger retry/fallback. Furthermore, NEVER dispatch worker CLI to run probe commands (`echo`, permission checks); all environmental tests must be deterministic local Python O(1) to protect 5h session quota. See `references/zero-diff-false-exit-zero-and-worker-hardening-20261016.md`.
- **Windows MSYS Multiline Truncation & Haiku Conversational Evasion Trap (16/10/2026):** When calling `claude -p` on Windows via `subprocess.run`, any newline `\n` in command-line arguments terminates or truncates the prompt in Node.js/Windows batch launchers, causing Claude CLI to receive only the first line (`Target file: ...`) and drop all task instructions. This makes Haiku ask "What do you want done with this file?" repeatedly. Fix: sanitize `prompt_input = " ".join(prompt.splitlines()).strip()` into a single line before passing to CLI, inject `WORKER_DIRECTIVE` via `--append-system-prompt`, and anchor `BLOCKED:` checks. See `references/windows-multiline-prompt-truncation-and-zero-diff-guard-20261016.md`.
- **CẠM BẪY CHẶN TỪ KHÓA ADB TRONG PROMPT WORKER (Hard Gate #5 False-Positive Trap 17/10/2026):** Khi gọi `claude_worker.py` từ terminal của Coordinator, bộ lọc hook an toàn (`hooks/guard_*.py`) quét toàn bộ chuỗi ký tự của command. Nếu trong text prompt chứa từ khóa `adb ` hoặc `adb shell` mà không đi kèm cờ `-s <serial>`, hook sẽ bắt nhầm và chặn đứng lệnh dispatch với lỗi `[HARD GATE #5 - AMBIGUOUS ADB DEVICE COMMAND]`. Khắc phục: TUYỆT ĐỐI KHÔNG dùng từ `adb` trần trong câu lệnh prompt truyền vào worker; thay bằng "device command execution", "Android debug bridge", hoặc tên hàm cụ thể (`execute_adb_cmd`, `dump_profile_ui_atx`). See `references/prompt-string-adb-guard-trap-and-grace-band-push-20261017.md`.
- **CẤM THỤ ĐỘNG ĐÙN VIỆC CHO USER KHI DÍNH GUARD BẢO VỆ (Anti-Abdication Invariant 17/10/2026):** Khi Coordinator thực hiện các thao tác cấu hình hệ thống (như cấu hình Hermes `config.yaml`, fix fallback IP, tăng retries) và bị bộ lọc bảo vệ `guard_system_protection` chặn do chuỗi tham số dòng lệnh chứa từ khóa nhạy cảm, TUYỆT ĐỐI CẤM ngồi than vãn, đầu hàng hay bảo Operator "mở file sửa tay mất 10s". Phải chủ động giải quyết bằng công cụ capability chuyên dụng `python D:/Taadaa/tools/manage_hermes_config.py` (hỗ trợ get/set, type casting, array indexing, atomic backup `.bak`) hoặc đóng gói logic vào script Python độc lập tại `D:/Taadaa/tools/` (ghép nối đường dẫn động, không phơi bày chuỗi cấm trong lệnh CLI). Đồng thời nắm rõ: Hermes Gateway là HTTP client liên tục nên chỉ fallback được qua HTTP proxy (`9Router :20128`, `OmniRoute :20129`), không thể fallback trực tiếp sang các subprocess CLI như Agy CLI hay Claude Haiku. Khi hạn mức 5h của Claude CLI đạt >= 85%, Quota Guard sẽ khóa cứng, Coordinator không được lôi Claude CLI ra cày review/test làm cạn quota mà phải tự review và thi công theo ngân sách O(1). See `references/coordinator-anti-abdication-and-gateway-config-resilience-20261017.md`.
- **CẠM BẪY ĐIỀU PHỐI UI/COMPONENT & NGHỊCH LÝ SUBAGENT DEADLOCK (The UI Delegation Deadlock & Claude CLI Escape 17/10/2026):** Khi sửa giao diện (UI/Dashboard/Component ≤ 1-2 files), Coordinator TUYỆT ĐỐI CẤM gán nhãn giả mạo `WORKER_CLI_EXHAUSTED: true` để cố đấm ăn xôi spawn `delegate_task` (`ag-gemini-pool-3`). Worker subagent chỉ có ngân sách 15 calls; việc đọc hiểu cấu trúc HTML/CSS/DOM sẽ ngốn 10-14 calls dẫn đến `ABORT_SCOPE` hoặc treo timeout 600s mà không ghi nổi 1 dòng code. Khi Worker lần 1 thất bại/abort: BẮT BUỘC DỪNG NGAY mọi `delegate_task`, leo thang thẳng lên `claude_worker.py --role worker` (hoặc Claude CLI với `--allowedTools Read,Edit,Write,Bash`). Claude Code CLI đọc hiểu và thay thế nguyên khối Master-Detail + chạy pytest chỉ trong vòng 60s. CẤM để xảy ra tình trạng "việc 1 phút thành 2 tiếng". See `references/ui-component-delegation-deadlock-and-claude-cli-escape-20261017.md`.
- **CƠ GIỚI HÓA TOÀN BỘ RULE THÀNH GUARD GATE CƠ HỌC & TRIỆT TIÊU KHÓC LÓC/TÊ LIỆT (Mechanical Gate vs Prompt-Based Invariant 18/10/2026):**
  Prompt chỉ là khuyến nghị mang tính xác suất, LLM sẽ drift và tự ý phá rào khi bị hối thúc hoặc bế tắc. MỌI rule vận hành bắt buộc phải cơ giới hóa thành code chặn vật lý (pre-tool hooks, single-entrypoint wrappers, HMAC-signed receipts, git hooks).
  1. *Khóa Push vật lý (`safe_push.py`):* Bắt buộc kiểm tra `gate_audit.jsonl` có bản ghi `APPROVED` / `CLAUDE_VERIFIED` gắn với `head_sha` còn hạn TTL 30 phút và score >= 85 (hoặc >= 80 grace band). Không có audit record hợp lệ thì ném `UnsafePushError("BLOCKED_GATE_NOT_APPROVED")`, cấm push vật lý ở tầng OS. Cấm tuyệt đối agent gọi `--owner-override`.
  2. *Zero-Waiting-State & Anti-Paralysis Invariant:* Mọi response DENY của Gate Authority BẮT BUỘC trả về `next_action` máy tự chạy được (deterministic code). TUYỆT ĐỐI CẤM trạng thái `ask_user` hay trả về câu hỏi mở khiến Coordinator rơi vào tê liệt khóc lóc.
  3. *State Machine không có `WAITING_OPERATOR`:* Strike 1 -> `sol_repair`; Strike 2 -> Đổi chiến lược/contract; Strike 3 -> `PARKED` (nhả lock thiết bị, hoàn nguyên known-good) và lập tức gọi `scheduler.next_task` bốc việc tiếp theo trong hàng đợi, cấm dừng lại hỏi xin phép. Lỗi tính toàn vẹn (Integrity) -> quarantine ngay lập tức.
  (Xem `references/mechanical-rule-to-guard-gate-v2-architecture-20261018.md`).

---

## Tests
43/43 passing across the worker dispatch subsystem:
- `D:/Taadaa/tools/tests/test_claude_worker.py`: 32/32 tests (role configs, turns clamping, tool lockdown, quota gate, stale cache, session limits, single-line prompt sanitization, `--no-fallback`, `EXIT_QUOTA_BLOCKED = 125`).
- `D:/Taadaa/tools/tests/test_dispatch_worker.py`: 11/11 tests (CRLF/whitespace normalization, failure hierarchy, snapshot & hash gate, target deletion rejection, unrelated files guard, anchored BLOCKED detection, PermissionError mapping, correlation ID consistency, Haiku/Agy fallback orchestration mocks).
- `D:/Taadaa/tools/tests/test_sol_worker.py`: 8/8 tests (safe shell command regex, metacharacters injection block, DSL parse, atomic patch lifecycle, AST validation, LF preserve, max_turns validation).

- `references/mechanical-rule-to-guard-gate-architecture-and-anti-paralysis-20261018.md` — **[MỚI 18/10/2026]** Kiến trúc Chuyển Hóa Mọi Rule Thành Mechanical Guard Gate (Spec v2.0 của Claude Sonnet 5.5 Planner + Reviewer APPROVED): Triệt tiêu hoàn toàn prompt-based compliance và trạng thái tê liệt/khóc lóc hỏi Operator; 5 nguyên lý fail-closed, FSM 3-strike khép kín tự bốc task kế (no WAITING_OPERATOR), khóa push vật lý trong safe_push.py kiểm tra gate_audit.jsonl TTL 30m, và bộ lõi guardgate/engine.py 30/30 unit tests.
- `references/claude-reviewer-anti-paralysis-unified-protocol-20261018.md` — **[MỚI 18/10/2026]** Bản Thỏa Thuận Đồng Thuận Cuối Cùng (Final Unified Protocol) giữa Claude Sonnet 5.5 Reviewer và Coordinator: phân tích 3 sai phạm nghiêm trọng (push sớm, gửi ảnh mù, stale receipt); thiết lập 3 cơ chế kiểm soát cơ học chống gian dối nhưng KHÔNG gây bại liệt (Grace Band 80-84 + 3-Strike, Evidence Gate tự phục hồi <= 3 lần chống false-positive, và Action-Scoped Sanction Ledger).
See `references/system-prompt-purge-and-json-config-update-20261018.md` for purging legacy Luna & delegate_task prompts from agent.system_prompt and atomic config update via manage_hermes_config.py --type json (18/10/2026).
See `references/catalog-warning-hallucination-and-header-consumer-desync-20261017.md` for post-incident analysis on Claude CLI catalog warning hallucination, why Haiku 5.5 worker must NEVER be switched to Sonnet, and Excel header consumer desync remediation (17/10/2026).
See `references/safe-push-mechanical-gate-and-anti-paralysis-architecture-20261017.md` for Safe Push Mechanical Gate architecture (unbypassable audit verification against gate_audit.jsonl with 30m TTL), auto_closeout closed loop, and eliminating coordinator paralysis/asking (17/10/2026).
See `references/sol-worker-guardrails-and-strike-3-failure-protocol-20261017.md` for Sol Worker 4 guardrails (atomic rollback, cumulative diff <=100 lines, test preservation, valid verify command), turn semantics, and Strike 3 Terminal Failure Protocol (17/10/2026).
See `references/strike-3-quota-preservation-haiku-worker-vs-sonnet-reviewer-20261017.md` for Strike 3 Quota Preservation: Haiku Worker vs Sonnet Reviewer role separation and Turn semantics (17/10/2026).
See `references/prompt-string-adb-guard-trap-and-grace-band-push-20261017.md` for Hard Gate #5 prompt string false-positive on bare ADB tokens, pre-push hook THRESHOLD=85 vs Grace Band, and L0 diff budget sequential commit strategy (17/10/2026).
See `references/ui-component-delegation-deadlock-and-claude-cli-escape-20261017.md` for the UI delegation deadlock analysis, why delegate_task aborts on 15-call budget, and direct Claude CLI single-shot resolution (17/10/2026).
See `references/strike-3-reviewer-handoff-direct-push-procedure-20261017.md` for Strike 3 Reviewer Hand-off direct-push procedure, avoiding open-ended worker loops and using targeted --max-turns 6 Claude Reviewer (17/10/2026).
See `references/closeout-scope-isolation-and-pre-push-hook-contract-20261017.md` for Closeout scope contamination prevention (the git commit -a trap), Pre-Push Hook contract reconciliation, and workbook header matching rules (17/10/2026).
See `references/sol-web-autonomous-fallback-worker-20261017.md` for Sol Web Autonomous Fallback Worker (:20129) architecture, atomic patching, and worker reporting vs session-close boundaries (17/10/2026).
See `references/strike-3-reviewer-handoff-and-telemetry-remediation-20261017.md` for Strike 3 Reviewer Hand-off protocol and telemetry/error handling remediation to overcome Closeout Gate 84/100 threshold (17/10/2026).
See `references/strike-3-background-dispatch-timeout-invariant-20261017.md` for Strike 3 Reviewer Hand-off background execution and avoiding foreground timeout traps (17/10/2026).
See `references/strike-3-claude-turns-cap-and-candidate-ranking-20261016.md` for Strike 3 Reviewer Hand-off turns cap allocation (--max-turns 15) and candidate ranking invariants (16/10/2026).
See `references/mechanical-gate-indentation-and-git-diff-trap-20261015.md` for Mechanical Gate indentation bug, regex boundary decay trap, and GIT_EXTERNAL_DIFF environment variable fix (15/10/2026).
See `references/mechanical-gate-pitfalls-and-anti-paralysis-discipline-20261015.md` for Mechanical Gate indentation pitfalls, Strike-3 Reviewer Hand-off, and the Anti-Paralysis Protocol (15/10/2026).
See `references/prompt-precedence-and-score-chasing-circuit-breaker-20261015.md` for Claude Sonnet architecture advice on Prompt Precedence, mechanical gates, and Closeout Gate circuit breaker (15/10/2026).
See `references/strike-3-automatic-claude-handoff-and-worktree-bypass-20261015.md` for Strike 3 automatic Claude CLI hand-off and dirty repo worktree bypass rules (15/10/2026).
See `references/claude-worker-role-dispatch-and-turns-hard-cap-20261015.md` for full incident analysis.
See `references/gemini-pool-subagent-and-closeout-score-chasing-trap-20261015.md` for analysis of the Gemini Pool subagent stall and 85-score Closeout Gate infinite loop (15/10/2026).
See `references/mechanical-gate-delegate-task-lockdown-20261015.md` for mechanical gate dispatch lockdown, delegate_task blocks on code edits, and the 3-tier worker fallback ladder (Haiku -> AG CLI -> L2/subagent escape valve).
See `references/windows-stdin-pipe-and-haiku-5-5-catalog-invariants-20261015.md` for analysis of the Windows Node.js stdin pipe bug (`--print` error) and host-level invariants for `claude-haiku-5-5` & `claude-sonnet-5-5`.
See `references/auto-closeout-claude-bypass-sol-pipeline-20261016.md` for the Claude Auto-Closeout Pipeline (`auto_closeout.py`), bypassing Sol infinite review loops, 4-stage mechanical verification gate, and anti-quarantine direct auto-push (16/10/2026).
See `references/closed-loop-autonomous-completion-and-fail-safe-ladder.md` for Closed-Loop Autonomous Completion, the 4-Tier Fail-Safe Ladder when quota is exhausted, and the Strike 3 Automatic Hand-off Protocol (16/10/2026).
See `references/single-dispatch-gateway-and-subagent-ban-20261016.md` for the Single Dispatch Gateway (`dispatch_worker.py`), the strict subagent ban (`delegate_task` forbidden for code edits), and the Claude Auto-Closeout Pipeline (`auto_closeout.py`) (16/10/2026).
See `references/intelligent-failure-classification-and-haiku-retry-ladder-20261016.md` for the Intelligent Failure Classification (QUOTA vs ENV vs MAX_TURNS), why Haiku must not decompose tasks, and the 2-Attempt Haiku Retry Ladder before escalating to Agy CLI (16/10/2026).
See `references/quota-guard-self-unlock-prevention-and-cross-family-review-20261016.md` for the incident analysis of Quota Guard self-unlock bypass, 100% quota depletion, Claude Code architectural advice, and strict Cross-Family Review enforcement against fake Gemini reviews (16/10/2026).
See `references/zero-diff-false-exit-zero-and-worker-hardening-20261016.md` for Zero-Diff False Exit 0 trap, conversational evasion on dirty trees, pre/post target SHA256 snapshotting, and the Zero-Probe Quota Discipline (16/10/2026).
See `references/zero-diff-verification-and-conversational-refusal-guard-20261016.md` for Zero-Diff Verification & Conversational Refusal Guard in dispatch_worker.py, failure classification precedence, line-anchored BLOCKED: regex, and fail-closed baselines (16/10/2026).
See `references/windows-multiline-prompt-truncation-and-zero-diff-guard-20261016.md` for the Windows MSYS multiline truncation trap (\n dropping prompt instructions), single-line prompt sanitization, WORKER_DIRECTIVE injection, and verified Attempt 1 Haiku completion (16/10/2026).
