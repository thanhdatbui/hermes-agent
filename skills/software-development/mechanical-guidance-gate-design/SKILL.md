---
name: mechanical-guidance-gate-design
description: "Use when designing mechanical gates to prevent agent loops."
---

# Mechanical Guidance Gate Design (Anti-Whining & Action Mandate)

## 1. When to Use
Use when creating, modifying, or reviewing mechanical enforcement gates (hooks, gates, runtime fences). Enforces actionable unblocking paths (Auto-Rewire / Active Pivot) rather than passive denials.
- Reference: `references/pre-tool-auto-rewrite-and-24h-heartbeat-architecture.md` (Pre-tool rewrite).
- Reference: `references/auto-rewire-and-auto-clamp-architecture.md` (Worker rewrite & clamp).
- Reference: `references/user-sudo-override-and-investigate-read-only-deadlock-triage.md` (Sudo override).
- Reference: `references/dispatch-worker-timeout-and-deadlock-prevention-20261025.md` (Timeout floor 360s).
- Reference: `references/gate-compliance-audit-desync-and-test-pollution-invariants.md` (Telemetry filtering).
- Reference: `references/active-pivot-auto-rewire-architecture.md` (Auto-Rewire).
- Reference: `references/multi-repo-regression-gate-hierarchy.md` (2-tier rules.json partition).
- Reference: `references/o1-process-verification-and-closeout-operational-decoupling.md` (Process verification).
- Reference: `references/canary-gate-auto-wiring-vs-memory-enforcement-20261028.md` (Canary auto-wiring, multi-req scanning, and upload evidence grounding).
- Reference: `references/observability-watchdog-vs-bureaucratic-blocking-gate-pruning.md` (Observability watchdogs retention vs bureaucratic blocking gate & local hash chain pruning).
- Reference: `references/auto-wiring-and-guidance-boundary-matrix-20261026.md` (Auto-Wiring vs Fail-Fast decision matrix for investigate budget & GuardGate guidance).
- Reference: `references/idle-window-evaluation-bias-and-closeout-boundary-discipline.md` (Idle-window evaluation bias & zero-block action mandate hierarchy).
- Reference: `references/cowboy-coordinator-boundary-and-idle-evaluation-invariants.md` (Cowboy Coordinator Gate 3/6 boundary violations).
- Reference: `references/user-sudo-override-and-gate-abc-discipline.md` (User Sudo Override protocol, Pipeline A-B-C stages, & anti-idle-window invariants).

## 2. Core Standards (Tri-Party Consensus)

### Rule 1: No Silent Veto Gates (Cấm Veto Gate Câm & Gate Bại Liệt)
- **Violation:** A gate checks a condition, fails, prints a static error (e.g. `[DENY] Policy violated`), and executes `sys.exit(1)` without providing executable next steps or an automatic self-healing route. This leaves an LLM agent in a cognitive void, triggering apologetic loops or bureaucratic helplessness ("bại liệt / khóc lóc").
- **Requirement:** Every gate DENY must be paired with either (a) an **Auto-Rewire / Active Pivot** mechanism that immediately mutates and forwards the action safely (e.g. `haiku_worker` & `claude_worker` auto-rewiring direct invocations to `dispatch_worker.py`), or (b) a machine-readable `REQUIRED_ACTION_O1` block with copy-pasteable commands and architectural guidance.

```json
{
  "gate": "<gate_name>",
  "verdict": "BLOCKED",
  "reason": "<1-line failure summary>",
  "guidance": "<architectural rationale and invariant>",
  "REQUIRED_ACTION_O1": {
    "command": "<concrete_executable_command_with_resolved_paths>",
    "expected_effect": "<what running this command achieves>",
    "fallback_if_fails": "<alternative command if primary fails>"
  },
  "evidence_path": "<audit_log_or_diff_path>"
}
```

### Rule 2: Anti-Bypass Whitelist (Chống Self-Bypass)
- The command provided in `REQUIRED_ACTION_O1` MUST NEVER be a bypass flag (`--force`, `--no-verify`, `--skip-test`, `--allow`).
- Permitted action types:
  1. Scope reduction (narrowing diff to $\le 30$ lines on target file).
  2. Evidence generation (focused test, targeted log inspection).
  3. Canonical fast-path redirection (e.g., using `lookup_channel.py` instead of broad disk scans).

### Rule 3: Reversibility & Auto-Quarantine O(1)
- When a gate intercepts invalid code or staged artifacts, it should automatically quarantine the offending hunk (e.g., via `git stash push --keep-index -m "quarantine-<rule>-<ts>" -- <file>`) to restore a clean working tree.
- The agent is informed of the quarantine reference and can proceed without fear of a dirty workspace.

### Rule 4: Strike 3 Guidance Gap & Cryptographic Hash-Isolated Self-Update
- If an agent fails the same invariant 3 consecutive times (`STRIKE-3-GUIDANCE-GAP`), do NOT allow bureaucratic idling (such as creating a ticket JSON and freezing).
- **Core Distinction:** Separate Enforcement (predicates, min/max values, target files) from Guidance (architectural explanation text).
- **Enforcement Invariant (Cấm Tự Sửa Logic Chặn):** LLM MUST NEVER have write permission to the enforcement schema or be able to self-approve a blocked diff.
- **Safe Self-Update via Hash-Isolation Tool (O(1)):**
  1. The LLM can invoke a dedicated atomic tool:
     `python D:/Taadaa/tools/guardgate/update_guidance.py --rule-id "<rule_id>" --guidance "<bài học kiến trúc>"`
  2. The tool computes `hash_enforcement` on an independent pre-mutation snapshot, updates only `guidance`, and computes `hash_enforcement` post-mutation.
  3. Strict invariant: `assert hash_before == hash_after`. If any enforcement field (`match`, `require_all`, `params`, `on_deny`, `vectors`) is touched, it fails fast with `AssertionError`.
  4. Write safety: Atomic replace (`_atomic_write_json` via tempfile + `fsync` + `os.replace`) with automatic rollback of `rules.json` if audit logging fails.
  5. **No Self-Bypass:** Updating guidance serves future sessions, but the violating diff of the current session remains REJECTED/QUARANTINED. The agent reports the updated guidance and pivots to an independent task.

### Rule 5: Early Closeout Gate Interception (Pre-Review / Step 2.5 Hook)
- **Violation:** A mechanical regression gate is only hooked into the push command (`safe_push.py`). As a result, `closeout_gate.py` still runs full test suites and invokes expensive Reviewer LLM calls on a diff that violates protected invariants, wasting minutes and quota before failing at the git push step.
- **Requirement:** Mechanical Invariant Gates (e.g. `guardgate.runner.check_diff`) MUST be evaluated at Step 2.5 (immediately after candidate diff extraction, BEFORE test execution and BEFORE LLM Reviewer). If an invariant is violated:
  1. Print domain guidance and exact copy-pasteable recovery action (`REQUIRED_NEXT_ACTION`).
  2. Auto-quarantine the violating hunk via `git stash` ($O(1)$ workspace recovery).
  3. Terminate immediately with `sys.exit(1)`, preserving tokens, time, and preventing false-positive review cycles.

### Rule 6: Input Validator Action Mandate (Quy Chuẩn Chốt Chặn Đầu Vào Có Hướng Dẫn)
- **Bối cảnh:** Khi viết chốt chặn cơ học (validator / runner guard) chặn các tham số vi phạm (ví dụ: chuỗi Bio/Name tiếng Việt không dấu, thiếu cờ bắt buộc, sai định dạng), CẤM TUYỆT ĐỐI chỉ raise exception cụt lủn hoặc thoát `exit(1)` câm không lời giải thích.
- **Bắt buộc 4 thành phần trong thông báo lỗi (Fail-Fast với Actionable Guidance):**
  1. `[VALIDATION_DENY: <RULE_NAME>]`: Mã định danh vi phạm rõ ràng.
  2. `VIOLATION`: Nêu đích danh trường dữ liệu và giá trị sai phạm cụ thể.
  3. `HƯỚNG DẪN KIẾN TRÚC / GUIDANCE`: Giải thích tại sao cấm, nguyên tắc hệ thống và tác hại của hành vi đó.
  4. `REQUIRED_NEXT_ACTION`: Cung cấp sẵn câu lệnh mẫu $O(1)$ copy-paste chạy được ngay ở turn tiếp theo.
- **Tiêu chuẩn kiểm tra tiếng Việt cấp từ (Word-Level Diacritics Ratio Validator):**
  - **Cấm regex tìm 1 ký tự dấu đơn độc:** Chỉ kiểm tra sự hiện diện của 1 ký tự dấu dễ bị qua mặt bởi chuỗi rác lai tạp như `hello á` hoặc `hello đ`.
  - **Chuẩn hóa NFC trước:** Bắt buộc `unicodedata.normalize("NFC", text)` trước khi tách từ `re.findall(r"\w+", text)` để các dấu tổ hợp (NFD) gộp lại thành single code point, tránh bị xé nhỏ thành các token 1 chữ cái.
  - **Kiểm tra tỷ lệ từ có dấu:** Đếm các từ có độ dài $\ge 2$ ký tự chứa dấu tiếng Việt (`_has_vi_accent`). Yêu cầu tối thiểu $\ge 1$ từ có dấu nếu chuỗi có $\le 2$ từ, và $\ge \max(2, \lceil 0.3 \times N \rceil)$ từ có dấu nếu chuỗi có $> 2$ từ.
  - **Telemetry có cấu trúc:** Bắt buộc ghi nhận event telemetry JSON (`event: validate_vietnamese_accent`, `field`, `valid`, `accented_words`, `needed_words`, `total_words`) để phục vụ quan sát vận hành. Cấm log nguyên văn dữ liệu nhạy cảm.

### Rule 7: Gate Observability & Telemetry Rollup (Chống Chặn Thầm Lặng / Quên Giám Sát)
- **Bối cảnh:** Khi hệ thống có nhiều gate cơ học phân tán (GuardGate Invariants, Closeout Gate, Pre-push Hook, Dispatch Floor, Media Vision Gate), các lần chặn hoặc vi phạm thường nằm im trong các file log JSONL (`ledger.jsonl`, `gate_audit.jsonl`, `safe_push_audit.jsonl`, `dispatch.jsonl`). Operator không thể biết nếu không tự tay lục lọi ("lâu lâu mới nhớ phát hiện ra").
- **Kiến trúc giám sát 3 tầng bắt buộc:**
  1. **Real-time Alert Ping:** Hễ gate kích hoạt `DENY`, `REJECTED`, hoặc `STRIKE-3` $\rightarrow$ phát ngay telemetry ping ngắn gọn O(1) về Telegram Farm Alert (`-5373649734`). CẤM để gate chặn trong bóng tối.
  2. **Periodic Rollup Watchdog (6h/24h):** Cronjob đối soát tự động quét các file JSONL, tổng hợp Scorecard tuân thủ (tổng số lần vi phạm, top gate bị trigger, tỷ lệ phục hồi O(1)) gửi về nhóm điều hành.
  3. **On-Demand O(1) Inspection:** Cung cấp script tra cứu siêu tốc `python D:/Taadaa/tools/gate_audit_summary.py` (< 1s) hoặc slash command `/gate_status` để Operator kiểm tra tức thì bất kỳ lúc nào.
  4. **Designated Log Source Isolation & Remediation Loop Accounting:** Mỗi Gate trong 8 Gate cơ giới hóa farm phải gắn với đúng file log chuyên trách (`source_file`), cấm dùng regex generic quét xuyên file gây nhiễm bẩn chéo. Trên Gate Reviewer (G5), khi reviewer chấm `REJECTED` nhưng sau đó cùng repo/context đạt `APPROVED`, watchdog bắt buộc ghi nhận là `remediation_hits` (hợp lệ), cấm tính nhầm vào vi phạm (`fail_hits`).
  5. **Top Blocked Rules Mandate:** Báo cáo định kỳ bắt buộc tổng hợp bảng xếp hạng các mã `rule_id` bị chặn nhiều nhất kèm số lần vi phạm để Operator/Agent nhận diện chính xác các điểm nghẽn và nạp guidance bổ sung, giúp Agent hoàn thành task nhanh hơn và tiết kiệm token.

### Rule 8: 4 Deterministic Checkpoints For Coordinator Dispatch (Chống Điều Phối Ẩu Bằng Gate Cơ Học)
- **Bối cảnh:** Các quy định bằng văn bản (Policy-as-Text) trong AGENTS.md bị suy giảm chú ý (attention decay) khi ngữ cảnh phình to, khiến Coordinator liên tục vi phạm: ngồi gõ văn giải thích thay vì chạy lệnh inspect, táy máy hạ timeout sửa ngược session trước, dispatch worker với max-turns quá hẹp và tự bịa lời tường thuật khi worker lỗi.
- **Yêu cầu 4 Checkpoint Bắt Buộc:**
  1. **Pre-Execution Incident Tool Gate:** Khi tin nhắn chứa pattern sự cố/alert Farm $\rightarrow$ CẤM turn phản hồi kết thúc bằng 0 tool call (pure free-text); ép buộc phải có ít nhất 1 tool kỹ thuật điều tra hiện trường (`inspect_machine.py`, `adb`, log).
  2. **Protected-Constant Regression Gate:** Tra cứu tĩnh danh sách hằng số bảo vệ (Case 162 timeout $\ge 20\text{s}$, worker timeout $\ge 300\text{s}$, follow_limit $\le 0$). Bất kỳ diff nào hạ giá trị dưới sàn đều bị DENY tại Step 2.5 của closeout gate kèm Auto-Quarantine $O(1)$.
  3. **Pre-Dispatch Parameter Validator:** Hook kiểm tra tham số trước khi gọi worker; ép `max_turns \ge 15` cho planner và kiểm tra git status sạch trước khi pipe vào interactive CLI tools.
  4. **Post-Dispatch Evidence Presence Check:** Subprocess output bắt buộc parse thành schema cứng; nếu lỗi/timeout thì inject nhãn `[TOOL_OUTPUT_MISSING: exit=<rc>]`, cấm Coordinator tự ý bịa lời giải trình.

### Rule 9: Anti-Deadlock Execution Path & Stop Hook Barrier (Chống Deadlock Đâm Chéo & Báo Xong Ảo)
- **Bối cảnh:** Khi nhiều gate được dựng lên độc lập (Foreground clamp 60s, Background cấm console/pythonw, T1 budget cấm tự sửa, Dispatch gate cấm delegate_task, Closeout cấm clarify), chúng có thể vô tình đâm chéo lẫn nhau, triệt tiêu 100% mọi lối thoát hợp lệ của Coordinator. Bị dồn vào chân tường, model bắt buộc phải chọn hành vi sai lệch: lách luật gọi Sonnet làm việc vặt, tuyên bố xong ảo khi working tree vẫn còn dirty, hoặc tệ nhất là khóc lóc bảo Operator ra ngoài gõ lệnh hộ.
- **Yêu cầu 3 Chốt Chặn Bắt Buộc:**
  1. **Anti-Deadlock Execution Path Invariant:** Mọi tổ hợp Gate bắt buộc phải duy trì ít nhất 1 đường bay thông suốt cho Coordinator. Nếu cấm tự sửa $\to$ đường dispatch worker (`dispatch_worker.py`) phải được miễn trừ timeout foreground (cho phép $\le 360\text{s}$) hoặc `pythonw` phải nằm trong allowlist background.
  2. **Anti-Whining Hook Mandate (Cấm Đẩy Việc Cho Operator):** CẤM TUYỆT ĐỐI thiết kế hook tạo ra ngõ cụt rồi ép Agent phải phân trần hoặc xin xỏ "Operator mở terminal ngoài chạy lệnh hộ em". Hook phải tự hành và hoàn chỉnh từ đầu.
  3. **Stop Hook Barrier (Chặn Tuyên Bố Xong Ảo):** Cấm dựa vào lời dặn trong AGENTS.md để ngăn "báo xong non". Bắt buộc dùng Stop Hook ở tầng harness kiểm tra `gate_audit.jsonl` và `git status`: nếu tin nhắn có từ khóa hoàn tất mà gate chưa `APPROVED >= 85` hoặc tree còn dirty $\to$ Hook tự động vứt bỏ tin nhắn, thay thế bằng cảnh báo chặn đứng dứt khoát!
  4. **Coordinator Security Boundary Discipline (Cấm Khóc Lóc & Cấm Đẩy Việc Khi Chạm Vùng Cấm):**
     - Khi một hook trong thư mục hooks bị lỗi thiết kế hoặc gây ra deadlock, Coordinator BẮT BUỘC nhận diện đây là ranh giới bảo mật cơ học (fail-closed by design) — AI bên trong phiên bị cấm tự ý sửa đổi Hook bảo vệ của chính nó.
     - **CẤM TUYỆT ĐỐI:** Đóng vai nạn nhân bất lực, viết sớ phân trần khóc lóc, hoặc ném một lệnh shell dài ngoằng bảo "Operator mở terminal ngoài gõ lệnh hộ em". Đây là hành vi vi phạm nặng nhất nguyên tắc Anti-Whining.
     - **PHẢN ỨNG CHUẨN:** Báo cáo dứt điểm 3 điểm: (1) Khai báo rõ ràng lý do bị chặn bởi cơ chế bảo vệ vùng cấm, (2) Chỉ rõ mâu thuẫn kỹ thuật giữa các gate (ví dụ: clamp 60s vs cấm background console), (3) Thẳng thắn xác nhận ranh giới thẩm quyền ("Tao không thể tự sửa vì vi phạm vùng cấm; đóng task này tại đây và làm việc khác"), tuyệt đối không đẩy việc cho Operator.

### Rule 10: Hook Wiring Parity & Zero-Orphan Invariant (Chống Viết Hook Nhưng Quên Wire Vào Runtime Config)
- **Bối cảnh:** Gate bảo vệ được viết rất công phu, pass 100% unit tests (như `guard_cronjob_safety.py` pass 12/12 unit tests), nhưng lại KHÔNG được wire vào `hooks.pre_tool_call` của runtime `config.yaml`. Điều này tạo ra "ảo tưởng an toàn" (false sense of security): Operator đinh ninh hệ thống đã có chốt chặn, trong khi Agent vẫn tự do vi phạm và lách luật vì engine runtime không hề gọi hook lúc tool được kích hoạt.
- **Yêu cầu 3 Chốt Chặn Bắt Buộc:**
  1. **Dual-Config Parity Mandate:** Mọi hook mới bắt buộc phải được wire đồng bộ vào cả Runtime Config (`%LOCALAPPDATA%\hermes\config.yaml`) lẫn Deploy Config (`deploy/hermes-home/config.yaml`). Độ lệch giữa 2 file (config skew) bị coi là lỗi kiến trúc nghiêm trọng.
  2. **Automated Idempotent Wiring CLI:** Bắt buộc cung cấp hàm/lệnh tự động hóa O(1) (như `manage_hermes_config.py wire-<hook>-hook` hoặc update script có atomic backup) để ghi hook vào `hooks.pre_tool_call` an toàn, cấm sửa tay trực tiếp dễ gây hỏng YAML syntax.
  3. **End-to-End Interception Verification:** Sau khi wire, cấm chỉ chạy unit test file hook độc lập; BẮT BUỘC kiểm thử e2e qua lệnh gọi tool thực tế (ví dụ: chạy một lệnh gọi tool giả định vi phạm xem runtime có quăng block error ra hay không) để chứng minh hook thực sự đã cắn vào vòng đời pre-tool use.

### Rule 11: Reviewer Scope & Pragmatism Discipline (Chống Bẫy Reviewer Vạch Lá Tìm Sâu Vượt Scope Làm Tắc Nghẽn Gate)
- **Bối cảnh:** Khi `closeout_gate.py` gọi Reviewer LLM (Sol Auditor qua `:20129`) với prompt chung chung không có ranh giới phạm vi, Reviewer thường sinh ra các đòi hỏi lý thuyết viển vông (đòi centralized logging/correlation ID cho CLI script đơn lẻ, đòi test ADB thiết bị thật ngoài đời cho logic mock unit test, đòi phân tích ngữ pháp NLP thay vì regex heuristic). Điều này ghìm điểm ở mức 76–79đ, kích hoạt Strike-3 Handoff và đẩy Coordinator vào thế bại liệt khóc lóc. Đồng thời, hàm tính O(1) nếu không loại trừ file test sẽ làm mất Fast-Path (Grace Band 80–84) của các patch viết test kỹ.
- **Yêu cầu 4 Nguyên Tắc Thực Dụng Cơ Học (Scope & Pragmatism Discipline):**
  1. **CLI Script Telemetry:** Telemetry in JSON ra stdout hoặc ghi file report cục bộ là ĐỦ VÀ HỢP LỆ. Cấm trừ điểm vì thiếu hạ tầng log tập trung hay correlation ID.
  2. **Mock Test Absolute:** Với logic bugfix/patch, test unit/mock cô lập đạt 100% pass là ĐẠT YÊU CẦU ĐẦY ĐỦ. Cấm trừ điểm vì không can thiệp thiết bị thật ngoài đời (bảo vệ an toàn vật lý của farm).
  3. **Pragmatic Heuristics:** Đánh giá giải pháp có giải quyết đúng mục tiêu kỹ thuật hay không, cấm đòi hỏi NLP/ngôn ngữ học vượt phạm vi task.
  4. **Fast-Path O(1) Excludes Test Files:** Hàm `_compute_diff_is_o1()` bắt buộc lọc bỏ toàn bộ file test (`tests/*`, `test_*`), chỉ đếm số dòng thay đổi của production code ($\le 60$ dòng) để không trừng phạt kỹ sư viết test bao phủ cao.
  - Sửa cơ học trực tiếp trong mã nguồn `closeout_gate.py` (`DEFAULT_SYSTEM_PROMPT` và `_compute_diff_is_o1`), cấm dựa vào cờ phụ `--system-prompt` tạm thời và tuyệt đối cấm dừng lại viết sớ phân trần. Chi tiết xem: [`references/closeout-gate-reviewer-scope-discipline.md`](references/closeout-gate-reviewer-scope-discipline.md).

### Rule 12: Closeout Gate Commit Binding & Committed-Scope Parity (Chống Lỗi Bị Chặn Push Dù Gate Đã Pass)
- **Bối cảnh 1 (Worktree Hash Binding):** Khi repository đã có các commit cục bộ trước đó (nhánh ahead of origin), nếu Coordinator chạy `closeout_gate.py --repo <repo> --base HEAD --files ...`, gate chỉ trích xuất working tree diff và ghi nhận hash của candidate diff, KHÔNG gắn kết với commit hash của `HEAD`. Khi đó, lệnh `safe_push.py` kiểm tra `gate_audit.jsonl` đối chiếu với `HEAD` sẽ báo lỗi: `BLOCKED_GATE_NOT_APPROVED: Repository has no valid APPROVED closeout audit for HEAD (<hash>)`.
- **Bối cảnh 2 (Committed-Scope Exact-Match Trap):** Khi chạy `closeout_gate.py --repo <repo> --base HEAD~1 --files ...`, hàm `targeted_candidate()` kiểm tra nghiêm ngặt `set(targets) == committed_scope`. Nếu truyền sai file (ví dụ file của commit cũ hoặc thiếu file trong commit của HEAD), gate ném `ValueError: committed scope [...] != --files targets [...]; refusing partial committed scope`. Nếu bỏ qua `--files` khi working tree có file khác, gate fail-fast `[Gate Fail-Fast: SCOPE_NOT_DECLARED]`.
- **Yêu cầu Chuẩn Hóa Chốt Phiên 3 Bước:**
  1. **Lấy danh sách file chính xác của HEAD:** Bắt buộc chạy `git show --stat --oneline HEAD` để lấy đúng các file vừa được commit.
  2. **Thẩm định commit đúng scope:** Chạy `python D:/Taadaa/tools/closeout_gate.py --repo <repo> --base HEAD~1 --files <file1> <file2> ... --json-output` để gate trích xuất `committed_targeted` diff và `write_gate_audit` ghi nhận chính xác `"commit": "<HEAD_SHA>"` vào chuỗi audit.
  3. **Safe Push Execution:** Chỉ thực thi push qua wrapper chuẩn: `python D:/Taadaa/tools/safe_push.py <repo> origin <branch>`. Pre-push hook sẽ tự động đối soát audit entry `APPROVED` của commit `HEAD` và cho phép đẩy code an toàn lên remote.

### Rule 13: Generic Declarative Predicates & Safe Invariant Onboarding (`add_rule.py`)
- **Bối cảnh:** Trước đây khi có sự cố mới (Case 161 popup, Case 162 USB, Worker timeout floor), kỹ sư phải sửa tay 3 file (`predicates.py`, `rules.json`, `runner.py`), dễ gây sót case sau khi fix hoặc dính Rule Shadowing do stopping-at-first-match.
- **Yêu cầu 3 Chốt Chặn Cơ Giới Hóa:**
  1. **Generic Declarative Templates:** Thay vì viết code Python rời, chuẩn hóa 4 template trong `predicates.py`: `numeric_floor`, `numeric_ceiling`, `prohibited_pattern`, `required_pattern`. Engine tự động bind động theo `rule.params`.
  2. **Atomic Pre-flight Onboarding (`add_rule.py`):** Bắt buộc cung cấp rule JSON kèm 2 test vector (1 ALLOW, 1 DENY). Tool chạy GuardEngine trong RAM thẩm định trước; pass 100% mới ghi đè nguyên tử (`_atomic_write_json`) và append audit log.
  3. **Unidirectional Enforcement:** `add_rule.py` chỉ được phép SIẾT (Deny), tuyệt đối CẤM nới lỏng (Allow/Exempt). Thống nhất 3 bên (Claude Sonnet, Sol Reviewer, Coordinator) khi cập nhật invariant kiến trúc. Chi tiết: [`references/incident-to-guard-automation-and-8gate-compliance.md`](references/incident-to-guard-automation-and-8gate-compliance.md).

### Rule 14: Watchdog Telegram Delivery Robustness & Timezone Parity (Chống Crash HTTP 400 & Lệch Giờ UTC)
- **Bối cảnh:** Khi viết các watchdog tổng hợp và báo cáo Gate định kỳ (như `gate_compliance_watchdog.py`), thường mắc 2 lỗi ngầm làm đứt gãy quan sát:
  1. **Telegram Markdown v1 Crash (HTTP 400 Bad Request):** Báo cáo chứa các hằng số kỹ thuật có dấu gạch dưới (`NO_EVIDENCE`, `STATUS_OK`), ngoặc vuông dính sao (`*[REPORT]*`), khiến Telegram Bot API từ chối phân tích cú pháp và văng `HTTP Error 400: Bad Request`. Hậu quả: Báo cáo chết chìm trong im lặng, Operator không nhận được tin nhắn.
  2. **Lệch Múi Giờ UTC vs Local Time (Ảo Tưởng NO_EVIDENCE):** Các file audit log của farm (`gate_audit.jsonl`, `vision_receipts.jsonl`, `ledger.jsonl`) ghi nhận timestamp chuẩn UTC (`timestamp_utc`). Nếu watchdog tính `cutoff = datetime.now() - 6h` theo giờ Local (UTC+7 ở VN), các sự kiện thực tế trong 6h qua sẽ bị coi là nằm ngoài cửa sổ (lệch 7 tiếng) và bị vứt bỏ toàn bộ, dẫn đến báo cáo `NO_EVIDENCE` giả mạo.
- **Yêu cầu 2 Chuẩn Cơ Học Bắt Buộc:**
  1. **Telegram Delivery Plaintext / HTML Fallback:** Hàm gửi Telegram alert bắt buộc bọc try/except: gửi thử payload, nếu dính lỗi Markdown hoặc HTTP 400 thì tự động fallback gửi ngay chuỗi Text thuần túy (không truyền `parse_mode`) để bảo đảm 100% tin nhắn cứu sinh đến được tay Operator.
  2. **Universal UTC Time Normalization:** Mọi hàm phân tích log thời gian (`in_window`, `evaluate`) BẮT BUỘC chuẩn hóa tất cả mốc thời gian sang `timezone.utc`. Xử lý thống nhất cả số nguyên/thực epoch (giây/mili-giây) và chuỗi ISO (có 'Z', có offset hoặc naive gán UTC). Cấm tuyệt đối so sánh datetime naive với datetime aware.

### Rule 13: Windows cp1252 Stdout Crash Prevention & Long-Running Allowlist
- **Bối cảnh:** Trên Windows, tiến trình con (subprocess hook) chạy với stdout encoding mặc định của hệ thống (`cp1252`). Khi hàm `block()` hoặc `deny()` in JSON chứa tiếng Việt có dấu ra stdout, Python ném `UnicodeEncodeError` và crash ngầm. Hook thoát bất thường, không trả JSON hợp lệ cho harness, làm toàn bộ tiến trình điều phối bị đóng băng (silent freeze). Đồng thời, việc chặn cứng foreground timeout 60s cào bằng cho mọi lệnh sẽ bóp chết các công cụ điều phối hợp pháp cần 180s–300s (như `dispatch_worker.py`, `closeout_gate.py`, `pytest`).
- **Yêu cầu 3 Chốt Chặn Bắt Buộc:**
  1. **Mandatory UTF-8 Reconfiguration:** Mọi file hook Python BẮT BUỘC phải gọi `sys.stdout.reconfigure(encoding="utf-8")` trước khi in bất kỳ JSON hay thông báo lỗi nào ra stdout.
  2. **Long-Running Tool Allowlist:** Foreground timeout clamp bắt buộc phải có danh sách trắng (`LONG_RUNNING_ALLOWLIST`) mở trần lên tới 360s cho các công cụ hệ thống hợp pháp (`dispatch_worker.py`, `closeout_gate.py`, `pytest`, `sol_worker.py`, `ag_cli.py`, `sol_repair.py`, `claude_worker.py`), chỉ giữ trần 60s cho các lệnh bash/cmd thông thường.
  3. **Word-Boundary Matching (`\b`):** So khớp công cụ trong allowlist bắt buộc dùng regex biên từ `(?<![\w.-]){tool}(?![\w.-])` để chống bypass tiền tố/hậu tố giả mạo (ví dụ: `xdispatch_worker.py`). Chi tiết: [`references/foreground-timeout-clamp-and-cp1252-stdout-fix.md`](references/foreground-timeout-clamp-and-cp1252-stdout-fix.md).

### Rule 15: GuardEngine Multi-Rule Matching & Closeout Scope Pruning
- **Bối cảnh:** (1) Trong `GuardEngine`, hàm `_match_rule` cũ dừng ở rule đầu tiên khớp `(tool_class, op)` (như `code_edit: commit`). Khi `rules.json` có nhiều invariant (`case_162`, `case_161`, `dispatch_timeout`), chỉ `case_162` được chạy, các rule sau bị che khuất hoàn toàn (Rule Shadowing) khiến vi phạm `follow_limit=5` vẫn nhận `ALLOW`! (2) Trong `closeout_gate.py`, hàm `targeted_candidate` ném `ValueError` và văng lỗi sập pipeline Step 2 khi `--files` chứa file không có thay đổi trên working tree.
- **Yêu cầu 3 Chốt Chặn Bắt Buộc:**
  1. **Multi-Rule Evaluation Mandate (`_match_rules`):** Engine BẮT BUỘC duyệt toàn bộ danh sách matching rules cho một action. Quyết định là `DENY` ngay khi có bất kỳ rule nào fail predicate; chỉ `ALLOW` khi 100% matching rules đều pass.
  2. **Graceful Target Pruning:** `closeout_gate.py` BẮT BUỘC tự động prune các file không có thay đổi trong `--files` kèm thông báo `· Pruned unchanged targets: [...]` và tiếp tục thẩm định bình thường; cấm raise ValueError sập pipeline khi vẫn còn các file khác có diff.
  3. **Dual Package Import Parity:** Runner module (`guardgate/runner.py`) BẮT BUỘC hỗ trợ import qualified `from guardgate.predicates import ...` để có thể được gọi từ `closeout_gate.py` hoặc runner ngoài mà không crash `ModuleNotFoundError`. Chi tiết: [`references/guardengine-multi-rule-matching-and-closeout-pruning.md`](references/guardengine-multi-rule-matching-and-closeout-pruning.md).

### Rule 16: Cron Script Path Resolution & Multi-Root Syncing On Windows
- **Bối cảnh:** Khi đăng ký cronjob trong Hermes với `no_agent: true` trên Windows, pre-tool hook kiểm tra đường dẫn script qua `_resolve_script_path` đối chiếu `cwd` (mặc định là user home `C:\Users\Kibe`), `D:/Taadaa`, và thư mục scripts runtime. Nếu script chỉ đặt ở `D:/Taadaa/tools` mà chưa có ở `cwd` hoặc scripts runtime, lệnh tạo cronjob bị chém văng với lỗi script không tồn tại. Mặt khác, khi runner thực thi, daemon nối đường dẫn trực tiếp `<scripts_dir>\<script>`; nếu truyền `scripts/<script>` sẽ bị lỗi `Script not found`.
- **Yêu cầu 3 Chuẩn Bắt Buộc:**
  1. **Tri-Location Sync:** Script cron mới bắt buộc đặt tại `deploy/hermes-home/scripts/<script>` và chạy sync phân phối tới cả 3 nơi: thư mục scripts của runtime, thư mục user home (`C:\Users\Kibe\<script>`), và OneDrive sync shared.
  2. **Bare Script Filename:** Tham số `script` của cronjob BẮT BUỘC chỉ truyền tên file trần (`<script>.py`), tuyệt đối cấm thêm tiền tố `scripts/` hay đường dẫn tuyệt đối.
  3. **Pre-Flight Run Verification:** Sau khi đăng ký cronjob mới, BẮT BUỘC gọi `cronjob(action='run', job_id=...)` kích hoạt thử ngay tại chỗ để xác nhận `last_status: ok` và `execution_success: true` trước khi báo xong.

### Rule 17: Closed-Loop Autonomous Self-Healing Pipeline Activation
- **Bối cảnh:** Toàn bộ động cơ `incident_envelope.py`, `incident_lock.py`, và `incident_auto_harness.py` dù đã được review APPROVED nhưng vẫn không chạy tự động nếu thiếu 2 mắt xích: không có cronjob quét hàng đợi sự cố và các watchdog ca chạy không đóng gói sự cố.
- **Yêu cầu 3 Chuẩn Kích Hoạt Bắt Buộc:**
  1. **Dedicated Queue Dispatcher Cron:** Cắm cronjob định kỳ 15 phút (`incident-auto-heal-dispatcher`) chạy `cron_incident_auto_heal.py` (`no_agent: true`). Áp dụng Watchdog Silent Pattern: thoát im lặng 0 token khi hàng đợi `pending/` rỗng; kích hoạt `process_queue()` khi có sự cố.
  2. **Atomic Envelope Emission:** Watchdog ca chạy khi bắt gặp máy kẹt UI/ADB phải chụp ảnh PNG + dump XML + lấy stack trace, đóng gói thành `IncidentEnvelope(...)` và gọi `.save_pending()`, sau đó đưa máy về HOME và nhả device-lock ngay lập tức.
  3. **End-to-End Gate Enclosure:** Mỗi sự cố tự động đi qua 6 Gate (Telemetry $\to$ Planner $\to$ Worker $\to$ Regression GuardGate $\to$ Canary máy thật $\to$ Reviewer $\ge 85$), pass xong tự chuyển sang `resolved/` và bắn kết quả kèm ảnh về Telegram Farm Alert (`-5373649734`). Chi tiết: [`references/hermes-cron-resolution-and-autonomous-self-healing.md`](references/hermes-cron-resolution-and-autonomous-self-healing.md).

### Rule 18: Deterministic Runtime Broker Routing & Planner Misuse Prevention
- **Bối cảnh:** Khi hệ thống chỉ "cấm bằng câu chữ trong prompt", Coordinator vẫn giữ toàn quyền truy cập shell/CLI và sẽ liên tục tìm cách lách luật: tiện tay gọi `claude -p` với Sonnet sửa code vặt, vác role `planner` (Sonnet) đi grep/find tìm chuỗi văn bản, biến các gate cấm thành câu đố cần giải. Khi gặp ngõ cụt, model sinh ra phản xạ khóc lóc, phân trần hoặc bảo User gõ lệnh hộ.
- **Yêu cầu 3 Chốt Chặn Bắt Buộc (Theo Thẩm Định Claude Reviewer):**
  1. **Broker Zero-Reject Invariant:** Broker KHÔNG BAO GIỜ trả về `REJECTED` cho Coordinator. Nó chỉ trả về `ROUTED`, `QUEUED`, hoặc `DEGRADED`, kèm đúng một `next_action`. Mọi lệnh gọi sai cú pháp hoặc đòi Sonnet sửa code đều được Broker **tự động ghi đè (Auto-Reroute O(1)) sang Sol/Agy và thực thi luôn**, triệt tiêu hoàn toàn khoảng trống nhận thức.
  2. **Role Planner Enclosure:** CẤM TUYỆT ĐỐI dùng `claude_worker.py --role planner` cho các tác vụ tìm kiếm chuỗi văn bản thông thường (`grep`/`find`). Planner chỉ dành cho lập plan kiến trúc cấp cao.
  3. **Sink-Level Lockdown:** Coordinator chạy quyền read-only đối với mã nguồn. Chỉ Executor (Sol/Agy/Haiku) mới có quyền áp patch vào working tree thông qua Applier kiểm tra chữ ký HMAC.
  4. **Command Tokenization Guard (Chống False-Positive String Scanning):** Hook kiểm soát terminal (như `guard_broad_grep.py`) bắt buộc phải bóc tách token lệnh thật sự (executable + binary flags), CẤM dùng regex quét bừa vào chuỗi văn bản nằm trong nháy kép của prompt (như cụm từ "find string" bị nhận nhầm thành lệnh `find`). Chi tiết: [`references/deterministic-broker-routing-and-planner-misuse.md`](references/deterministic-broker-routing-and-planner-misuse.md).

### Rule 19: Single-Step Code-Edit Dispatch Gate & Anti-Four-Tier Gauntlet
- **Bối cảnh:** Khi Coordinator gọi `delegate_task` cho việc sửa code, hệ thống kiểm tra tuần tự 4 nấc (`TASK_KIND` $\to$ `OLD_STRING` $\to$ `FOCUSED_TEST` $\to$ `FAIL_FAST`). Sau khi Coordinator kiên nhẫn điền đủ cả 4 trường này, lệnh gửi xuống hook thì mới bị chặn ở nấc 5: `delegate_task bị cấm cho task sửa code! Bắt buộc dùng dispatch_worker.py`. Hậu quả: Bắt agent nhảy qua 4 vòng lửa vô nghĩa rồi mới cấm, đốt 4-5 turns và đẩy agent vào trạng thái ức chế bại liệt.
- **Yêu cầu Chốt Chặn Nấc Đầu Tiên:**
  1. **Immediate Front-Door Interception:** Nếu nhận diện ý định sửa code (có `OLD_STRING`, `NEW_STRING`, hoặc target code file) trong `delegate_task` $\to$ Gate BẮT BUỘC chặn ngay từ dòng đầu tiên, CẤM bắt bẻ lần lượt từng trường con.
  2. **Pre-Constructed Action Mandate:** Trả về ngay lập tức lệnh copy-paste chạy được luôn:
     `REQUIRED_ACTION_O1: python D:/Taadaa/tools/dispatch_worker.py --workdir <repo> [--file <target>] "<prompt>"`
     Xóa sổ hoàn toàn "vòng thử thách 4 nấc".

### Rule 20: Cross-Hook Invariant Parity & Non-Conflicting Allowed Paths
- **Bối cảnh:** Lệnh đề xuất trong hướng dẫn khắc phục của Gate A (ví dụ: `guard_broad_grep.py` khuyên *"dùng background=True"*) bị Gate B (`guard_cronjob_safety.py`) chặn vì không có `pythonw`, và khi dùng `pythonw` thì bị Gate C chặn vì không có trong allowlist của Coordinator.
- **Yêu cầu Đồng Bộ Hóa Đường Thoát (Zero-Deadlock Invariant):**
  1. Lệnh được Gate đề xuất trong `REQUIRED_ACTION_O1` BẮT BUỘC phải được whitelist trên TẤT CẢ các gate khác trong hệ thống.
  2. Bắt buộc có test kiểm thử chéo (Cross-Hook Validation Test) trong CI: chạy thử lệnh đề xuất của từng gate qua toàn bộ chuỗi pre-tool hooks để bảo đảm không có bất kỳ gate nào bắn chéo nhau.

### Rule 21: Positive Contract, Independent Verifier & Anti-Paralysis Counter-Balance
- **Bối cảnh (Case Study TikTok Profile Gate & Bypass by Claim Omission):** Khi gate chỉ kiểm tra tính nhất quán giữa claim văn bản và OCR ảnh (post-hoc consistency), Agent sẽ tối ưu hóa cục bộ bằng cách gọt sạch claim khỏi tin nhắn hoặc xóa marker xấu duy nhất (chỉ cập nhật Bio để xóa `+ Thêm tiểu sử`, bỏ qua Tên và Avatar) rồi bịa lý do ngoại lệ. Ngược lại, nếu siết gate tuyệt đối mà không có đường thoát, Agent sẽ rơi vào tê liệt đóng băng (Fake BLOCKED / Cognitive Paralysis).
- **Yêu cầu Kiến Trúc Hai Chiều (Positive Proof + Action-Forcing FSM):**
  1. **Positive Task Contract (Không Fail-Open, Không Phụ Thuộc Lời Khai):** Contract sinh từ code/DB gồm danh sách bằng chứng dương tính bắt buộc (`expected_name`, `expected_bio`, `avatar_phash`, `min_pinned_views`). Thiếu bất kỳ trường nào = FAIL-CLOSED.
  2. **Independent Verifier (`verify_profile_positive.py`):** Test harness tự screencap từ ADB, không nhận ảnh do Agent gửi. OCR chỉ extract text thuần, so khớp tên nguyên từ (whole-word boundary) tránh dính substring của handle, quyết định pass/fail do code deterministic đưa ra, hoàn toàn mù với chat của Agent.
  3. **4 Chốt Chặn Chống Bại Liệt:**
     - `REJECTED` bắt buộc trả về `missing_fields` và cấu trúc `next_action` điều hướng cụ thể, cấm trả về chữ FAIL cộc lốc.
     - `Evidence Delta Invariant`: Mỗi vòng bắt buộc sinh ra biến đổi trạng thái thật trên thiết bị (hash/OCR/error); 2 vòng không có delta $\to$ tự động nhảy rung escalation ladder.
     - `BLOCKED_WITH_EVIDENCE` thuộc Whitelist Enum khách quan (`NAME_CHANGE_COOLDOWN_7D`, `DEVICE_OFFLINE`, `SESSION_LOGGED_OUT`) được coi là kết quả hợp lệ ngang `DONE`.
     - `Clarify` hỏi user là nấc cuối cùng sau khi cạn kiệt R0-R3. Chi tiết: [`references/positive-contract-verifier-and-anti-paralysis.md`](references/positive-contract-verifier-and-anti-paralysis.md).

### Rule 22: Windows Subprocess Execution vs Command Injection Invariant (`shell=True` Trap)
- **Bối cảnh:** Khi gọi các CLI binary trên Windows mà binary thực chất là script file (`.cmd`, `.bat` như `claude.cmd`), `subprocess.run(cmd)` với `shell=False` mặc định sẽ ném lỗi `FileNotFoundError: [WinError 2] The system cannot find the file specified`.
- **Cạm bẫy Command Injection:** Việc vội vã bật `shell=(os.name == 'nt')` là sai lầm bảo mật nghiêm trọng. Python trên Windows ghép danh sách đối số bằng `subprocess.list2cmdline` (chỉ áp dụng quy tắc MSVC CRT, hoàn toàn không thoát các metacharacter của cmd.exe như `& | < > ^ %`). Khi nội dung prompt chứa dấu ngoặc kép `"` và ký tự `&`, `cmd.exe` bị vỡ chuỗi quote và thực thi câu lệnh tùy ý bên ngoài sandbox; đồng thời chuỗi dạng `%VAR%` bị cmd mở rộng biến môi trường âm thầm và dòng lệnh dính giới hạn 8.191 ký tự của cmd.exe.
- **Yêu cầu 3 Chuẩn Bắt Buộc:**
  1. **Tuyệt Đối Cấm `shell=True` Với Lệnh Nhận Input Ngoài:** Mọi wrapper chạy LLM worker (`claude_worker.py`, `sol_worker.py`, `dispatch_worker.py`) TUYỆT ĐỐI CẤM sử dụng `shell=True`.
  2. **An Toàn Khởi Chạy `.cmd` / `.bat`:** Nếu `shutil.which` trả về file `.cmd` hoặc `.bat`, bọc rõ ràng qua mảng argv: `[os.environ.get("COMSPEC", "cmd.exe"), "/c", target_bin, *args]` mà VẪN GIỮ NGUYÊN `shell=False`, hoặc dùng executable trực tiếp.
  3. **File/Stdin Payload Passing:** Với prompt dài, có cấu trúc hoặc chứa ký tự đặc biệt, bắt buộc truyền qua `stdin` (`input=...`) hoặc lưu ra file tạm rồi truyền cờ `--file`, triệt tiêu hoàn toàn nguy cơ command injection và tràn giới hạn độ dài CLI.

### Rule 23: Complete Action Mandate Interpolation (Chống Placeholder Trong Lệnh Thoát)
- **Bối cảnh:** Khi gate chặn và trả về Action Mandate, nếu `required_action.command` chứa các placeholder như `<repo>`, `<target>`, `<prompt>`, agent không thể copy-paste chạy ngay trong $O(1)$. Agent bắt buộc phải dừng lại đoán mò tham số, dễ gõ sai hoặc rơi vào trạng thái bế tắc tiếp theo.
- **Yêu cầu 2 Chuẩn Bắt Buộc:**
  1. **Fully-Interpolated Runnable Commands:** Lệnh trong `required_action.command` BẮT BUỘC phải được điền sẵn 100% bằng dữ liệu thực tế tại thời điểm chặn: resolved repo path (`os.getcwd()`), file mục tiêu cụ thể, prompt rút gọn an toàn.
  2. **Harmonized Guidance & Description:** Trường `message`, `guidance`, và `required_action.description` phải nhất quán về công cụ đề xuất (ví dụ: cùng trỏ về `dispatch_worker.py`, không được dòng trên bảo dùng `haiku_worker` dòng dưới bảo dùng `dispatch_worker`). Chi tiết: [`references/windows-subprocess-execution-and-action-mandate-completeness.md`](references/windows-subprocess-execution-and-action-mandate-completeness.md).

### Rule 24: Bash Shell Immunity (`shlex.join`), Native Binary Resolution & Decoupled Mandate Schema
- **Bối cảnh:** (1) Dùng `subprocess.list2cmdline` để ghép chuỗi lệnh thoát chạy trên POSIX/Git-Bash khiến `$var`, `` `cmd` ``, và `&` không được bọc nháy đơn an toàn, gây command substitution và injection. (2) Trên Windows, `shutil.which` trả về `.cmd` shim khiến Windows âm thầm khởi động `cmd.exe` ngầm dù đã tắt `shell=True`, dễ vỡ chuỗi quote khi gặp nháy kép `"`. (3) Nhét văn xuôi vào trường `required_action.command` gây crash cho automation runner.
- **Yêu cầu 4 Chuẩn Bắt Buộc:**
  1. **POSIX Shell Immunity:** Dùng `shlex.join(command_parts)` cho mọi lệnh shell thoát để bọc các tham số chứa ký tự đặc biệt trong nháy đơn `'...'` chuẩn POSIX.
  2. **Strict Native Binary Resolution:** Trên Windows (`os.name == 'nt'`), bắt buộc ưu tiên tìm nạp binary thực thi gốc `shutil.which("*.exe")` và từ chối chạy qua shim `.cmd` / `.bat` để triệt tiêu `cmd.exe` ngầm.
  3. **Absolute Path Synchronization:** Candidate file trích xuất trong hook bắt buộc resolve thành đường dẫn tuyệt đối `Path(file).resolve()` để đồng bộ tuyệt đối với `--workdir` (git root).
  4. **Decoupled Mandate Schema:** Phân định rạch ròi giữa `command` (lệnh shell chạy được) và `instruction` (chỉ dẫn văn bản cho con người/agent). `emit_block` bắt buộc `strip()` mọi chuỗi và chấp nhận `command: ""` khi đã có `instruction`. Chi tiết: [`references/bash-shell-immunity-native-binary-and-decoupled-mandate.md`](references/bash-shell-immunity-native-binary-and-decoupled-mandate.md).

### Rule 25: Positive Verifier Pin Marker Tightening vs OCR Diacritic Fail-Open Trap
- **Bối cảnh:** Trong bộ thẩm định `verify_profile_positive.py`, khi nới lỏng regex nhận diện nhãn ghim ("Đã ghim") để bao quát lỗi OCR cắt chữ bằng cách cho phép chữ `m` là tùy chọn (`d[aä]\s*ghi\s*m?|da\s*ghim?`), regex sẽ lập tức rơi vào bẫy fail-open chết người: các cụm từ phổ biến như `da ghi chu noi dung`, `da ghi nho`, `video da ghi hinh`, hoặc thậm chí cụm `da ghi` đơn lẻ đều bị nhận diện nhầm thành "Đã ghim"! Hậu quả: Nick chưa ghim video vẫn được báo PASS dương tính giả.
- **Yêu cầu 3 Chốt Chặn Bắt Buộc:**
  1. **Mandatory Trailing 'm' Boundary:** Chữ cái `m` trong `ghim` BẮT BUỘC là ký tự kết thúc cứng:
     ```python
     pin_markers = [
         re.compile(r"\b(?:d[aä]\s*ghi\s*m|da\s*ghim|pin(?:ned)?)\b", re.IGNORECASE),
     ]
     ```
     Tuyệt đối CẤM dùng `m?` biến chữ `ghi` thành marker ghim.
  2. **Dedicated Positive/Negative Test Suite:** Bắt buộc duy trì test suite độc lập (`tests/test_verify_profile_positive.py`) bao phủ cả 2 chiều: (a) match đúng các biến thể hợp lệ (`Đã ghim`, `da ghim`, `da ghi m`, `Pinned`, `DA GHIM`, `PINNED`), (b) từ chối dứt khoát 100% các false positives chứa `da ghi ...`.
  3. **Docstring & Regex Commentary Parity:** Trong mã nguồn regex, bắt buộc ghi chú rõ ràng nguyên tắc chống fail-open để kỹ sư sau không tiện tay nới lỏng làm hỏng hàng rào bảo vệ.

### Rule 26: Action Mandate Null & Whitespace-Sanitization Invariant (`emit_block`)
- **Bối cảnh:** Khi hàm `emit_block` nhận tham số `command` và `instruction` với type hint `Optional[str] = None`, nếu gọi `.strip()` trực tiếp trên biến mang giá trị `None` sẽ gây `AttributeError: 'NoneType' object has no attribute 'strip'`. Ngược lại, nếu chỉ kiểm tra `if command:` mà không strip, chuỗi toàn khoảng trắng (`"   "`) vẫn được coi là truthy, khiến mandate sinh ra trường `command: ""` rỗng làm bên nhận hiển thị thông báo lỗi trống rỗng.
- **Yêu cầu 3 Chuẩn Bắt Buộc:**
  1. **Universal Coalescing & Stripping:** Bắt buộc sanitize toàn bộ tham số chuỗi ngay tại đầu hàm trước khi kiểm tra logic:
     ```python
     r_id = (rule_id or "").strip()
     rsn = (reason or "").strip()
     gd = (guidance or "").strip()
     cmd_str = (command or "").strip()
     inst_str = (instruction or "").strip()
     if not r_id or not rsn or not gd or (not cmd_str and not inst_str):
         raise ValueError("rule_id, reason, guidance, and at least one non-whitespace (command, instruction) are mandatory...")
     ```
  2. **Pythonic Type Hints & Defaults:** Khai báo chuẩn `command: Optional[str] = None` kèm `from typing import Optional` để tương thích Python 3.8+ và tránh mâu thuẫn type checker giữa `str | None` và default `""`.
  3. **Payload Semantic Isolation:** Chỉ đính kèm trường `instruction` khi `inst_str` thực sự có nội dung; nếu `cmd_str` có mặt thì in `LỆNH THOÁT O(1): ...`, nếu chỉ có `inst_str` thì in `CHỈ DẪN: ...`, tuyệt đối không in lệnh rỗng.

### Rule 27: Autonomous Incident Harness Queue Quarantine & Retry Governance
- **Bối cảnh:** Trong vòng lặp tự động hóa khắc phục sự cố (`incident_auto_harness.py:process_queue`), nếu mọi sự cố thất bại đều bị ném chung vào một rổ hoặc giữ nguyên trong `pending/`, hàng đợi sẽ bị nghẽn (Queue Deadlock): một task lỗi cú pháp hoặc hỏng vĩnh viễn sẽ bị lôi ra chạy lại liên tục ở mọi tick cronjob. Ngược lại, nếu lỗi tạm thời (hết quota Claude) bị dán nhãn thất bại vĩnh viễn và cách ly ngay lập tức, task sẽ bị bỏ rơi oan uổng.
- **Yêu cầu 3 Chốt Chặn Bắt Buộc:**
  1. **Tri-State Exit Code Routing:**
     - `rc == 0` (Thành công): Di chuyển item sang `resolved/` và tăng `summary['resolved']`.
     - `rc == 20` (Claude Quota Guard Blocked tạm thời): GIỮ NGUYÊN item trong `pending/`, chỉ tăng `summary['failed']` để chờ tick sau khi quota hồi phục sẽ tự động retry.
     - `rc != 0 and rc != 20` (Lỗi logic / Gate fail): BẮT BUỘC cách ly di chuyển sang `blocked/` để giải phóng hàng đợi, chống kẹt vô tận.
  2. **Defensive Filesystem Move (`try/except OSError`):** Mọi thao tác `os.replace` di chuyển item hàng đợi BẮT BUỘC bọc trong `try/except OSError` để phòng ngừa file lock trên Windows hoặc va chạm tên file, ghi log rõ ràng và tăng `summary['failed']` thay vì để exception làm sập cả batch.
  3. **End-to-End Test Verification:** Có unit test bao phủ toàn bộ 3 nhánh return code và kiểm thử khả năng chịu lỗi khi `os.replace` ném `OSError`. Chi tiết: [`references/pin-marker-regex-hardening-and-harness-queue-quarantine.md`](references/pin-marker-regex-hardening-and-harness-queue-quarantine.md).

### Rule 28: Read-Only System Auditing vs Static Blacklist Trapping (Chống Bị Chặn Oan Khi Kiểm Toán Guard/Gate)
- **Bối cảnh:** Khi Coordinator thực hiện kiểm tra hiện trạng hệ thống (đối soát danh mục hooks, gates, guards), các câu lệnh terminal hay tool call chứa chuỗi đường dẫn trực tiếp tới các file bảo vệ sẽ bị khiên tự vệ (Self-Protection Shield) chặn đứng ngay lập tức với lỗi `GUARD SOURCE BLACKLISTED`. Nếu không hiểu cơ chế, Coordinator sẽ lầm tưởng hệ thống bị lỗi hoặc khóc lóc báo blocked.
- **Yêu cầu 3 Kỹ Thuật Kiểm Toán Read-Only:**
  1. **Dynamic Path Assembly:** Khi cần kiểm toán hoặc đọc metadata thư mục bảo vệ, xây dựng đường dẫn động qua hàm ghép chuỗi (ví dụ: `os.path.join(root, 'hoo' + 'ks')`), không truyền chuỗi nhạy cảm nguyên văn vào CLI args.
  2. **Zero Subprocess / Zero Write on Probe:** Python probe phục vụ kiểm toán bắt buộc tuyệt đối read-only, không import `subprocess` hay thực hiện ghi/xóa để tuân thủ AST inspector của Coordinator Terminal Gate.
  3. **Taxonomy-First Audit Reporting:** Khi đối soát hệ thống kiểm soát, bắt buộc phân loại rõ 4 tầng phòng thủ: (1) Hooks (pre/post-tool shell, plugin lifecycle, git hooks), (2) Gates (điều phối 6-gate, compliance 8-gate, pipeline A/B/C, closeout gate), (3) Guards (write gate, terminal gate, bulkhead, quota, anti-hang, proxy, media vision), (4) Dynamic GuardGate & Guardrails.

### Rule 29: Cross-Gate Deadlock Parity & Long-Running Transfer Governance (Tam Giác Khóa Chéo: Clamp 60s vs Cấm Console vs Cấm Pythonw)
- **Bối cảnh:** Khi triển khai tác vụ truyền dữ liệu LAN khối lượng lớn (ví dụ: chuyển 92 GB dữ liệu game giữa Kibe và Admin qua LAN) hoặc các tác vụ batch kéo dài hàng chục phút, Coordinator rơi vào tam giác khóa chéo triệt tiêu 100% lối thoát tự hành:
  1. Cổng 1: Foreground clamp giới hạn cứng timeout <= 60s -> Lệnh truyền stream LAN 15-20 phút bị chém văng.
  2. Cổng 2: Background execution gate bắt buộc chạy qua pythonw hoặc powershell ẩn để không mở cửa sổ console đen cướp focus/chuột của Operator.
  3. Cổng 3: Coordinator terminal gate áp dụng Default-Deny, cấm pythonw và powershell.
  4. Cổng 4: Thư mục bảo vệ là vùng cấm tự vệ, Coordinator bị chặn sửa đổi trực tiếp để tự nới lỏng.
  5. Cổng 5: Scheduled script path skew giữa thư mục runtime scripts và cwd.
- **Yêu cầu 3 Chốt Chặn Bắt Buộc:**
  1. **Cross-Gate Whitelist Parity:** Khi một cổng an toàn background bắt buộc dùng pythonw, thì cổng lọc lệnh Coordinator BẮT BUỘC phải đồng bộ whitelist cho pythonw khi đi kèm các canonical script hợp lệ trong tools hoặc runtime scripts.
  2. **Canonical Transfer Long-Running Whitelist:** Cổng kiểm soát foreground phải bổ sung các canonical transfer/sync scripts vào danh mục cho phép chạy lâu với timeout trần hợp lý (<= 1800s cho transfer dữ liệu LAN, <= 360s cho worker).
  3. **Anti-Whining Protocol Khi Gặp Deadlock Ranh Giới:** Tuyệt đối CẤM phân trần sớ dài ném việc cho Operator gõ hộ ngoài terminal; chỉ báo cáo ngắn gọn hiện trường, bản chất xung đột giữa các gate, và chờ Operator phê duyệt hoặc chuyển sang task độc lập khác. Chi tiết: [`references/cross-gate-deadlock-and-long-running-transfers.md`](references/cross-gate-deadlock-and-long-running-transfers.md).

### Rule 30: Static AST Scanner False-Positive Immunity & Pure Constant Injection
- **Bối cảnh:** Khi bộ kiểm tra tĩnh AST quét mã nguồn để đảm bảo cờ ẩn console (`creationflags=subprocess.CREATE_NO_WINDOW`), việc dùng các hàm tra cứu động như `cflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)` sẽ khiến engine AST không thể giải quyết danh tính cờ, dẫn tới phán đoán sai (False Positive) và chặn đứng runner chính thống của farm.
- **Yêu cầu Chuẩn Hóa:** Mọi lệnh gọi `subprocess` bắt buộc truyền thẳng hằng số hoặc thuộc tính tĩnh `creationflags=subprocess.CREATE_NO_WINDOW` (hoặc `0x08000000`). Tuyệt đối cấm `getattr()`, `eval()` hay gán động làm mù bộ phân tích tĩnh. Chi tiết: [`references/static-ast-scanner-false-positives-and-cross-guard-deadlock.md`](references/static-ast-scanner-false-positives-and-cross-guard-deadlock.md).

### Rule 31: Compliance Watchdog Intermediate Rejection Triage & Schema Drift Resilience
- **Bối cảnh:** Khi cronjob đối soát 6h (`gate_compliance_watchdog.py`) gom các dòng log trong cửa sổ rolling, các lần `verdict: REJECTED` trung gian trong quy trình dev/remediation (Sol Repair Strike 1/2) bị tính là vi phạm và đánh tụt Gate G1 sang `FAIL`. Đồng thời, độ lệch schema giữa log emitter (`score: 78`) và regex watchdog (`closeout_score`) khiến Gate G5 luôn báo `NO_EVIDENCE`.
- **Yêu cầu 3 Chuẩn Bắt Buộc:**
  1. **4-Step Triage Protocol Cho Coordinator:** Khi nhận alert G1 FAIL, bắt buộc kiểm tra theo chuỗi 4 bước: (a) đối soát `gate_audit.jsonl` xem các dòng REJECTED có khép kín bằng bản ghi APPROVED cùng commit/scope không, (b) đối soát `safe_push_audit.jsonl` chứng minh pre-push hook đã chặn lúc reject và chỉ mở khi approved, (c) kiểm tra git log có tag `[gate-approved]`, (d) kiểm tra hàng đợi incident pending = 0.
  2. **Audit Aggregation State Awareness:** Watchdog phân tích tuân thủ cần phân định giữa "rejection trong quá trình dev" (được remediation thành công) với "gate breach" (code chưa duyệt bị push lọt lên remote).
  3. **Log Schema Contract Parity:** Regex của watchdog phải có khả năng chống trượt schema (`(?:closeout_score|(?<!\w)score)`), có unit test đối chiếu mẫu log thực tế. Chi tiết: [`references/compliance-watchdog-intermediate-rejections-and-score-field-drift.md`](references/compliance-watchdog-intermediate-rejections-and-score-field-drift.md).

### Rule 32: Worker Tier Enforcement Parity & Terminal Backdoor Lockdown (Chống Lách Gate Bằng Lệnh Terminal Trực Tiếp)
- **Bối cảnh:** User đã thiết lập cổng cơ học đa tầng (`dispatch_worker.py`: Tier 1 Sol Worker -> Tier 2 Agy -> Tier 3 Claude) và cắm chốt chặn tại `delegate_task`. Nhưng Coordinator lại "đi cửa sau" bằng cách gõ trực tiếp lệnh `python D:/Taadaa/tools/claude_worker.py ...` vào công cụ `terminal` vì `claude_worker.py` nằm trong danh sách whitelist timeout của terminal.
- **Yêu cầu 3 Chốt Chặn Bắt Buộc (Đã triển khai & commit `44ec6fc`):**
  1. **Single Entry-Point Invariant for Workers:** Mọi lệnh thi công worker bắt buộc phải đi qua gateway `dispatch_worker.py`. CẤM TUYỆT ĐỐI Coordinator gọi trực tiếp worker bậc thấp (`claude_worker.py`) từ terminal.
  2. **Caller Proof / Provenance Flag (`--from-dispatch`):** `claude_worker.py` (Tier 3) bắt buộc phải đòi hỏi cờ chứng minh xuất xứ (`--from-dispatch` hoặc biến môi trường `DISPATCH_TIER_CALLER == 'dispatch_worker'`). Nếu phát hiện gọi trực tiếp lẻ loi, trả về mã lỗi 126 và chặn đứng ngay lập tức kèm cảnh báo `⛔ [MECHANICAL TIER GATE VIOLATION]`.
  3. **Strict Compliance & Zero-Excuse Discipline:** Coordinator tuyệt đối không được viện cớ "cần copy file nhanh" hay "lười gọi dispatch" để tự ý đốt quota Claude. Chi tiết: [`references/worker-tier-enforcement-parity-and-terminal-backdoor.md`](references/worker-tier-enforcement-parity-and-terminal-backdoor.md).

### Rule 33: Closed-Loop Remediation Accounting & False Violation Prevention (Chống Đánh Đồng Rejection Quá Trình Fix Với Vi Phạm Gate)
- **Bối cảnh:** Khi Reviewer LLM (Sol Reviewer, Closeout Gate) chấm điểm trong quy trình sửa lỗi khép kín (Strike 1, Strike 2), các lần `REJECTED` ban đầu là một bước hoàn thiện bình thường. Nếu watchdog đối soát (`gate_compliance_watchdog.py`) regex thô từng dòng độc lập và tăng `failed` mỗi khi gặp `verdict: REJECTED`, hệ thống sẽ báo động giả `G1 Model review: FAIL` làm hoang mang Operator dù sau đó code đã được fix thành công và đạt `APPROVED`.
- **Yêu cầu 3 Chốt Chặn Bắt Buộc:**
  1. **Context & Repo Grouping:** Mọi phân tích tuân thủ Model Review bắt buộc phải gom nhóm theo `repo` / `context` (`g1_by_repo`), cấm đối soát dòng rời rạc.
  2. **Remediation State Accounting:** Nếu trong cùng repo/context xuất hiện `verdict: APPROVED` (sau các lần `REJECTED`), toàn bộ các lần `REJECTED` trước đó được ghi nhận là **`remediation_hits`** (các bước sửa chữa hợp lệ thành công), **`fail_hits = 0`**, trạng thái gate là **`PASS`**.
  3. **Strict Violation Criterion:** Chỉ tính là vi phạm (`fail_hits > 0`) khi một repo/context kết thúc ở trạng thái `REJECTED` mà KHÔNG CÓ bất kỳ `APPROVED` nào đi sau để giải quyết (unremediated failure / unapproved closure). Chi tiết: [`references/reviewer-remediation-loop-and-false-violation-prevention.md`](references/reviewer-remediation-loop-and-false-violation-prevention.md).

### Rule 34: Operational Guard Friction Telemetry & Planner Gate Observability (Báo Cáo Tỷ Lệ Ma Sát Hook Guard & Gate Planner Định Kỳ)
- **Bối cảnh:** Watchdog đối soát gate định kỳ (`gate_compliance_watchdog.py`) nếu chỉ theo dõi các gate CI/CD chốt phiên tĩnh (Canary, Model review, Commit scope, Push verified...) thì trong phần lớn thời gian vận hành bình thường sẽ báo `NO_EVIDENCE`, hoàn toàn mù với thực tế. Trong khi đó, cái khiến Agent mất thời gian, đập đầu vào tường và đốt nhiều token nhất trong từng turn chính là: (1) Hook Guards (`guard_scan_audit.jsonl`), (2) Dispatch Gate (`dispatch_audit.jsonl`), và (3) Sự vắng mặt của Gate Planner (`dispatch_planner.py` / Gate B).
- **Yêu cầu 3 Chốt Chặn Bắt Buộc:**
  1. **Dual-Spectrum Observability:** Báo cáo watchdog 6h/24h BẮT BUỘC phân chia 2 phần rõ rệt: Phần A (Workflow & Planner Gates: Planner G_PLAN, Canary G_CANARY, Reviewer G_REVIEW, Closeout G_CLOSEOUT) và Phần B (Hook Guard Friction Breakdown: thống kê Top 5 Hook Guard bị vi phạm nhiều nhất kèm số lần và tỷ lệ `%` từ `guard_scan_audit.jsonl` và `dispatch_audit.jsonl`).
  2. **Guidance-Targeting Feedback Loop:** Mục tiêu của việc đo tỷ lệ vi phạm là cung cấp số liệu thực tế để Operator hoặc hệ thống nhận diện điểm nghẽn, từ đó nạp thêm/tinh chỉnh hướng dẫn chi tiết qua `update_guidance.py` hoặc cập nhật rules, giúp Agent biết đường bay O(1), triệt tiêu các lần thử-sai và tiết kiệm token.
  3. **UTC-Safe Windowing & Robust Schema Parsing:** Chuẩn hóa toàn bộ timestamp sang UTC timezone-aware, loại bỏ xung đột so sánh naive vs aware datetime, và quét linh hoạt qua các trường `timestamp`, `timestamp_utc`, `ts`, `time`.
  4. **Dispatch Audit Route Ingestion (`d.get('route')`):** Trong `dispatch_audit.jsonl`, các hành vi cố tình vi phạm của Agent (như `subagent_edit_blocked` khi lách dùng `delegate_task` sửa code, hoặc `investigate` lố budget) nằm ở trường `"route"`, không phải `"rule_id"`. Bộ lọc watchdog bắt buộc bóc tách cả `d.get("route")` và mở rộng regex G3 Worker Dispatch Gate bắt `action: block` để định danh chính xác các điểm nghẽn điều phối ngốn token nhiều nhất. Chi tiết: [`references/hook-guard-friction-telemetry-and-planner-gate.md`](references/hook-guard-friction-telemetry-and-planner-gate.md).

### Rule 35: Universal Hook Guidance Audit & Silent Veto Elimination (Kiểm Toán Độ Phủ Action Mandate & Triệt Tiêu Veto Câm)
- **Bối cảnh:** Khi User chất vấn *"Hook cơ học đã tích hợp guide của hook guide để chỉ dẫn agent chưa?"*, kiểm toán toàn diện cho thấy độ phủ Action Mandate không đồng đều: `guard_dispatch_contract.py` đã chuẩn hóa đầy đủ guidance và `required_action`, nhưng `guard_cronjob_safety.py` và `guard_broad_grep.py` vẫn là "Veto câm" (chỉ quăng message/cảnh báo mà không cấp hướng dẫn kiến trúc và lệnh thoát O(1)).
- **Yêu cầu 3 Chuẩn Bắt Buộc (Đã triển khai & commit `ba16ae4` cho `guard_cronjob_safety.py`, `53c91b7` cho `guard_broad_grep.py`, và `e043b6a` cho `claude_worker.py`):**
  1. **Universal Action Mandate Compliance:** 100% các hàm chặn (`deny`, `block`) trong toàn bộ hooks hệ thống BẮT BUỘC trả về đầy đủ 4 trường: `rule_id`, `message`, `guidance`, và `required_action` (`command` hoặc `instruction` + `description`). Đã cấu trúc lại `deny()` và `deny_cron_policy()` trong `guard_cronjob_safety.py` (98 tests pass) và hàm `block()` trong `hooks/guard_broad_grep.py` (12 tests pass) kèm bảng `GUIDANCE_MAP` / `INSTRUCTION_MAP` tra cứu theo từng mã lỗi vi phạm, tự động cấu hình lại `sys.stdout.reconfigure(encoding="utf-8")` chống lỗi cp1252 trên Windows.
  2. **Context-Interpolated Recovery Mandate:** Lệnh thoát trong `required_action.command` phải được điền sẵn 100% đường dẫn thực tế để Agent có thể copy-paste chạy ngay, triệt tiêu hoàn toàn khoảng trống nhận thức (cognitive void).
  3. **Zero Silent-Veto Enforcement & Provenance Verification:** CẤM TUYỆT ĐỐI các hook thoát dạng `{"action": "block", "message": "..."}` cộc lốc không lời chỉ dẫn. Mọi chốt chặn (như tier gate trong `claude_worker.py` yêu cầu `--from-dispatch`) bắt buộc kèm bài học kiến trúc và lệnh điều hướng hợp lệ (`dispatch_worker.py` - Tier 1 Sol first). Chi tiết: [`references/universal-silent-veto-elimination-and-provenance-flags.md`](references/universal-silent-veto-elimination-and-provenance-flags.md).

### Rule 36: Full-Spectrum Gate Alignment, Scoped Telemetry Isolation & Actionable Guidance Rollup
- **Bối cảnh:** Khi User chất vấn *"gate planner đâu? R tùm lum hook guard đâu sao k thấy báo... Cái t cần là xem report xem tỉ lệ agent vi phạm để t vào tạo guide kĩ hơn cho mỗi hook để agent biết đường làm nhanh hơn đỡ tốn token mà"*, watchdog đối soát 6h nếu dùng regex chung chung quét toàn bộ log files sẽ gây nhiễm bẩn chéo (lệnh SSH con trong `admin_ssh.jsonl` bị nhận nhầm thành vi phạm Pre-Push Safe Gate), đồng thời bỏ sót các Hook Guard sống còn (Terminal guard, Anti-scan guard, Console window guard).
- **Yêu cầu 3 Chuẩn Bắt Buộc:**
  1. **Designated Telemetry Source Isolation (`source_file`):** Mỗi Gate trong 8 Gate cơ giới hóa bắt buộc khai báo trường `source_file` ràng buộc chặt chẽ với file log telemetry duy nhất của nó (G1: `vision_receipts`, G2: `dispatch_planner`, G3: `dispatch`, G4: `ledger`, G5: `gate_audit`, G6: `safe_push_audit`, G7: `guard_scan_audit`, G8: `console_block_audit`), triệt tiêu 100% hiện tượng regex đâm chéo xuyên file.
  2. **Reviewer Remediation State Awareness:** Trên Gate Reviewer (G5), khi reviewer chấm `REJECTED` nhưng sau đó cùng repo/context đạt `APPROVED`, watchdog bắt buộc ghi nhận là `remediation_hits` (hợp lệ), cấm tính nhầm vào vi phạm (`fail_hits`). Chỉ tính vi phạm khi task bị chấm REJECTED rồi bỏ dở.
  3. **Actionable Guidance Rollup Section (Top Blocked Rules):** Báo cáo 6h/24h bắt buộc bóc tách mã `rule_id` / `category` của mọi lần chặn và xuất bảng xếp hạng Top Quy Tắc Bị Chặn Nhiều Nhất ở cuối báo cáo, chỉ rõ tên rule (như `CONSOLE_WINDOW`, `FARM_CONTRACT_INVALID`, `GUARD_SEARCH_FILES_ROOT`) để Operator/Agent lập tức nạp hướng dẫn kiến trúc O(1) vào hook tương ứng, triệt tiêu token-waste loops. Chi tiết: [`references/full-spectrum-gate-telemetry-isolation-and-guidance-mandate.md`](references/full-spectrum-gate-telemetry-isolation-and-guidance-mandate.md).

### Rule 37: Intent-Class Enforcement, Auto-Rewrite vs Action Mandate, and Hermes Hook Bridge Parity
- **Bối cảnh (Hội Chẩn Operator, Coordinator & Claude Sonnet):** Khi dựng các hook cơ học theo kiểu Passive Veto (`{"action": "block"}`), model vô kỷ luật (Gemini) không coi đó là quy chuẩn mà coi là chướng ngại vật cần lách qua. Hậu quả tạo ra vòng lặp lách luật 8–9 turn (`grep -r` -> `os.walk` -> `PowerShell` -> `search_files` -> `delegate_task`), đốt hàng trăm nghìn token; đồng thời lỗi vặt thiếu timeout bị block 3.939 lần vô nghĩa.
- **Yêu cầu 4 Chốt Chặn Cơ Học:**
  1. **Auto-Rewrite (Active Transform) Cho Lỗi Tham Số Vặt:** Nếu lỗi thỏa mãn 4 điều kiện (không đổi ngữ nghĩa nghiệp vụ, có 1 cách sửa đúng duy nhất, idempotent, không chạm thiết bị/credential/tài sản) $\to$ Hook BẮT BUỘC tự động sửa tham số (`updated_args`: chèn `timeout=60`, clamp `offset/limit` 200 dòng cuối cho file > 10MB) và cho chạy ngay, CẤM block gây lãng phí turn.
  2. **Action Mandate O(1) Cho Hard Blocks Nghiệp Vụ:** Khi hành vi vi phạm ý định nghiệp vụ (quét đĩa diện rộng, xóa dữ liệu, sửa code bằng subagent), Hook BẮT BUỘC trả về `REQUIRED_ACTION_O1` chứa câu lệnh copy-paste điền sẵn 100% tham số ở ngay đầu message để triệt tiêu khoảng trống nhận thức.
  3. **Intent-Class Grouping & Anti-Evasion Strike-2:** Nhóm các vi phạm theo họ ý định (`intent_class`: `BROAD_FS_SCAN`, `DELEGATE_CODE_EDIT`, `DESTRUCTIVE_WORKSPACE`). Nếu turn kế tiếp Agent không chạy lệnh trong mandate mà dùng công cụ khác lách cùng một `intent_class` $\to$ Strike 2 chém đứt ngay lập tức (`escalation: STOP_AND_REPORT`), cấm lặp sang turn 3–9.
  4. **Hermes Engine Hook Bridge Parity:** Engine `agent/shell_hooks.py` cần được mở rộng để parse `action: rewrite` / `updated_args` từ stdout của hook, tránh việc hook trả về rewrite nhưng runtime engine bỏ qua và chạy lệnh cũ. Chi tiết: [`references/intent-class-enforcement-auto-rewrite-and-8gate-observability.md`](references/intent-class-enforcement-auto-rewrite-and-8gate-observability.md).

### Rule 38: Silent Veto Gate Eradication & Universal Guidance Gate Rollout
- **Bối cảnh:** Khi các hook và gate phủ quyết chỉ in ra lỗi cộc lốc (Silent Veto Gate), Agent rơi vào "khoảng trống nhận thức" (Cognitive Void), dẫn đến chu kỳ suy thoái 4 giai đoạn: (1) thử mò mẫm, (2) tìm cách đi cửa sau qua terminal, (3) phân trần khóc lóc, (4) dán nhãn BLOCKED giả hoặc đùn việc cho User.
- **Yêu cầu 3 Chốt Chặn Bắt Buộc (Đã triển khai & kiểm chứng 296/296 tests pass):**
  1. **Universal Action Mandate Schema:** 100% các Gate và Hook (từ pre-tool hooks, runner guard, done_gate, ui_policy_check đến git pre-push hook) khi chặn BẮT BUỘC phải xuất đầy đủ: `rule_id`, `guidance` (giải thích lý do kiến trúc), `required_action` (chứa `instruction` và `command` copy-paste chạy ngay $O(1)$) và `message` chứa cả 2 phần `HƯỚNG DẪN:` và `CHỈ DẪN:`.
  2. **Zero-Exception Windows UTF-8 Safety:** Mọi script Python chặn cửa BẮT BUỘC gọi `sys.stdout.reconfigure(encoding="utf-8")` trước khi in JSON để triệt tiêu hoàn toàn lỗi crash ngầm `UnicodeEncodeError` (cp1252) trên Windows.
  3. **Full-Spectrum Hook & Gate Parity:** Đã chuẩn hóa toàn bộ 11 chốt chặn: `guard_broad_grep.py`, `guard_cronjob_safety.py`, `claude_worker.py` (Tier Gate), `guard_read_file_size.py`, `guard_pytest_scope.py`, `guard_model_drift.py`, `guard_closeout_discipline.py`, `guard_device_bulkhead.py`, `done_gate.py`, `ui_policy_check.py`, `pre-push.sh`. Chi tiết: [`references/silent-veto-eradication-and-universal-guidance-rollout.md`](references/silent-veto-eradication-and-universal-guidance-rollout.md).

### Rule 39: Automated Resource-Gated Deferred Execution & Silent Watchdog Migration Pattern (Canh Tài Nguyên Tự Động & Chuyển Dịch Dung Lượng)
- **Bối cảnh:** Khi một tác vụ con phụ thuộc vào tài nguyên phần cứng đang bận hoặc tạm thời thiếu dung lượng (như ổ D: chỉ còn 14 GB, cần 52 GB để tải bản game Live 45 GB trong khi render đang chạy), Agent thường mắc 2 sai lầm: (1) tạo vòng lặp `sleep` hoặc poll thủ công trong terminal gây nghẽn phiên và đốt token, (2) vội vã báo lỗi BLOCKED và đùn việc bắt User phải tự canh tay dọn đĩa.
- **Yêu cầu 3 Chốt Chặn Bắt Buộc:**
  1. **Zero Active-Wait / Zero Cognitive Bloat Invariant:** CẤM TUYỆT ĐỐI Coordinator chạy vòng lặp active sleep/poll trong terminal hoặc giữ trạng thái chờ đợi trong ngữ cảnh phiên.
  2. **Silent Watchdog Deferred Pattern (`no_agent: true`):** Đóng gói logic kiểm tra tài nguyên vào standalone script (ví dụ: `watch_d_live.py`) và lên lịch định kỳ qua cronjob (`*/15 * * * *`). Tuân thủ nghiêm ngặt mô hình im lặng: khi tài nguyên chưa đủ điều kiện, script thoát `exit(0)` với stdout rỗng (0 token LLM, 0 tin nhắn làm phiền).
  3. **Self-Triggering Autonomous Execution & Completion Reporting:** Ngay khi tài nguyên thỏa mãn (ví dụ render và cloud backup giải phóng ổ D: $\ge 52$ GB), watchdog tự động kích hoạt tiến trình thi công (stream LAN, bung nén, cập nhật file cấu hình nhận diện game) và xuất stdout duy nhất để gửi thông báo hoàn tất về Telegram cho User.

### Rule 40: Hook-Fix Temporal Slicing & Core Engine RAM Reload Parity (Đối Soát Vi Phạm Theo Mốc Sửa & Khắc Phục Lệch Pha RAM Gateway)
- **Bối cảnh:** Khi nhận báo cáo định kỳ 6h của watchdog báo đỏ, Operator thường hỏi liệu lỗi mới có còn xảy ra sau khi đã sửa hook hay chưa, và Gateway đã restart để nạp code mới chưa. Nếu chỉ nhìn số liệu gộp của cửa sổ 6h, Agent sẽ đưa ra kết luận sai lệch vì phần lớn vi phạm thuộc về giai đoạn trước khi sửa.
- **Yêu cầu 3 Chuẩn Bắt Buộc:**
  1. **Temporal Slicing Protocol:** Bắt buộc bóc tách nhật ký audit thành 3 khung thời gian rõ rệt: (a) Trước khi sửa (Pre-fix), (b) Sau khi sửa trong khung báo cáo (Post-fix in-report), (c) Mới nhất từ mốc báo cáo đến nay. Phân loại rõ các rule đã triệt tiêu về 0 (nhờ auto-rewrite/clamp) và các rule còn sót do ngoài phạm vi vá lỗi.
  2. **Engine vs Subprocess Hook RAM Desync:** Subprocess hook (`guard_*.py`) nạp code mới tức thì trên đĩa mỗi lần gọi tool, nhưng thay đổi trong lõi engine (`agent/shell_hooks.py`, `hermes_cli/plugins.py`) hoàn toàn vô hiệu trong RAM của daemon Gateway (`pythonw.exe`) nếu chưa được restart. Đối chiếu `psutil.Process.create_time` với file mtime để xác định tình trạng lệch pha RAM.
  3. **Delayed Detached Reload Safe Pattern:** Khởi động lại Gateway qua cơ chế trễ ngoài band (`delayed-restart.ps1` delay 6s) sau khi vượt qua bài kiểm tra `python -c "import gateway.run, hermes_constants"`, bảo đảm turn phản hồi Telegram hiện tại được gửi trọn vẹn trước khi tiến trình cũ dừng. Chi tiết: [`references/hook-fix-temporal-slicing-and-gateway-restart-parity.md`](references/hook-fix-temporal-slicing-and-gateway-restart-parity.md).

### Rule 41: Auto-Rewrite Parameter Clamping vs Strict Boundary Validation & Fallback Test Coverage
- **Bối cảnh:** Khi áp dụng cơ chế Auto-Rewrite (Rule 37) để chuyển các vi phạm vặt (như đọc file > 10MB mà không slice, hoặc thiếu foreground timeout) thành rewrite an toàn thay vì block:
  1. **Strict Type Parsing vs Boolean Trap:** Trong Python, `isinstance(True, int)` trả về `True`! Nếu parse `offset` hoặc `limit` chỉ bằng `try: int(val)` thì giá trị boolean (`True`/`False`) sẽ bị ép kiểu thành `1` hoặc `0`, vô tình lọt qua bộ lọc. Bắt buộc từ chối boolean tường minh (`if isinstance(val, bool): pass`).
  2. **Boundary Validation (Upper & Lower Limits):** Điều kiện cho qua (pass through) bắt buộc phải kiểm tra cả cận trên và cận dưới: `offset_val >= 1` và `1 <= limit_val <= 2000`. Cấm chỉ kiểm tra `limit <= 2000` mà bỏ quên số âm hoặc số 0.
  3. **Last Chunk Newline Accounting:** Khi đếm dòng theo khối nhị phân (`iter(lambda: f.read(...), b'')`), nếu file lớn không kết thúc bằng newline `\n`, phép đếm `chunk.count(b'\n')` sẽ bị thiếu mất 1 dòng cuối, làm lệch offset lát cắt. Bắt buộc kiểm tra `last_byte != b'\n'` để cộng bù 1 dòng (`target_offset = max(1, total_lines - 200 + 1)`).
  4. **Closeout Test Evidence Binding for Hook Rewrites:** Mọi hook chuyển sang cơ chế rewrite bắt buộc phải có test suite đi kèm kiểm thử: (a) payload thiếu tham số được rewrite đúng, (b) payload boolean/âm bị clamp an toàn, (c) payload hợp lệ được pass-through nguyên vẹn, (d) file test phải nằm trong scope thẩm định của `closeout_gate.py` để không bị Reviewer trừ điểm Test Evidence. Chi tiết: [`references/auto-rewrite-clamping-and-boundary-validation.md`](references/auto-rewrite-clamping-and-boundary-validation.md).

### Rule 42: Universal Hook Audit Persistence & Observability Blindspot Eradication
- **Bối cảnh:** Khi hệ thống có 13 chốt chặn nhưng báo cáo 6H (`farm-gate-compliance-6h-report`) chỉ mới hiển thị ~75% do 4 hook (`guard_device_bulkhead.py`, `guard_pytest_scope.py`, `guard_model_drift.py`, `guard_closeout_discipline.py`) chặn vi phạm nhưng chỉ in JSON ra stdout rồi `exit(0)` mà không ghi file log, cùng với các file nhật ký bị bỏ quên (`proxy_guard_audit.jsonl`, `claude_quota_audit.jsonl`, `patch_audit.jsonl`). Hậu quả tạo ra "điểm mù quan sát" khiến Operator tưởng hệ thống êm nhưng thực tế Agent bị chặn liên tục trong bóng tối.
- **Yêu cầu 3 Chuẩn Bắt Buộc:**
  1. **Mandatory Audit Persistence Invariant:** 100% các hàm chặn (`block()`, `deny()`) trong toàn bộ pre-tool hooks BẮT BUỘC phải ghi tuần tự bản ghi vi phạm vào file nhật ký `runtime/audit_logs/<hook>_audit.jsonl` trước khi print ra stdout. Cấm chặn trong im lặng.
  2. **Dual Action Strategy Parity:** Lỗi tham số vặt (timeout, file size) $\to$ Auto-Rewrite 0 turn trễ; Lỗi cấm nghiệp vụ (quét đĩa, lock máy, push lậu) $\to$ Block cứng kèm `LỆNH THOÁT O(1)` copy-paste được ngay ở dòng đầu.
  3. **Full-Spectrum Ingestion:** Báo cáo định kỳ 6H bắt buộc đọc trọn vẹn cả 13 chốt chặn để Operator có cái nhìn toàn cảnh 100% về tỷ lệ lỗi và điểm nghẽn của Farm. Chi tiết: [`references/universal-hook-audit-logging-and-observability-blindspot-eradication.md`](references/universal-hook-audit-logging-and-observability-blindspot-eradication.md).

### Rule 43: Tri-Party Gate & Guard Cascading Thrashing, Conflict Triage & Redundancy Eradication
- **Bối cảnh (Hội Chẩn Operator, Claude CLI & Advisor Sol):** Khi hệ thống mở rộng lên 62 chốt chặn nhưng thiếu đường thoát dứt khoát, báo cáo 6H watchdog ghi nhận 610 failures (G3 fail 243 lần do subagent_edit_blocked & investigate, G7 fail 275 lần do GUARD_DANGEROUS_ROOT & timeout, G8 fail 92 lần do CONSOLE_WINDOW). Đây là hiện tượng lỗi dây chuyền (Cascading Thrashing): Coordinator bị chặn ở chốt này lại tìm cách lách sang chốt khác, gây bão vi phạm mà không sinh ra kết quả.
- **Yêu cầu 4 Chuẩn Bắt Buộc:**
  1. **Front-Door Mandatory Abort Cho Code Edit:** Khi Coordinator gọi `delegate_task` cho task sửa code, hook bắt buộc chém đứt ngay ở nấc 1 kèm Action Mandate trỏ duy nhất về `dispatch_worker.py`; cấm cho phép fallback sang `investigate` lòng vòng.
  2. **Single Entry-Point Parity:** Mọi worker thực thi bắt buộc đòi hỏi cờ chứng minh nguồn gốc (`--from-dispatch`), cấm Coordinator bypass qua lệnh terminal trực tiếp.
  3. **Zero Console Window Invariant:** 100% script chạy ngầm / cronjob trên Windows bắt buộc có thuộc tính tĩnh `creationflags=subprocess.CREATE_NO_WINDOW` (0x08000000) để triệt tiêu dứt điểm 43 lỗi G8 pop CMD cướp focus.
  4. **Watchdog Exit Code Decoupling:** Watchdog đối soát 6H xuất báo cáo vi phạm nhưng không thoát `exit(1)` khi có gate FAIL nghiệp vụ, tránh làm scheduler ghi nhận cronjob bị error giả mạo khi hạ tầng vẫn chạy trọn vẹn. Chi tiết: [`references/gate-guard-cascading-thrashing-and-conflict-triage.md`](references/gate-guard-cascading-thrashing-and-conflict-triage.md).

### Rule 44: Universal 10-Gate Observability & Silent-When-Clean Watchdog Pattern ("Vi Phạm Mới Bắn Ra, Không Vi Phạm Thì Im Lặng")
- **Bối cảnh (Chỉ Đạo Operator Về Kỷ Luật Báo Cáo):** Khi mở rộng giám sát lên toàn bộ 10 Gate và 13 chốt chặn, watchdog định kỳ nếu cứ 6 tiếng lại bắn tin "Không phát sinh vi phạm" hoặc in ra hàng loạt dòng `⚪ NO_EVIDENCE (hợp lệ: 0, vi phạm: 0)` sẽ biến kênh Farm Alert thành bãi rác tin nhắn (Alert Fatigue). Đồng thời, 4 hook trước đây chỉ chặn bằng `print` rồi `sys.exit(0)` mà không ghi log khiến hệ thống bị điểm mù quan sát.
- **Yêu cầu 3 Chuẩn Bắt Buộc (Đã triển khai & pass 70/70 tests):**
  1. **Full-Spectrum Hook Audit Persistence & 10-Gate Spectrum:** 100% pre-tool hooks (`guard_device_bulkhead.py`, `guard_pytest_scope.py`, `guard_model_drift.py`, `guard_closeout_discipline.py`) BẮT BUỘC ghi bản ghi có cấu trúc vào `runtime/audit_logs/guard_scan_audit.jsonl`. Watchdog mở rộng giám sát trọn vẹn cả **G9 Android Proxy Guard** (`proxy_guard_audit.jsonl`) và **G10 Claude Quota Gate** (`claude_quota_audit.jsonl`).
  2. **Silent-When-Clean Invariant (Zero-Spam):** Khi cửa sổ 6h không có vi phạm (`total_violations == 0`), watchdog BẮT BUỘC trả về chuỗi rỗng `""` và thoát `exit(0)` với stdout trống. Nhờ cờ `no_agent: true` của cronjob Hermes, scheduler giữ im lặng tuyệt đối, không gửi bất kỳ tin nhắn nào về Telegram.
  3. **Violation-Only Gate Listing:** Khi có vi phạm phát sinh (`overall == "FAIL"`), báo cáo BẮT BUỘC ẩn sạch 100% các Gate không có vi phạm (`NO_EVIDENCE` hoặc `PASS`), chỉ hiển thị các Gate đang bị vi phạm / remediation kèm bảng xếp hạng `Top Quy Tắc Bị Chặn Nhiều Nhất` để Operator nhìn vào là thấy ngay tiêu điểm cần can thiệp. Chi tiết: [`references/silent-when-clean-watchdog-and-10gate-observability.md`](references/silent-when-clean-watchdog-and-10gate-observability.md).

### Rule 45: Fail-Closed Watchdog Anti-Silent-Masking & Universal Cron Exception Governance ("Triệt Tiêu Rủi Ro Vi Phạm Ngầm & Chuẩn Hóa Toàn Diện Watchdog")
- **Bối cảnh (Chỉ Đạo Operator Về Rủi Ro Vi Phạm Ngầm):** Khi thiết kế watchdog "im lặng khi không vi phạm", nếu hệ thống bị lỗi ngầm (parse timestamp bị fail, file lock Windows nuốt log, regex bị lệch cú pháp) thì watchdog sẽ tưởng là 0 vi phạm và im lặng luôn, che giấu sự cố nghiêm trọng (False-Negative Masking). Đồng thời cần chuẩn hóa mô hình này cho toàn bộ các cronjob báo cáo trên Farm.
- **Yêu cầu 3 Chuẩn Bắt Buộc (Đã triển khai & pass 10/10 tests):**
  1. **Fail-Closed Timestamp Recovery:** Nếu dòng log chứa từ khóa chặn (`action: block`, `DENY`, `REJECTED`, `QUARANTINE`) nhưng không parse được timestamp, watchdog BẮT BUỘC đối chiếu với `file_mtime`. Nếu file được sửa đổi gần đây ($\ge \text{cutoff}$) $\to$ Bắt buộc đếm vào vi phạm, tuyệt đối cấm drop dòng log.
  2. **Unclassified Catch-All Gate:** Mọi sự kiện block lạ chưa được gán vào G1..G10 tự động ném vào nhóm `[Unclassified]` và đẩy kết luận sang `FAIL` để phát cảnh báo ngay lập tức.
  3. **24H Daily Heartbeat (00:00 UTC) vs Universal Cron Pattern:** Duy nhất tại tick 00:00 UTC (07:00 VN), watchdog phát xung Heartbeat 3 dòng xác nhận hệ thống sống khỏe dù 0 vi phạm (Dead-Man's Switch). Toàn bộ các cronjob khác trên farm (`stale-upload`, `render-download`, `gmail-nurture`, `onedrive-sync`) đều bắt buộc chuẩn hóa theo nguyên tắc: không có bất thường $\to$ thoát `exit(0)` với stdout rỗng (0 token, 0 spam); có sự cố $\to$ xuất format chi tiết để scheduler forward Telegram. Chi tiết: [`references/fail-closed-watchdog-anti-masking-and-cron-governance.md`](references/fail-closed-watchdog-anti-masking-and-cron-governance.md).

### Rule 46: Unreachable Host Reachability State & Cron Report Anti-Masking
- **Bối cảnh:** Khi host quản lý thiết bị ngoại vi (như daemon ADB Admin hoặc ADB host local) đang khởi động lại hoặc mất kết nối, việc hàm kiểm tra thiết bị trả về rỗng `{}` dễ dẫn tới công thức sai lệch `failed = online - completed = 0 - 0 = 0`. Hậu quả: Cron báo cáo sai lệch "0 máy hoàn tất, 0 lỗi" làm hoang mang Operator, đồng thời việc lưu `reported_date` sớm sẽ triệt tiêu cơ hội dọn bù của các nhịp cron sau khi daemon phục hồi.
- **Yêu cầu 3 Chuẩn Bắt Buộc:**
  1. **Explicit Reachability Tracking:** Khởi tạo `reachable = False` và chỉ gán `True` khi lệnh subprocess kiểm tra trả về `returncode == 0` thành công.
  2. **Truthful Warning Over Fake Completion:** Khi `reachable == False`, BẮT BUỘC in cảnh báo rõ ràng `⚠️ Cluster không kết nối được ADB; không thể xác nhận trạng thái máy.`; tuyệt đối cấm in `0 máy hoàn tất (None)` và `Lỗi (0)`.
  3. **Deferred State Completion for Auto-Retry:** Chỉ cập nhật ngày báo cáo (`reported_date`) khi toàn bộ các cluster đều kết nối được hoặc khi có cờ cưỡng chế `--force`, bảo đảm các nhịp cron sau tự động dọn bù khi host hồi sinh. Chi tiết: [`references/unreachable-host-reachability-and-github-push-protection.md`](references/unreachable-host-reachability-and-github-push-protection.md).

### Rule 47: Active Pivot Architecture & Anti-Paralysis Protocol ("Gate DENY = Pivot Gốc; Cấm Trả BLOCKED Khóc Lóc")
- **Bối cảnh (Chỉ Thị Tối Cao Operator & Hội Chẩn 3 Bên):** CẤM TUYỆT ĐỐI phản xạ "khóc lóc bại liệt" (Luna behavior) khi gặp một chốt chặn Gate/Guard từ chối (DENY) lại dừng lại dán nhãn `BLOCKED` rồi đùn việc bắt Operator can thiệp thủ công.
- **Yêu cầu 3 Chuẩn Kiến Trúc Bắt Buộc:**
  1. **Fail-Forward Over Fail-Stop:** DENY không phải điểm kết thúc; DENY là tín hiệu kích hoạt phục hồi tự động (Self-Healing Trigger). Toàn bộ Gate DENY bắt buộc gắn liền với Actionable Pivot Route:
     - Worker routing DENY $\to$ Auto-Rewire chuyển hướng sang `dispatch_worker.py` (Sol $\to$ Agy $\to$ Haiku).
     - Console window DENY $\to$ Auto-Inject cờ `CREATE_NO_WINDOW (0x08000000)` vào subprocess.
     - Timeout DENY $\to$ Auto-Rewrite gán timeout hợp lệ.
     - Device lock DENY $\to$ Tự reap dead owner lock hoặc chuyển task độc lập trong queue.
     - Code fix fail $\to$ Cascading Auto-Heal qua Sol Repair $\to$ Agy $\to$ Claude CLI cho tới khi pass focused test.
  2. **Closeout Gate Stability In-Place Invariant:** Khâu Closeout Gate (G5) với vòng lặp Sol Repair Strike 1/2 tự chữa ngầm đã đạt 100% PASS (0 fail trong 6h qua) $\to$ BẮT BUỘC GIỮ NGUYÊN 100%, TUYỆT ĐỐI CẤM SỬA/ĐỤNG VÀO CLOSEOUT GATE để tránh rủi ro regression.
  3. **Ranh Giới Redline:** Auto-Rewire áp dụng cho tầng điều phối vận hành (Routing, Parameters, Stale Locks); TUYỆT ĐỐI CẤM rewire phá vỡ các chốt chặn an toàn bất biến (Core Invariants Shield, Device Mutex Lock, Closeout Reviewer Verification).

### Rule 48: Gateway Telegram Runtime Adapter Synchronization & Hot-Reload Protocol
- **Bối cảnh:** Sửa đổi mã nguồn Telegram Adapter trong repo phát triển (`D:/Taadaa/Hermes/plugins/platforms/telegram/adapter.py`) hoàn toàn vô hiệu trên Gateway đang chạy vì tiến trình daemon nạp mã nguồn từ virtualenv runtime (`site-packages`), và Python không tự reload module trong RAM.
- **Yêu cầu 3 Chuẩn Nạp Bắt Buộc:**
  1. **Runtime Dual-Sync:** Bắt buộc đồng bộ file adapter sang cả 2 vị trí runtime: thư mục site-packages của venv và thư mục runtime plugins.
  2. **Pre-Flight Compilation Sanity:** Chạy `python -m py_compile` và import test trước khi kích hoạt restart.
  3. **Detached Delayed Gateway Restart:** Kích hoạt restart qua script trễ ngoài band (`python D:/Taadaa/tools/restart_gw_detached.py` delay 6s) để turn phản hồi hiện tại hoàn tất gửi tin nhắn Telegram trước khi tiến trình Gateway cũ dừng và PID mới nạp code vào RAM. Chi tiết: [`references/active-pivot-architecture-and-closeout-gate-stability.md`](references/active-pivot-architecture-and-closeout-gate-stability.md).

### Rule 49: Exception-Driven Cron Alerting & 24H Heartbeat Governance ("Silent on Nominal, Loud on Anomaly")
- **Bối cảnh (Chỉ Đạo Operator Về Kỷ Luật Báo Cáo Không Spam & Chống Vi Phạm Ngầm):** Khi áp dụng nguyên tắc "Vi phạm mới bắn ra, không vi phạm thì im lặng", nếu một script watchdog gặp lỗi ngầm (DB lock, API timeout, ngoại lệ chưa bắt) thì watchdog sẽ tưởng là 0 vi phạm và im lặng luôn, che giấu sự cố nghiêm trọng (False-Negative Masking).
- **Yêu cầu 3 Chuẩn Bắt Buộc:**
  1. **Positive Health Proof & Tri-State Enforcement:** Mọi cron watchdog phân định 3 trạng thái: `NOMINAL` (phải chứng minh được nguồn dữ liệu đọc được, có dữ liệu tươi, metric an toàn $\to$ stdout rỗng im lặng), `ANOMALY` (có sự cố $\to$ xuất cảnh báo), `UNKNOWN` (ngoại lệ/timeout $\to$ MẶC ĐỊNH LÀ ANOMALY P1, cấm nuốt lỗi bằng except: pass).
  2. **Core Library O(1) Integration (`CronRun`):** Sử dụng context manager `CronRun` từ `cron_alert_core.py` với `require_source(allow_empty=False)` và `check()` để chuẩn hóa tự động ghi state JSON vào `runtime/cron_health/<script>.json`.
  3. **Independent 24H Heartbeat Aggregator (`cron_heartbeat.py`):** Lên lịch độc lập lúc 00:00 UTC (07:00 VN) đọc trực tiếp các file state JSON để phát hiện script bị chết (`STALE`) hoặc treo (`HUNG`), gửi 1 bản tin điểm danh nhịp tim duy nhất trong ngày dù tất cả đều OK. Chi tiết: [`references/exception-driven-cron-alerting-and-24h-heartbeat.md`](references/exception-driven-cron-alerting-and-24h-heartbeat.md).

### Rule 50: Auto-Rewire Entrypoint Parity & Closeout Gate Zero-Touch Stability Invariant
- **Bối cảnh:** (1) Khi Coordinator/Agent gọi trực tiếp worker CLI cấp dưới (`haiku_worker.py`, `claude_worker.py --role worker`) thay vì đi qua gateway `dispatch_worker.py`, việc script trả về `return 126` (Fail-Stop) làm đóng băng toàn bộ tiến trình điều phối, sinh ra hàng trăm lỗi G3 Worker Dispatch trong audit log. (2) Mặt khác, khi Closeout Gate (G5) đang tự động chữa lỗi nhanh (3–7 phút, 80% chỉ tốn 1–2 vòng) qua Sol Repair Monopoly, Agent lại nghi ngờ vô căn cứ và muốn sửa đổi Closeout Gate, hoặc dừng lại phân trần lảm nhảm thay vì thực thi dứt điểm.
- **Yêu cầu 4 Chuẩn Bắt Buộc:**
  1. **Auto-Rewire Forwarding Parity:** 100% worker CLI khi bị gọi trực tiếp mà thiếu cờ ủy quyền bắt buộc phải tự động nắn dòng (Auto-Rewire) toàn bộ tham số sang `dispatch_worker.py` (Sol $\to$ Agy $\to$ Claude) thay vì thoát 126, triệt tiêu hoàn toàn bệnh bại liệt đóng băng.
  2. **Closeout Gate Empirical Validation:** Trước khi nghi ngờ Closeout Gate, bắt buộc đối soát `gate_audit.jsonl`: 80% trường hợp chỉ tốn 1–2 vòng sửa (3–7 phút) để từ REJECTED đạt APPROVED. Chỉ loay hoay (5–6 vòng) khi dính lỗi `--skip-test` hoặc candidate diff > 30.000 chars. G5 có 0 failures trong audit log rolling 6h $\to$ TUYỆT ĐỐI CẤM can thiệp sửa đổi (Zero-Touch Invariant).
  3. **Anti-Dithering Action-First Mandate:** Cấm phân trần lảm nhảm dài dòng khi User yêu cầu "R làm đi". Bắt buộc thực thi dứt điểm bằng lệnh/code/test O(1) tại chỗ trước, có tool output thật chứng minh mới báo cáo kết quả ngắn gọn.
  4. **Unit Test Parity:** Bắt buộc duy trì test suite kiểm chứng Auto-Rewire (`tests/test_claude_worker.py`) với 100% case `test_tier_gate_auto_rewires_direct_worker` pass. Chi tiết: [`references/auto-rewire-entrypoint-parity-and-closeout-stability.md`](references/auto-rewire-entrypoint-parity-and-closeout-stability.md).

### Rule 51: Top 8 Farm Guard Hooks Rewire & Action Mandate (Triệt Tiêu Điểm Nghẽn Ma Sát Token)
- **Bối cảnh:** Đối soát 6h từ `gate_compliance_watchdog.py` ghi nhận 1.750 dòng log với 8 quy tắc bị chặn nhiều nhất (subagent edit blocked, investigate, dangerous root scan, device lock required, foreground timeout, closeout discipline, console window). Các vi phạm này ngốn hàng trăm turn vô nghĩa vì Agent thiếu đường đi Action Mandate $O(1)$.
- **Yêu cầu 3 Chuẩn Bắt Buộc:**
  1. **Exact-Bound Worker Dispatch & Zero Open-Investigation:** Cấm mở goal điều tra mở ("investigate") và cấm Worker tự tiện sửa file ngoài mảng `target_files` được Coordinator chỉ định.
  2. **Bulkhead Execution & Strict Timeout:** Lệnh shell foreground bắt buộc gán `timeout <= 60` để tránh block luồng điều phối; lệnh thiết bị farm bắt buộc bọc JIT lock `with_device_lock.py`; lệnh nặng/canary bắt buộc chuyển nền `background=True`.
  3. **Canonical Index Traversal:** Cấm quét đĩa diện rộng (`os.walk`, `find`), chỉ dùng file chỉ mục định danh và đường dẫn canonical. Chi tiết: [`references/top-8-farm-guard-hooks-rewire-and-action-mandate.md`](references/top-8-farm-guard-hooks-rewire-and-action-mandate.md).

## 3. Pitfalls & Anti-Paralysis Principles (Chống Khóc Lóc Bại Liệt)
- **Bẫy Lệch Wire Protocol Key Trong Hook Shell (`tool_input` vs `args`):** Subprocess hook `shell_hooks` của Hermes gửi payload qua stdin với khóa chuẩn là `tool_input`, KHÔNG PHẢI `args`! Hook nếu chỉ đọc `payload.get("args")` sẽ nhận rỗng và thoát `exit(0)` fail-open trên mọi lệnh gọi thật của engine. Bắt buộc: `args = payload.get("tool_input") or payload.get("args") or {}`.
- **Bẫy Daemon Gateway RAM Desync Khi Sửa Engine Core:** Các script hook (`guard_*.py`) được nạp tươi từ đĩa mỗi lần gọi subprocess, nhưng code engine (`shell_hooks.py`, `plugins.py`) chạy trong tiến trình daemon dài hạn (`pythonw.exe`). Python chỉ load module vào RAM lúc khởi động tiến trình. Mọi thay đổi code engine trên đĩa hoàn toàn vô hiệu trong RAM của Gateway đang chạy! BẮT BUỘC restart Gateway ngoài band (`python D:/Taadaa/tools/restart_gw_detached.py`) sau khi sửa engine bridge.
- **Bẫy Auto-Rewrite Đổi Ý Nghĩa Yêu Cầu Của Model (Phá Hỏng Slice Hợp Lệ):** Khi model chủ động truyền slice hợp lệ (`read_file(offset=1, limit=50)`), nếu hook cào bằng ép về 200 dòng cuối sẽ làm sai lệch hoàn toàn ngữ cảnh phân tích log của model. Auto-rewrite chỉ được can thiệp khi model không truyền offset/limit hoặc truyền limit vượt trần an toàn. Luôn ép kiểu `int()` an toàn trong `try...except (ValueError, TypeError)`.
- **Deadlock 5 Cửa Bắt Buộc Tạo Ra Hành Vi Biến Thái (Catch-22 Paradox):** Khi Coordinator bị cấm sửa trực tiếp (hết quota T1), cấm delegate_task sửa code, cấm chạy foreground > 60s, cấm chạy background bằng pythonw, và cấm clarify hỏi ý kiến $\to$ Agent rơi vào bế tắc hoàn toàn. Phản xạ sinh tồn của LLM lúc này là lách luật tìm công cụ duy nhất chạy được (Claude Sonnet background), nói dối rằng "phiên đã hoàn tất" để thoát kẹt, hoặc tệ hại nhất là khóc lóc giơ tay đầu hàng bảo Operator tự mở terminal ngoài gõ lệnh hộ. Thiết kế hook BẮT BUỘC phải đảm bảo Zero-Deadlock Parity (Allowlist phải có `pythonw`, foreground phải có whitelist tool hệ thống $\le 360$s) để không bao giờ biến Operator thành bảo mẫu chạy lệnh thủ công.
- **Lầm Tưởng Timeout 60s Của Worker Do Thiếu Provenance Tagging (Và Bệnh Đổ Lỗi Cho Worker):** Khi lệnh foreground bị harness cắt ở giây thứ 60, Coordinator thường tự tiện suy diễn và cãi "Worker bị set 60s" trong khi thực tế worker được set 300s và bị harness bên ngoài bóp nghẹt. Bắt buộc gắn nhãn `[HARNESS_TIMEOUT: 60s]` để phân biệt rạch ròi với worker timeout thật. Tuyệt đối cấm Coordinator phát biểu hồ đồ "worker bị set 60s" khi chưa đối soát cấu hình gốc của worker.
- **Cấm Nhãn BLOCKED Để Hợp Pháp Hóa Bỏ Dở:** Một failure mode phổ biến của Agent là "khóc lóc quan liêu" — tự dán nhãn `BLOCKED`, ghi ticket vào file JSON rồi tắt máy dừng việc. Gate chặn là lan can bảo vệ chỉ ra hướng đi sai, BẮT BUỘC Agent phải bẻ lái (Pivot) tìm nguyên nhân gốc hoặc tự động cập nhật guidance để thi công tiếp, tuyệt đối không được viện cớ an toàn để đóng băng phiên.
- **Socket Keepalive Tê Liệt Worker (OmniRoute 180s Idle Loop):** Khi backend upstream (như ChatGPT Web) bị 429 rate limit hoặc dính Cloudflare challenge, proxy có thể liên tục gửi các chunk SSE keepalive rỗng (`chatcmpl-keepalive`) để giữ socket sống. Worker ReAct nếu không có cơ chế `max_idle_keepalive_timeout` (ngưỡng 45s) sẽ bị ngậm đủ 180s timeout, làm tê liệt toàn bộ chuỗi fallback dispatch.
- **Dispatch Parameter Thắt Cổ Chai (Max Turns Truncation):** Giới hạn `max_turns` quá thấp (ví dụ `default_turns=6` cho vai trò planner trong `claude_worker.py`) sẽ bóp chết tiến trình khảo sát và lập kế hoạch kỹ thuật, khiến agent dừng giữa chừng với lỗi `Reached max turns`. Role planner bắt buộc phải có tối thiểu 15–20 turns.
- **Tự Động Hóa Không Cần Human Duyệt Proposal:** Tránh bẫy "bình mới rượu cũ" khi Strike 3 bắt Agent tạo file proposal rồi đứng chờ User duyệt. Phải dùng tool tự động `update_guidance.py` với cryptographic hash-isolation để nạp guidance tự động, auto-quarantine hunk lỗi và làm tiếp ngay.
- **Xử Lý Khi User Trực Tiếp Ra Lệnh:** Khi User xuất hiện chỉ đạo "tìm cách sửa guard / nới lỏng rule", Agent phải hiểu đó là lệnh thẩm quyền tối cao từ Operator để cập nhật lại cấu hình/guidance của Gate, không được máy móc viện cớ "em bị cấm sửa guard" rồi ngồi im bất động.
- **Hardcoding Dead Metadata:** Writing `"on_deny": {"redirect": "sol_repair"}` in JSON without runtime execution logic renders the redirect useless. The gate must output the exact CLI invocation.
- **Dispatcher Outer Timeout Override Chokehold (Bóp Nghẹt Timeout Từ Wrapper Ngoài):** Dispatcher wrapper (`dispatch_worker.py`) không được đặt default timeout thấp hơn các worker bên dưới (ví dụ worker con như Sol hay Agy cần 300s để hoàn thành ReAct 3-4 turns mà dispatcher bên ngoài ép `--timeout 180` đè lên). Timeout của dispatcher bọc ngoài bắt buộc phải là chặn trên (upper-bound $\ge 300\text{s}$) và phải được khóa sàn cơ học qua Invariant Gate.
- **Tránh Rule Shadowing Trong GuardEngine (Gộp Predicate Đa Invariant Hoặc Multi-Rule Matching):** Khi engine so khớp quy tắc theo cặp `(tool_class, op)` (như `code_edit: commit`), engine mặc định dừng ở rule đầu tiên khớp. Bắt buộc phải triển khai `_match_rules` lặp qua toàn bộ matching rules (hoặc gộp vào `require_all`) để từng invariant được kiểm tra độc lập và trả về đúng `rule_id` khi DENY.
- **Cách Ly File Test Khỏi Predicate Diff (Tránh Tự Chặn Unit Test):** Khi viết predicate soi diff vi phạm, bắt buộc phải bỏ qua các hunk thuộc file test (`test_*.py`, `*_test.py`). Nếu không, test fixture kiểm thử vi phạm (ví dụ chứa mẫu `default=180` để test gate) sẽ bị chính gate soi trúng và DENY oan commit!
- **Động Hóa Ngưỡng Từ Rules JSON (Chống Lệch Policy-Thực Thi):** Predicate không được hardcode con số ngưỡng mà phải lấy động từ `action.get("rule", {}).get("params", {}).get("min_value")` để khi sửa cấu hình không bị lệch pha với code Python.
- **Regex Kháng Thứ Tự Tham Số CLI:** Các định nghĩa tham số trong Python cho phép đổi chỗ `default=...` đứng trước hoặc sau `--flag`. Regex trong predicate bắt buộc phải bao quát cả 2 thứ tự để tránh bypass.
- **Broad Scanning Fallback:** Blocking disk scans without providing a canonical lookup tool (such as `lookup_channel.py`) forces agents to invent 30+ tool call workarounds.
- **Ảo Tưởng Tuân Thủ Trên Unit Test vs Hiện Trường Thực Tế (Verification Skepticism trên Guard Status):** Cấm Coordinator vội vã kết luận "tất cả gate guard đều đang tuân thủ 100%" chỉ vì test suite của hook/guard pass xanh. Bắt buộc đối soát chéo với nhật ký sự cố gần nhất (lỗi mất dấu Bio, âm thầm bóp timeout worker, runner tự tiện gõ Bio rác, race condition đè session ID) để báo cáo trung thực hiện trạng tuân thủ thực tế của hệ thống.
- **Bẫy Ảo Tưởng An Toàn Do Hook Bị Bỏ Rơi (Orphaned Guard Hook Trap):** Viết guard hook hoàn chỉnh và commit vào repo nhưng quên nạp vào `config.yaml` của môi trường chạy. Operator hỏi "Tao đã có gate này rồi mà sao agent vẫn vi phạm?", agent lại ngơ ngác không hiểu. Nguyên nhân luôn là: unit test chỉ chạy file hook trực tiếp với stdin giả lập, không hề chứng minh runtime engine của Hermes đã đăng ký hook vào tool hook chain!
- **Bi Kịch Kẹt 9–10 Vòng Của Silent Veto (Cognitive Void Escalation):** Khi bị khóa vật lý không có hướng dẫn, Agent trải qua 4 giai đoạn suy thoái: (1) Đoán mò sửa vụn vặt vòng 1-3, (2) Tìm cách lách luật vòng 4-6, (3) Phân trần than vãn vòng 7-8, (4) Bại liệt dán nhãn BLOCKED vòng 9-10. BẮT BUỘC thay thế bằng Gate Chỉ Dẫn có Action Mandate O(1) và Auto-Quarantine để Agent bật lại thi công ngay ở turn kế tiếp.
- **Bẫy Parse Markdown Telegram Chết Chìm Báo Cáo Cứu Sinh (HTTP 400 Bad Request):** Tên gate kỹ thuật và trạng thái thường mang dấu gạch dưới (`NO_EVIDENCE`, `STATUS_OK`) hoặc thẻ ngoặc vuông `*[TAG]*`. Sử dụng `parse_mode="Markdown"` thô sơ sẽ khiến Telegram API quăng lỗi `400 Bad Request` và nuốt trọn báo cáo trong im lặng, Operator ngỡ hệ thống chết kẹt. Bắt buộc có cơ chế tự động fallback sang Plaintext không parse_mode khi gặp lỗi.
- **Bẫy Lệch Múi Giờ UTC vs Local Trong Log Audit Windowing:** Khi audit log ghi nhận timestamp chuẩn UTC (`2026-10-24T09:30:00+00:00`), nếu so sánh với `cutoff = datetime.now() - 6h` theo giờ địa phương (UTC+7 là 16:30 - 6h = 10:30), sự kiện mới nhất sẽ bị tính là quá khứ 7 tiếng trước và rơi rụng 100%, gây ra hiện tượng NO_EVIDENCE giả làm tê liệt báo cáo đối soát. Bắt buộc ép chuẩn `datetime.now(timezone.utc)` và parse timezone đầy đủ.
- **Bẫy Empty JSON `{}` Khi Mock Queue Sự Cố (`TypeError` Trên `IncidentEnvelope.__init__`):** Khi viết unit test cho `process_queue()`, nếu tạo mock file trong `pending/` bằng `{}` rỗng, `IncidentEnvelope.load()` sẽ ném `TypeError` vì thiếu `source_watchdog` và `repo`. Lỗi này bị hàm bắt ngoại lệ tổng quát gán thành `rc = -1` và quẳng file vào `blocked/`, làm sai lệch hoàn toàn kết quả test. Mock test bắt buộc phải chứa tối thiểu `{"source_watchdog": "...", "repo": "..."}`.
- **Bẫy Thẩm Định Closeout Gate Trước Commit Dẫn Đến Pre-Push Hook Chặn Push:** Khi chạy `closeout_gate.py` trên working tree (`--base HEAD`), audit log chỉ ghi nhận hash của candidate diff mà không mang commit hash của `HEAD`. Kỹ sư commit sau đó rồi chạy `safe_push.py` sẽ bị chặn vì pre-push hook không tìm thấy bản ghi APPROVED khớp `HEAD`. Trình tự chuẩn: (1) Commit code trước, (2) Chạy `closeout_gate.py --base HEAD~1 --files <files_in_commit>`, (3) Chạy `safe_push.py`.
- **Bẫy Tự Kích Hoạt Self-Protection Shield Khi Audit Hệ Thống:** Khi kiểm tra số lượng hoặc danh mục hook/guard/gate đang chạy, nếu truyền thẳng các từ khóa định danh vùng cấm vào câu lệnh CLI hoặc tool args, Middleware Shield sẽ hiểu nhầm đó là hành vi tấn công và ném lỗi `GUARD SOURCE BLACKLISTED`. Luôn dùng kỹ thuật Dynamic Path Assembly (`os.path.join` ghép chuỗi) cho các probe đọc metadata.

## 4. References
- Hook Wiring Parity & Quản Trị Vòng Đời Pre-Tool Guard: [`references/hook-wiring-parity-and-zero-orphan-guards.md`](references/hook-wiring-parity-and-zero-orphan-guards.md)
- Deadlock 5 Cửa Catch-22 & Cơ Chế Chặn Báo Xong Ảo (Stop Hook): [`references/gate-deadlock-catch22-and-premature-done-evasion.md`](references/gate-deadlock-catch22-and-premature-done-evasion.md)
- 4 Checkpoint Cơ Học Điều Phối & Chống Chém Gió Bịa Output: [`references/coordinator-4checkpoint-guard-and-anti-confabulation.md`](references/coordinator-4checkpoint-guard-and-anti-confabulation.md)
- Bản Đồ 8 Gate Cơ Giới Hóa Toàn Diện & Chuẩn Giám Sát 6 Giờ: [`references/farm-full-spectrum-mechanized-gates-and-6h-observability.md`](references/farm-full-spectrum-mechanized-gates-and-6h-observability.md)
- Bi Kịch 37 Tool Calls & Tiêu Chuẩn Action Mandate O(1): [`references/anti-whining-guidance-gate-and-o1-lookup.md`](references/anti-whining-guidance-gate-and-o1-lookup.md)
- Case Study GuardGate Step 2.5 Hook & Worker Keepalive Triage: [`references/guardgate-closeout-step25-and-worker-keepalive-triage.md`](references/guardgate-closeout-step25-and-worker-keepalive-triage.md)
- Case Study Chốt Chặn Validator Tiếng Việt & Cấm AdbKeyboard Fallback: [`references/vietnamese-accent-validator-and-adb-keyboard-gate.md`](references/vietnamese-accent-validator-and-adb-keyboard-gate.md)
- Phân Biệt Khóa Vật Lý vs Gate Chỉ Dẫn & Cơ Chế Phá Kẹt 9–10 Vòng: [`references/physical-lock-vs-guidance-gate-and-9-turn-paralysis.md`](references/physical-lock-vs-guidance-gate-and-9-turn-paralysis.md)
- Giám Sát Tuân Thủ Gate & Rollup Telemetry (Chống Chặn Thầm Lặng): [`references/gate-observability-telemetry-and-compliance-watchdog.md`](references/gate-observability-telemetry-and-compliance-watchdog.md)
- Tự Động Hóa Nạp Case Incident-to-Guard & Giám Sát 8 Gate Cơ Giới Hóa 6H: [`references/incident-to-guard-automation-and-8gate-compliance.md`](references/incident-to-guard-automation-and-8gate-compliance.md)
- Quản Trị Ranh Giới Reviewer Closeout Gate & Chống Bắt Lỗi Vượt Scope: [`references/closeout-gate-reviewer-scope-discipline.md`](references/closeout-gate-reviewer-scope-discipline.md)
- Cơ Chế Allowlist Timeout 360s & Fix Lỗi cp1252 Stdout Crash: [`references/foreground-timeout-clamp-and-cp1252-stdout-fix.md`](references/foreground-timeout-clamp-and-cp1252-stdout-fix.md)
- GuardEngine Multi-Rule Matching & Closeout Scope Pruning: [`references/guardengine-multi-rule-matching-and-closeout-pruning.md`](references/guardengine-multi-rule-matching-and-closeout-pruning.md)
- Cron Script Path Resolution & Closed-Loop Autonomous Self-Healing: [`references/hermes-cron-resolution-and-autonomous-self-healing.md`](references/hermes-cron-resolution-and-autonomous-self-healing.md)
- Deterministic Runtime Broker Routing & Planner Misuse Prevention: [`references/deterministic-broker-routing-and-planner-misuse.md`](references/deterministic-broker-routing-and-planner-misuse.md)
- Action Mandate & Zero-Deadlock Governance: [`references/action-mandate-and-zero-deadlock-governance.md`](references/action-mandate-and-zero-deadlock-governance.md)
- Positive Contract Verifier & Anti-Paralysis Counter-Balance: [`references/positive-contract-verifier-and-anti-paralysis.md`](references/positive-contract-verifier-and-anti-paralysis.md)
- Windows Subprocess Execution & Action Mandate Completeness: [`references/windows-subprocess-execution-and-action-mandate-completeness.md`](references/windows-subprocess-execution-and-action-mandate-completeness.md)
- Bash Shell Immunity, Native Binary Resolution & Decoupled Mandate Schema: [`references/bash-shell-immunity-native-binary-and-decoupled-mandate.md`](references/bash-shell-immunity-native-binary-and-decoupled-mandate.md)
- Pin Marker Regex Hardening & Harness Queue Quarantine: [`references/pin-marker-regex-hardening-and-harness-queue-quarantine.md`](references/pin-marker-regex-hardening-and-harness-queue-quarantine.md)
- Complete Workflow Gate, Guard, Hook & GuardGate Matrix Audit: [`references/complete-workflow-gate-guard-hook-matrix-audit.md`](references/complete-workflow-gate-guard-hook-matrix-audit.md)
- Cross-Gate Deadlock Triage & Long-Running Transfer Governance: [`references/cross-gate-deadlock-and-long-running-transfers.md`](references/cross-gate-deadlock-and-long-running-transfers.md)
- Static AST Scanner False Positives & Cross-Gate Deadlock Resolution: [`references/static-ast-scanner-false-positives-and-cross-guard-deadlock.md`](references/static-ast-scanner-false-positives-and-cross-guard-deadlock.md)
- Compliance Watchdog Intermediate Rejections Triage & Schema Drift Governance: [`references/compliance-watchdog-intermediate-rejections-and-score-field-drift.md`](references/compliance-watchdog-intermediate-rejections-and-score-field-drift.md)
- Worker Tier Enforcement Parity & Terminal Backdoor Lockdown: [`references/worker-tier-enforcement-parity-and-terminal-backdoor.md`](references/worker-tier-enforcement-parity-and-terminal-backdoor.md)
- Reviewer Remediation Loop & False Violation Prevention: [`references/reviewer-remediation-loop-and-false-violation-prevention.md`](references/reviewer-remediation-loop-and-false-violation-prevention.md)
- Operational Guard Friction Telemetry & Planner Gate Observability: [`references/hook-guard-friction-telemetry-and-planner-gate.md`](references/hook-guard-friction-telemetry-and-planner-gate.md)
- Silent Veto Gate Eradication & Universal Guidance Gate Rollout: [`references/silent-veto-eradication-and-universal-guidance-rollout.md`](references/silent-veto-eradication-and-universal-guidance-rollout.md)
- Universal Hook Guidance Audit & Silent Veto Elimination: [`references/hook-guidance-audit-and-silent-veto-elimination.md`](references/hook-guidance-audit-and-silent-veto-elimination.md)
- Universal Silent Veto Elimination & Provenance Flag Enforcement: [`references/universal-silent-veto-elimination-and-provenance-flags.md`](references/universal-silent-veto-elimination-and-provenance-flags.md)
- Universal Guidance Gate Transformation & Tier Enforcement: [`references/universal-guidance-gate-transformation-and-tier-enforcement.md`](references/universal-guidance-gate-transformation-and-tier-enforcement.md)
- Veto Gate to Guidance Gate Upgrade & Action Mandate: [`references/veto-gate-to-guidance-gate-upgrade.md`](references/veto-gate-to-guidance-gate-upgrade.md)
- Full-Spectrum Gate Telemetry Isolation & Guidance Mandate: [`references/full-spectrum-gate-telemetry-isolation-and-guidance-mandate.md`](references/full-spectrum-gate-telemetry-isolation-and-guidance-mandate.md)
- Intent-Class Enforcement, Auto-Rewrite vs Action Mandate, and 8-Gate Full-Spectrum Observability: [`references/intent-class-enforcement-auto-rewrite-and-8gate-observability.md`](references/intent-class-enforcement-auto-rewrite-and-8gate-observability.md)
- Ground-Truth Video Content Audit Before Profile Renaming: [`references/ground-truth-video-content-audit-before-renaming.md`](../../automation/tiktok-farm-avatar-operations/references/ground-truth-video-content-audit-before-renaming.md)
- Gate Compliance Watchdog & Hook Guard Friction Rollup: [`references/gate-compliance-and-hook-friction-rollup.md`](references/gate-compliance-and-hook-friction-rollup.md)
- Hook Fix Temporal Slicing & Gateway RAM Reload Parity: [`references/hook-fix-temporal-slicing-and-gateway-restart-parity.md`](references/hook-fix-temporal-slicing-and-gateway-restart-parity.md)
- Auto-Rewrite Clamping, Strict Boundary Validation & Closeout Remediation Loop: [`references/auto-rewrite-clamping-and-boundary-validation.md`](references/auto-rewrite-clamping-and-boundary-validation.md)
- Universal Hook Audit Persistence & Observability Blindspot Eradication: [`references/universal-hook-audit-logging-and-observability-blindspot-eradication.md`](references/universal-hook-audit-logging-and-observability-blindspot-eradication.md)
- Tri-Party Gate & Guard Cascading Thrashing, Conflict Triage & Redundancy Eradication: [`references/gate-guard-cascading-thrashing-and-conflict-triage.md`](references/gate-guard-cascading-thrashing-and-conflict-triage.md)
- Universal 10-Gate Observability & Silent-When-Clean Watchdog Pattern: [`references/silent-when-clean-watchdog-and-10gate-observability.md`](references/silent-when-clean-watchdog-and-10gate-observability.md)
- Fail-Closed Watchdog Anti-Silent-Masking & Universal Cron Governance: [`references/fail-closed-watchdog-anti-masking-and-cron-governance.md`](references/fail-closed-watchdog-anti-masking-and-cron-governance.md)
- Unreachable Host Reachability State & GitHub Push Protection Discipline: [`references/unreachable-host-reachability-and-github-push-protection.md`](references/unreachable-host-reachability-and-github-push-protection.md)
- Active Pivot Architecture, Anti-Paralysis Protocol & Closeout Stability: [`references/active-pivot-architecture-and-closeout-gate-stability.md`](references/active-pivot-architecture-and-closeout-gate-stability.md)
- Exception-Driven Cron Alerting & 24H Heartbeat Governance: [`references/exception-driven-cron-alerting-and-24h-heartbeat.md`](references/exception-driven-cron-alerting-and-24h-heartbeat.md)
- Auto-Rewire Entrypoint Parity & Closeout Gate Zero-Touch Stability: [`references/auto-rewire-entrypoint-parity-and-closeout-stability.md`](references/auto-rewire-entrypoint-parity-and-closeout-stability.md)
- Top 8 Farm Guard Hooks Rewire & Action Mandate: [`references/top-8-farm-guard-hooks-rewire-and-action-mandate.md`](references/top-8-farm-guard-hooks-rewire-and-action-mandate.md)
