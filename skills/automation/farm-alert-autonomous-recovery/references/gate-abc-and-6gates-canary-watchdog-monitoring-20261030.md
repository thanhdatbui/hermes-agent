# Gate A-B-C và 6 Gates Điều Phối (với Gate 6 là Canary) trong Watchdog Giám Sát

> Ngày ghi nhận: 30/10/2026
> Nguồn: Trực tiếp từ cấu hình `gate_compliance_watchdog.py`, `safe_push.py`, `done_gate.py`, `dispatch_audit.jsonl`, `closeout_gate.py`.

---

## 1. HỆ THỐNG GATE A - B - C (ĐIỀU TRA -> LẬP PLAN -> THI HÀNH WORKER)

Nhằm chống tình trạng Coordinator tự sửa bừa bãi hoặc dùng subagent lén sửa code, toàn bộ quy trình 3 chặng A-B-C được đưa vào Watchdog:

1. **Gate A — Investigation Gate (`G14: Investigation Gate (Gate A)`):**
   - **Nguồn log:** `runtime/audit_logs/dispatch_audit.jsonl`.
   - **Quy tắc:** `delegate_task` CHỈ được dùng để điều tra, đọc code, khảo sát hiện trường độc lập (budget <= 8 calls).
   - **Fail Pattern:** Bắt ngay `subagent_edit_blocked` (khi Coordinator giao việc sửa code cho subagent), hoặc `INVESTIGATION_BUDGET_EXCEEDED`, `INVESTIGATION_UNAUTHORIZED`.
   - **Pass Pattern:** `"route": "investigate_allowed" | "action": "allow" | "stage": "investigate_done"`.

2. **Gate B — Planning Gate (`G2: Planning Gate`):**
   - **Nguồn log:** `logs/dispatch_planner.jsonl`.
   - **Quy tắc:** Mọi tác vụ sửa code thông thường trước khi thi công bắt buộc phải có Plan hợp lệ do Sol phê duyệt.
   - **Fail Pattern:** `PLAN_MISSING | PLAN_FAILED | PLANNER_BYPASSED`.
   - **Pass Pattern:** `SOL_PLAN_ID | SOL_PLAN_SOURCE | "tier": "(?:sonnet|sol|coordinator)"`.

3. **Gate C — Worker Dispatch Gate (`G3: Worker Dispatch Gate`):**
   - **Nguồn log:** `logs/dispatch.jsonl`, `runtime/audit_logs/dispatch_audit.jsonl`.
   - **Quy tắc:** Thi công sửa code bắt buộc qua Worker độc lập (`dispatch_worker.py`).
   - **Fail Pattern:** `"category": "(?:TIMEOUT|QUOTA|NO_DIFF|NEEDS_INPUT|COMMAND_ERROR)" | "action": "block"`.
   - **Pass Pattern:** `"category": "OK" | "action": "allow"`.

---

## 2. HỆ THỐNG 6 GATES ĐIỀU PHỐI (GATE 6 LÀ PHYSICAL CANARY)

Nhằm đảm bảo an toàn tuyệt đối trước khi Push hoặc khai báo DONE:

* **Gate 1 (Decompose):** Tách biệt Code Surgery (vài phút) và Batch Job (hàng giờ).
* **Gate 2 (Patch Contract Monolith):** Giám sát qua `G11: Patch Surgery Gate` (`patch_audit.jsonl`), bắt `ANCHOR_FAIL`, `PATCH_FAIL`, vi phạm ngân sách O(1) <= 30 dòng.
* **Gate 3 (Circuit Breaker & Transient Exclusion):** Giám sát qua `G3: Worker Dispatch Gate` và `G12: Safety Valve Gate` (`safety_valve_trigger.jsonl`), bắt loop, retry quá 2 lần lỗi cấu trúc.
* **Gate 4 (Worker Fail-Fast):** Bắt buộc worker tự ngắt sau <= 3 iterations nếu scope bất khả thi.
* **Gate 5 (Closeout Gate & Invariant Step 2.6):** Giám sát qua `G5: Closeout Gate` (`gate_audit.jsonl`), bắt vi phạm thiếu rule (`INVARIANT_OR_WAIVER_MISSING`) hoặc vi phạm Invariant (`GUARDGATE_INVARIANT_VIOLATION`).
* **Gate 6 (Physical Canary Gate — `G13: Canary Verification Gate (Gate 6)`):**
  - **Nguồn log:** `logs/safe_push_audit.jsonl`, `done_gate.py`, `canary_runner.py`.
  - **Quy tắc:** Mọi sửa đổi trên repo automation phone farm BẮT BUỘC phải chạy Canary kiểm chứng trên máy thật trước khi Push hoặc declare DONE.
  - **Fail Pattern:** Bắt ngay `BLOCKED_CANARY_REQUIRED` (chặn push khi trốn chạy Canary), `BLOCKED_CANARY_VERIFY_FAILED`, `CANARY_FAIL`, `CANARY_TIMEOUT`, `CANARY_STALE`.
  - **Pass Pattern:** `CANARY_PASSED | CANARY_VERIFIED | "canary_status": "PASS" | canary_receipt_valid | Canary OK`.

---

## 3. CHECKLIST KIỂM ĐỊNH TỰ ĐỘNG CỦA WATCHDOG
* File thực thi: `D:/Taadaa/tools/gate_compliance_watchdog.py`.
* Cronjob: `farm-gate-compliance-6h-report` (chạy mỗi 6 giờ).
* Test kiểm chứng: `D:/Taadaa/tools/tests/test_gate_compliance_watchdog.py` (15/15 tests PASS).
