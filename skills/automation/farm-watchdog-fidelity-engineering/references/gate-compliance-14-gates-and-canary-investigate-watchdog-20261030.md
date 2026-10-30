# Gate Compliance Watchdog: 14-Gate Full Spectrum Architecture (2026-10-30)

## 1. Context & Motivation
Hệ thống giám sát định kỳ `gate_compliance_watchdog.py` (chạy mỗi 6h qua cronjob `farm-gate-compliance-6h-report`) ban đầu chỉ theo dõi 10 gate cơ bản, gây ra các điểm mù nguy hiểm:
1. **Thiếu Gate A (Điều tra & Khảo sát):** Không phát hiện khi Coordinator lén dùng `delegate_task` cho việc sửa code thay vì khảo sát (`subagent_edit_blocked`).
2. **Thiếu Gate 6 (Canary Verification trên thiết bị thật):** Không phát hiện khi một task automation phone farm trốn chạy Canary trên máy thật (`BLOCKED_CANARY_REQUIRED`).
3. **Thiếu Invariant Step 2.6 tại Closeout:** Không phát hiện khi commit fix bug bị từ chối do thiếu Rule/Waiver (`INVARIANT_OR_WAIVER_MISSING`) hoặc vi phạm Invariant xương máu (`GUARDGATE_INVARIANT_VIOLATION`).
4. **Thiếu Patch Surgery & Safety Valve:** Không cảnh báo khi Coordinator làm mất anchor (`ANCHOR_FAIL`) hoặc hệ thống kích hoạt van ngắt khẩn cấp (`safety_valve_trigger`).
5. **Bỏ sót thư mục `tools/guardgate/`:** Watchdog chỉ quét `logs/` và `runtime/audit_logs/`, bỏ sót toàn bộ `ledger.jsonl`, `blocks.jsonl`, `amendments.jsonl`, `consumed_waivers.jsonl`.

---

## 2. 14-Gate Matrix & Monitored Audit Sources

```
+---------------------------------------------------------------------------------------------------+
| GATE ID | TÊN GATE                              | NGUỒN AUDIT SCAN        | FAIL TRIGGER PATTERN  |
+---------+---------------------------------------+-------------------------+-----------------------+
| G1      | Visual Evidence Gate                  | vision_receipts.jsonl   | EVIDENCE_MISSING      |
| G2      | Planning Gate (Gate B)                | dispatch_planner.jsonl  | PLAN_MISSING/FAILED   |
| G3      | Worker Dispatch Gate (Gate C)         | dispatch.jsonl, audit   | TIMEOUT/QUOTA/NO_DIFF |
| G4      | Invariant GuardGate                   | tools/guardgate/ledger  | DENY/BLOCK/QUARANTINE |
| G5      | Closeout Gate (Step 2.6 Invariant)    | gate_audit.jsonl        | INVARIANT_OR_WAIVER.. |
| G6      | Pre-Push Safe Guard                   | safe_push_audit.jsonl   | returncode != 0       |
| G7      | Anti-Scan & Terminal Guard            | guard_scan_audit.jsonl  | action: block         |
| G8      | Cronjob Window Guard                  | console_block_audit     | decision: block       |
| G9      | Farm & GPM Proxy Guard                | proxy_guard_audit.jsonl | gpm_proxy/android blk |
| G10     | Claude Quota Gate                     | claude_quota_audit      | EXEC_BLOCKED_QUOTA    |
| G11     | Patch Surgery Gate                    | patch_audit.jsonl       | ANCHOR_FAIL/BUDGET    |
| G12     | Safety Valve Gate                     | safety_valve_trigger    | SAFETY_VALVE/SOL_FB   |
| G13     | Canary Verification Gate (Gate 6)     | safe_push_audit.jsonl   | BLOCKED_CANARY_REQ..  |
| G14     | Investigation Gate (Gate A)           | dispatch_audit.jsonl    | subagent_edit_blocked |
+---------------------------------------------------------------------------------------------------+
```

---

## 3. Implementation Details

### A. Mở rộng `LOG_DIRS` trong `gate_compliance_watchdog.py`
```python
DEFAULT_ROOT = Path(r"D:\Taadaa")
LOG_DIRS = ("logs", "runtime/audit_logs", "tools/guardgate")
LOG_SUFFIXES = {".log", ".jsonl", ".txt", ".json"}
```

### B. Mở rộng G4 & G5 bắt Invariant Crystallize
```python
    Gate("G4", "Invariant GuardGate",
         _rx(r"\"status\":\s*\"ALLOW\""),
         _rx(r"\"status\":\s*\"(?:DENY|BLOCK|QUARANTINE)\"|\"event\":\s*\"rule_block\"|\"error\":\s*\"(?:INVARIANT_VERIFICATION_FAILED|MISSING_INVARIANT_OR_WAIVER|RULES_INTEGRITY_VIOLATION)\""),
         "ledger"),
    Gate("G5", "Closeout Gate",
         _rx(r"verdict\W+APPROVED\b|\[GuardEngine\s+ALLOW\]|CLOSEOUT_PASSED|Invariant Crystallized:"),
         _rx(r"verdict\W+(?:REJECTED|CHANGES_REQUESTED|NEEDS_FIX|INVARIANT_OR_WAIVER_MISSING|GUARDGATE_INVARIANT_VIOLATION|RULES_INTEGRITY_VIOLATION)\b|\[Crystallize\s+DENY\]|\[GuardGate\s+DENY\]"),
         "gate_audit"),
```

### C. G9 bao phủ cả Android Farm Proxy và Desktop GPM Proxy
```python
    Gate("G9", "Farm & GPM Proxy Guard",
         _rx(r"android_proxy_allow|gpm_proxy_allow"),
         _rx(r"android_proxy_domain_block|ANDROID_PROXY_BLOCKED|gpm_profile_no_proxy_block|GPM_PROXY_BLOCKED"),
         "proxy_guard_audit"),
```

### D. G13 (Canary Gate 6) & G14 (Investigation Gate A)
```python
    Gate("G13", "Canary Verification Gate (Gate 6)",
         _rx(r"CANARY_PASSED|CANARY_VERIFIED|\"canary_status\":\s*\"PASS\"|canary_receipt_valid|Canary OK"),
         _rx(r"BLOCKED_CANARY_REQUIRED|BLOCKED_CANARY_VERIFY_FAILED|CANARY_FAIL|CANARY_TIMEOUT|CANARY_STALE"),
         "safe_push_audit"),
    Gate("G14", "Investigation Gate (Gate A)",
         _rx(r"\"route\":\s*\"investigate_allowed\"|\"action\":\s*\"allow\"|\"stage\":\s*\"investigate_done\""),
         _rx(r"subagent_edit_blocked|INVESTIGATION_BUDGET_EXCEEDED|INVESTIGATION_UNAUTHORIZED"),
         "dispatch_audit"),
```

---

## 4. Verification & Testing Invariants
* Bộ test `tests/test_gate_compliance_watchdog.py` bắt buộc phải assert `len(res["gates"]) == len(GATES) == 14`.
* Bắt buộc có test case `test_g4_g5_guardgate_invariant_watchdog` chứng minh vi phạm Invariant DENY từ `tools/guardgate/ledger.jsonl` và `INVARIANT_OR_WAIVER_MISSING` từ `runtime/audit_logs/gate_audit.jsonl` chuyển gate thành FAIL.
* Chống False-Positive trong mock signature: Chuỗi mẫu cấm (như `os.walk('D:...')`) trong code test phải được phân tách để tránh GuardGate quét nhầm khi kiểm tra diff của chính watchdog.
