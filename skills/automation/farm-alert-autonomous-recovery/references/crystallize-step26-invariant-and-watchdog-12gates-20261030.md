# Invariant Crystallization Gate (Step 2.6) & Watchdog 12 Gates Governance

## 1. Cơ Chế Cơ Giới Hóa Bắt Buộc Tại Closeout Gate (Step 2.6 — `crystallize.py`)
Mọi commit sửa lỗi (`[L2-surgery]`, `fix:`, `hotfix:`, `bug:` hoặc diff có xóa code nguồn `.py`) BẮT BUỘC phải đi qua một trong hai cửa trước khi được phép chạy test và review:

### Cửa A: Invariant Rule Mới trong `rules.json`
- **Reverse Diff Verification:** Gate tự động đảo ngược dòng xóa (`-`) thành thêm (`+`) để dựng đoạn code lỗi ban đầu (`reverse_diff`).
- **Ràng buộc:** Rule mới bắt buộc phải **DENY `reverse_diff`** và **ALLOW `current_diff`**.
- **Scope Grounding:** `scope.paths` của rule mới bắt buộc phải bao phủ ít nhất một file mã nguồn đang được sửa trong commit.
- **Additive Fix:** Nếu bản fix thuần thêm code (không có dòng xóa), rule bắt buộc phải khai báo danh sách `params.incident_diff` và đoạn mẫu này phải bị engine DENY.
- **Monotonic Integrity:** So sánh sâu toàn bộ rule từ `base_ref`: cấm xóa rule, cấm làm rỗng pattern (`.*`, `.+`, `zzz_never`), cấm đặt `exclude_paths` quá rộng (`.`, `/`, `*`, `.py`).

### Cửa B: Audited Single-Use Waiver (`rule.py waive`)
- **Category Hợp lệ:**
  - `COVERED_BY_TEST`: Bắt buộc diff phải chứa file test thật (`test_*.py`, `*_test.py`) VÀ có câu lệnh test (`assert`, `def test_`).
  - `NO_BEHAVIOR_RISK`: Chỉ áp dụng cho tài liệu (`.md`, `.txt`) hoặc config; CẤM áp dụng cho file mã nguồn (`.py`, `.js`, v.v.).
  - `OPERATOR_OVERRIDE`: Bắt buộc secret token ủy quyền của Operator. Cấm agent tự cấp.
  - `ONE_OFF_DATA_FIX` / `ENV_ONLY`: Phải giải trình $\ge 20$ ký tự.
- **Binding Bắt Buộc:** Mọi waiver phải ghim cứng `repo_name` và `diff_sha256`.
- **Sổ cái Một Chiều (Append-only Ledger):** Đã ghi nhận vào `consumed_waivers.jsonl` thì không bao giờ được dùng lại lần 2.

---

## 2. Cơ Chế Ratchet Nới Lỏng Rule Khi Có Side-Effect (`rule.py amend`)
Khi một rule gây chặn nhầm code hợp lệ mới (False-Positive), agent được quyền điều tra và nới lỏng an toàn bằng lệnh:
```bash
python D:/Taadaa/tools/guardgate/rule.py amend <rule_id> \
  --reason "<lý do >= 15 ký tự>" \
  --fp-diff "<diff hợp lệ bị chặn oan>" \
  --rules-path <path/to/repo/rules.json> \
  [--new-pattern "<regex_thu_hẹp>"] \
  [--exclude-paths <path_cụ_thể>]
```
- **Ràng buộc Bánh Cóc 1 Chiều (Ratchet Invariant):**
  1. Pattern mới bắt buộc phải **tiếp tục DENY 100% `incident_diff` gốc** của sự cố ban đầu (cấm làm yếu rule làm sống lại bug cũ).
  2. Pattern mới phải **ALLOW đoạn `--fp-diff`** hợp lệ.
  3. `exclude_paths` cấm các giá trị rộng như `.`, `/`, `*` hoặc chuỗi $< 3$ ký tự.
  4. Cấm agent tự ý sửa `rules.json` toàn cục của Farm.

---

## 3. Hệ Thống 12 Gates Giám Sát Tuân Thủ (`gate_compliance_watchdog.py`)
Hệ thống watchdog định kỳ 6h quét 3 thư mục `logs/`, `runtime/audit_logs/`, `tools/guardgate/` để phát hiện và báo động Telegram:

1. **G1 (Visual Evidence):** Bắt buộc `MEDIA:` thật từ hiện trường.
2. **G2 (Planning Gate):** Bắt buộc có Plan ID của Sol trước khi Worker thi công.
3. **G3 (Worker Dispatch Gate):** Giám sát timeout, quota, command error của worker.
4. **G4 (Invariant GuardGate):** Quét `ledger.jsonl`, bắt mọi vi phạm DENY, BLOCK, QUARANTINE, INVARIANT_VERIFICATION_FAILED.
5. **G5 (Closeout Gate):** Quét `gate_audit.jsonl`, bắt các phán quyết REJECTED, INVARIANT_OR_WAIVER_MISSING, GUARDGATE_INVARIANT_VIOLATION.
6. **G6 (Pre-Push Safe Guard):** Quét `safe_push_audit.jsonl`, chặn đẩy commit lỗi lên git.
7. **G7 (Anti-Scan & Terminal Guard):** Quét `guard_scan_audit.jsonl`, chặn quét đĩa diện rộng (`find`, `grep -r`, `glob`).
8. **G8 (Cronjob Window Guard):** Quét `console_block_audit.jsonl`, chặn can thiệp ngoài giờ an toàn.
9. **G9 (Farm & GPM Proxy Guard):** Quét cả `proxy_guard_audit.jsonl` và `gpm_proxy_guard_audit.jsonl`, chống rò rỉ IP thật trên cả mobile và desktop profile.
10. **G10 (Claude Quota Gate):** Quét `claude_quota_audit.jsonl`, chống cạn quota Claude.
11. **G11 (Patch Surgery Gate):** Quét `patch_audit.jsonl`, bắt vi phạm mất anchor duy nhất, lỗi cú pháp hoặc vượt quá ngân sách $\le 30$ dòng.
12. **G12 (Safety Valve Gate):** Quét `safety_valve_trigger.jsonl`, giám sát kích hoạt ngắt khẩn cấp và loop interceptor.
