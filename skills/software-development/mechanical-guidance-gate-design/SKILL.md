---
name: mechanical-guidance-gate-design
description: "Use when designing mechanical gates to prevent agent loops."
---

# Mechanical Guidance Gate Design (Anti-Whining & Action Mandate)

## 1. When to Use
Use when creating, modifying, or reviewing mechanical enforcement gates (pre-tool hooks, git hooks, closeout gates, or runtime fences). Enforces that every gate provides deterministic, actionable unblocking paths rather than passive denials.

## 2. Core Standards (Tri-Party Consensus)

### Rule 1: No Silent Veto Gates (Cấm Veto Gate Câm)
- **Violation:** A gate checks a condition, fails, prints a static error (e.g. `[DENY] Policy violated`), and executes `sys.exit(1)` without providing executable next steps. This leaves an LLM agent in a cognitive void, triggering apologetic loops or bureaucratic helplessness.
- **Requirement:** Every non-zero exit from a gate MUST provide a machine-readable `REQUIRED_ACTION_O1` block with copy-pasteable commands and a domain-specific `guidance` string explaining the architectural invariant.

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

### Rule 19: Closeout Gate Commit Binding & Safe Push Parity (Chống Lỗi Bị Chặn Push Dù Gate Đã Pass)
- **Bối cảnh:** Khi repository đã có các commit cục bộ trước đó (nhánh ahead of origin), nếu Coordinator chạy `closeout_gate.py --repo <repo> --base HEAD --files ...`, gate chỉ trích xuất working tree diff và ghi nhận hash của candidate diff, KHÔNG gắn kết với commit hash của `HEAD`. Khi đó, lệnh `safe_push.py` kiểm tra `gate_audit.jsonl` đối chiếu với `HEAD` sẽ báo lỗi: `BLOCKED_GATE_NOT_APPROVED: Repository has no valid APPROVED closeout audit for HEAD (<hash>)`.
- **Yêu cầu Chuẩn Hóa Chốt Phiên:**
  1. **Commit-Targeted Closeout:** Khi chốt phiên cho các commit đã tạo, bắt buộc chạy `closeout_gate.py --repo <repo> --base HEAD~1 --json-output` (hoặc `--base origin/main`) để diff được trích xuất từ commit thật và `write_gate_audit` ghi nhận chính xác `"commit": "<HEAD_SHA>"` vào chuỗi audit.
  2. **Safe Push Execution:** Chỉ thực thi push qua wrapper chuẩn: `python D:/Taadaa/tools/safe_push.py <repo> origin <branch>`. Pre-push hook sẽ tự động đối soát audit entry `APPROVED` của commit `HEAD` và cho phép đẩy code an toàn lên remote.

### Rule 12: Generic Declarative Predicates & Safe Invariant Onboarding (`add_rule.py`)
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

## 3. Pitfalls & Anti-Paralysis Principles (Chống Khóc Lóc Bại Liệt)
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
