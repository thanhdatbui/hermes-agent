# Gate Compliance 14-Gates Watchdog Architecture (2026-10-30)

## 1. Mục Tiêu & Phạm Vi Giám Sát
Hệ thống `gate_compliance_watchdog.py` (chạy định kỳ 6h/lần qua cronjob `farm-gate-compliance-6h-report`) được nâng cấp toàn diện từ 10 Gate lên 14 Gate khép kín, bao quát toàn bộ 2 hệ thống cốt lõi:
- **Chuỗi Chặng A-B-C (Investigation -> Planning -> Worker Execution).**
- **Chuỗi 6 Gates Điều Phối & An Toàn Thiết Bị (bao gồm Gate 6 Canary Máy Thật).**

## 2. Danh Mục 14 Gates Chuẩn Hóa
1. **G1 (Visual Evidence Gate):** `vision_receipts.jsonl` — Chống báo thành công mù thiếu ảnh MEDIA:.
2. **G2 (Planning Gate - Gate B):** `dispatch_planner.jsonl` — Bắt buộc có Plan của Sol (`SOL_PLAN_ID`) trước khi dispatch.
3. **G3 (Worker Dispatch Gate - Gate C):** `dispatch.jsonl`, `dispatch_audit.jsonl` — Giám sát Worker timeout/no-diff.
4. **G4 (Invariant GuardGate):** `tools/guardgate/ledger.jsonl`, `blocks.jsonl` — Bắt vi phạm Invariant xương máu (`DENY`, `BLOCK`, `QUARANTINE`).
5. **G5 (Closeout Gate):** `runtime/audit_logs/gate_audit.jsonl` — Bắt vi phạm Closeout v2 & Step 2.6 (`INVARIANT_OR_WAIVER_MISSING`, `GUARDGATE_INVARIANT_VIOLATION`).
6. **G6 (Pre-Push Safe Guard):** `logs/safe_push_audit.jsonl` — Giám sát tính toàn vẹn lệnh git push.
7. **G7 (Anti-Scan & Terminal Guard):** `guard_scan_audit.jsonl` — Chặn quét đĩa diện rộng (`find`, `grep -r`, `glob recursive`).
8. **G8 (Cronjob Window Guard):** `console_block_audit.jsonl` — Chặn can thiệp máy ngoài khung giờ an toàn.
9. **G9 (Farm & GPM Proxy Guard):** `proxy_guard_audit.jsonl`, `gpm_proxy_guard_audit.jsonl` — Chặn rò rỉ IP thật trên cả Mobile Farm và GPM Desktop Profiles.
10. **G10 (Claude Quota Gate):** `claude_quota_audit.jsonl` — Ngắt tự động trước khi cạn kiệt hạn mức Claude CLI.
11. **G11 (Patch Surgery Gate):** `patch_audit.jsonl` — Giám sát mất anchor monolith (`ANCHOR_FAIL`) và vượt ngân sách O(1).
12. **G12 (Safety Valve Gate):** `safety_valve_trigger.jsonl` — Bắt sự cố ngắt khẩn cấp, timeout Sol và Loop Interceptor.
13. **G13 (Canary Verification Gate - Gate 6):** `safe_push_audit.jsonl` — Bắt vi phạm trốn chạy Canary trên máy thật (`BLOCKED_CANARY_REQUIRED`, `CANARY_FAIL`).
14. **G14 (Investigation Gate - Gate A):** `dispatch_audit.jsonl` — Bắt vi phạm Coordinator dùng subagent để sửa code trái phép (`subagent_edit_blocked`) hoặc vượt budget 8 calls.

## 3. Mở Rộng Thư Mục Log Quét (`LOG_DIRS`)
Đã đưa `tools/guardgate` vào danh mục quét tự động:
```python
LOG_DIRS = ("logs", "runtime/audit_logs", "tools/guardgate")
```
Giúp Watchdog tự động đối soát toàn bộ sổ cái `ledger.jsonl`, `blocks.jsonl`, `amendments.jsonl` và `consumed_waivers.jsonl` của GuardGate.
