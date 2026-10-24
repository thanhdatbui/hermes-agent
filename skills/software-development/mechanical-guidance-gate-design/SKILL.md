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

## 3. Pitfalls & Anti-Paralysis Principles (Chống Khóc Lóc Bại Liệt)
- **Cấm Nhãn BLOCKED Để Hợp Pháp Hóa Bỏ Dở:** Một failure mode phổ biến của Agent là "khóc lóc quan liêu" — tự dán nhãn `BLOCKED`, ghi ticket vào file JSON rồi tắt máy dừng việc. Gate chặn là lan can bảo vệ chỉ ra hướng đi sai, BẮT BUỘC Agent phải bẻ lái (Pivot) tìm nguyên nhân gốc hoặc tự động cập nhật guidance để thi công tiếp, tuyệt đối không được viện cớ an toàn để đóng băng phiên.
- **Socket Keepalive Tê Liệt Worker (OmniRoute 180s Idle Loop):** Khi backend upstream (như ChatGPT Web) bị 429 rate limit hoặc dính Cloudflare challenge, proxy có thể liên tục gửi các chunk SSE keepalive rỗng (`chatcmpl-keepalive`) để giữ socket sống. Worker ReAct nếu không có cơ chế `max_idle_keepalive_timeout` (ngưỡng 45s) sẽ bị ngậm đủ 180s timeout, làm tê liệt toàn bộ chuỗi fallback dispatch.
- **Dispatch Parameter Thắt Cổ Chai (Max Turns Truncation):** Giới hạn `max_turns` quá thấp (ví dụ `default_turns=6` cho vai trò planner trong `claude_worker.py`) sẽ bóp chết tiến trình khảo sát và lập kế hoạch kỹ thuật, khiến agent dừng giữa chừng với lỗi `Reached max turns`. Role planner bắt buộc phải có tối thiểu 15–20 turns.
- **Tự Động Hóa Không Cần Human Duyệt Proposal:** Tránh bẫy "bình mới rượu cũ" khi Strike 3 bắt Agent tạo file proposal rồi đứng chờ User duyệt. Phải dùng tool tự động `update_guidance.py` với cryptographic hash-isolation để nạp guidance tự động, auto-quarantine hunk lỗi và làm tiếp ngay.
- **Xử Lý Khi User Trực Tiếp Ra Lệnh:** Khi User xuất hiện chỉ đạo "tìm cách sửa guard / nới lỏng rule", Agent phải hiểu đó là lệnh thẩm quyền tối cao từ Operator để cập nhật lại cấu hình/guidance của Gate, không được máy móc viện cớ "em bị cấm sửa guard" rồi ngồi im bất động.
- **Hardcoding Dead Metadata:** Writing `"on_deny": {"redirect": "sol_repair"}` in JSON without runtime execution logic renders the redirect useless. The gate must output the exact CLI invocation.
- **Dispatcher Outer Timeout Override Chokehold (Bóp Nghẹt Timeout Từ Wrapper Ngoài):** Dispatcher wrapper (`dispatch_worker.py`) không được đặt default timeout thấp hơn các worker bên dưới (ví dụ worker con như Sol hay Agy cần 300s để hoàn thành ReAct 3-4 turns mà dispatcher bên ngoài ép `--timeout 180` đè lên). Timeout của dispatcher bọc ngoài bắt buộc phải là chặn trên (upper-bound $\ge 300\text{s}$) và phải được khóa sàn cơ học qua Invariant Gate.
- **Tránh Rule Shadowing Trong GuardEngine (Gộp Predicate Đa Invariant):** Khi engine so khớp quy tắc theo cặp `(tool_class, op)` (như `code_edit: commit`), engine dừng ở rule đầu tiên khớp. Để kiểm tra đồng thời nhiều bất biến (như timeout USB Case 162 và timeout dispatch worker), BẮT BUỘC phải gộp tất cả các invariant predicates vào cùng danh sách `require_all` của master rule, không được khai báo rule rời rạc cùng `match` kẻo bị che khuất.
- **Broad Scanning Fallback:** Blocking disk scans without providing a canonical lookup tool (such as `lookup_channel.py`) forces agents to invent 30+ tool call workarounds.
- **Ảo Tưởng Tuân Thủ Trên Unit Test vs Hiện Trường Thực Tế (Verification Skepticism trên Guard Status):** Cấm Coordinator vội vã kết luận "tất cả gate guard đều đang tuân thủ 100%" chỉ vì test suite của hook/guard pass xanh. Bắt buộc đối soát chéo với nhật ký sự cố gần nhất (lỗi mất dấu Bio, âm thầm bóp timeout worker, runner tự tiện gõ Bio rác, race condition đè session ID) để báo cáo trung thực hiện trạng tuân thủ thực tế của hệ thống.
- **Bi Kịch Kẹt 9–10 Vòng Của Silent Veto (Cognitive Void Escalation):** Khi bị khóa vật lý không có hướng dẫn, Agent trải qua 4 giai đoạn suy thoái: (1) Đoán mò sửa vụn vặt vòng 1-3, (2) Tìm cách lách luật vòng 4-6, (3) Phân trần than vãn vòng 7-8, (4) Bại liệt dán nhãn BLOCKED vòng 9-10. BẮT BUỘC thay thế bằng Gate Chỉ Dẫn có Action Mandate O(1) và Auto-Quarantine để Agent bật lại thi công ngay ở turn kế tiếp.

## 4. References
- Bản Đồ 8 Gate Cơ Giới Hóa Toàn Diện & Chuẩn Giám Sát 6 Giờ: [`references/farm-full-spectrum-mechanized-gates-and-6h-observability.md`](references/farm-full-spectrum-mechanized-gates-and-6h-observability.md)
- Bi Kịch 37 Tool Calls & Tiêu Chuẩn Action Mandate O(1): [`references/anti-whining-guidance-gate-and-o1-lookup.md`](references/anti-whining-guidance-gate-and-o1-lookup.md)
- Case Study GuardGate Step 2.5 Hook & Worker Keepalive Triage: [`references/guardgate-closeout-step25-and-worker-keepalive-triage.md`](references/guardgate-closeout-step25-and-worker-keepalive-triage.md)
- Case Study Chốt Chặn Validator Tiếng Việt & Cấm AdbKeyboard Fallback: [`references/vietnamese-accent-validator-and-adb-keyboard-gate.md`](references/vietnamese-accent-validator-and-adb-keyboard-gate.md)
- Phân Biệt Khóa Vật Lý vs Gate Chỉ Dẫn & Cơ Chế Phá Kẹt 9–10 Vòng: [`references/physical-lock-vs-guidance-gate-and-9-turn-paralysis.md`](references/physical-lock-vs-guidance-gate-and-9-turn-paralysis.md)
- Giám Sát Tuân Thủ Gate & Rollup Telemetry (Chống Chặn Thầm Lặng): [`references/gate-observability-telemetry-and-compliance-watchdog.md`](references/gate-observability-telemetry-and-compliance-watchdog.md)
