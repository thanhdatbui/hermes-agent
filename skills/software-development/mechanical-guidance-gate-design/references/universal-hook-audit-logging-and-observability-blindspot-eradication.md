# Universal Hook Audit Logging Parity & Observability Blindspot Eradication (Xóa Bỏ Điểm Mù Giám Sát 6H)

## 1. Bối Cảnh & Vấn Đề (The Observability Blindspot Paradox)
Khi hệ thống thiết kế nhiều lớp phòng thủ cơ giới hóa (Hooks, GuardGate, Git Hooks, Canary Gate), một giả định sai lầm phổ biến là: "Đã có báo cáo định kỳ 6h (`farm-gate-compliance-6h-report`) thì chắc chắn 100% các lần vi phạm đều được phản ánh".

Thực tế kiểm toán toàn diện hệ thống cho thấy báo cáo 6H chỉ mới bao quát được ~75%, để lại **25% điểm mù chí mạng**:
1. **Các Hook "Chặn Trong Im Lặng" (Silent Terminal Exits):**
   - Các hook `guard_device_bulkhead.py` (chặn tap tay ADB, thiếu lock máy), `guard_pytest_scope.py` (chặn pytest toàn repo), `guard_model_drift.py` (chặn đổi model review), `guard_closeout_discipline.py` (chặn xóa diff git) khi phát hiện vi phạm chỉ in JSON ra stdout rồi `sys.exit(0)`.
   - Chúng **hoàn toàn không ghi bản ghi audit nào** vào `runtime/audit_logs/*.jsonl`.
   - Kết quả: Agent bị chặn liên tục trong phiên, nhưng Watchdog 6H hoàn toàn "mù", báo cáo gửi về Operator vẫn hiển thị `NO_EVIDENCE` hoặc 0 vi phạm!
2. **Các File Nhật Ký Bị Bỏ Quên (Uningested Audit Logs):**
   - Hệ thống có `proxy_guard_audit.jsonl` (từng chặn 589 lần gán proxy sai), `claude_quota_audit.jsonl` (chặn gọi Claude khi quota 5h >= 85%), `patch_audit.jsonl` (ghi nhận ANCHOR_FAIL khi patch code).
   - Tuy nhiên `gate_compliance_watchdog.py` chỉ khai báo 8 Gate với các `source_file` cố định, bỏ sót các nguồn telemetry này.

---

## 2. Toàn Cảnh 13 Chốt Chặn Cơ Giới Hóa Hệ Thống
Hệ thống phòng thủ Farm được chia làm 3 tầng:

### Tầng 1: Runtime Pre/Post Hooks (10 Hooks cắm vào Hermes Engine)
1. `guard_broad_grep.py`: Auto-Rewrite timeout (60s/360s) + Block quét đĩa diện rộng (`guard_scan_audit.jsonl`).
2. `guard_read_file_size.py`: Auto-Rewrite kẹp 200 dòng cuối cho file > 10MB thiếu slice.
3. `guard_cronjob_safety.py`: Block lệnh thiếu CREATE_NO_WINDOW cướp chuột, bắt buộc `no_agent=True` (`console_block_audit.jsonl`).
4. `guard_android_proxy.py`: Block proxy domain/IP công khai ngoài Internet (`proxy_guard_audit.jsonl`).
5. `guard_device_bulkhead.py`: Block tap tay ADB, ép device lock khi đụng máy thật.
6. `guard_dispatch_contract.py`: Block subagent sửa code, khóa trần 15 calls (`dispatch_audit.jsonl`).
7. `guard_pytest_scope.py`: Block lệnh pytest quét toàn bộ repo làm treo 900s.
8. `guard_model_drift.py`: Block đổi model review sang sol-pro/instant trong closeout.
9. `guard_closeout_discipline.py`: Block git reset --hard, git checkout ., chặn clarify evasion.
10. `record_device_failure.py`: Post-tool Circuit Breaker ghi nhận máy lỗi liên tiếp.

### Tầng 2: AST Invariant GuardGate (1 Engine phân tích mã nguồn)
11. `guardgate/runner.py` + `rules.json`: Phân tích AST, khóa sàn timeout USB Case 162 (>= 20s), trần follow popup Case 161 (<= 0), auto-quarantine qua git stash (`ledger.jsonl`).

### Tầng 3: Git Border Hooks (2 Hooks khóa cứng biên giới)
12. `tools/.git/hooks/pre-push`: Khóa cứng `git push` nếu thiếu vé duyệt `closeout_gate.py` APPROVED >= 85 (`safe_push_audit.jsonl`).
13. `nuoi acc/.git/hooks/pre-commit`: Khóa cứng commit nếu chứa `uiautomator dump` thô.

---

## 3. Yêu Cầu Cơ Học Bắt Buộc (Mandatory Architectural Invariants)

### Chuẩn 1: Mandatory Audit Persistence Invariant (Cấm Chặn Không Ghi Log)
- Mọi hàm `block()` hoặc `deny()` trong 100% pre-tool hooks BẮT BUỘC phải thực hiện ghi log tuần tự trước khi in stdout:
  ```python
  log_dir = Path("D:/Taadaa/runtime/audit_logs")
  log_dir.mkdir(parents=True, exist_ok=True)
  with open(log_dir / "<hook_name>_audit.jsonl", "a", encoding="utf-8") as f:
      f.write(json.dumps(payload, ensure_ascii=False) + "\n")
  ```
- Tuyệt đối cấm hook chỉ print stdout rồi exit(0) mà bỏ quên audit persistence. Không có audit log = mù quan sát vận hành.

### Chuẩn 2: Dual Action Strategy (Auto-Rewrite vs Action Mandate)
- **Lỗi vặt (Tham số an toàn, timeout, file size):** Bắt buộc Auto-Rewrite. Cấm block bắt Agent mò mẫm qua 8–9 turn.
- **Lỗi cấm (Scan đĩa, device lock, push lậu):** Block cứng, nhưng BẮT BUỘC cấp sẵn `LỆNH THOÁT O(1)` copy-paste được ngay tại đầu message.

### Chuẩn 3: Watchdog Full-Spectrum Source Ingestion
- `gate_compliance_watchdog.py` phải bổ sung các nguồn log đang thiếu (`proxy_guard_audit.jsonl`, `claude_quota_audit.jsonl`, `patch_audit.jsonl`).
- Báo cáo 6H phải đảm bảo không có bất kỳ cơ chế cơ giới hóa nào bị "bỏ rơi" ngoài tầm mắt của Operator.
