# Invariant Crystallization, Ratchet Amendment & Watchdog Compliance (2026-10-30)

## 1. Ngữ Cảnh Sự Cố & Chỉ Thị User
- **Bối cảnh:** Khi xử lý incident/bug trên farm (ví dụ: tab Friends/Following bị chặn fallback về For You do kẹt `_manual_guard_triggered`), Coordinator sửa code và pass unit test, nhưng buông xuôi không tự động đóng đinh Invariant Rule vào `rules.json`.
- **Chỉ thị của User (Invariant):**
  - CẤM lưu memory suông (memory text dễ bị trôi/bỏ quên).
  - BẮT BUỘC CƠ GIỚI HÓA (Mechanical Enforcement): Không để sót chờ User nhắc.
  - KHÔNG gây khóc lóc bại liệt + KHÔNG over-engineer (không đẻ ra service rườm rà hay khóa tay lúc đang code).
  - Mục đích: Chống regression mỗi lần sửa.
  - Cho phép điều tra & điều chỉnh lại rule nếu lần sửa này gây side-effect / false-positive.
  - Bắt buộc đưa vào Watchdog định kỳ để theo dõi và bắn alert nếu có vi phạm.

---

## 2. Bản Thiết Kế 4 Trụ Cột Cơ Giới Hóa (O(1))

### Trụ cột 1: Step 2.6 Closeout Invariant Gate (`crystallize.py`)
- **Vị trí:** Chèn trực tiếp vào `closeout_gate.py` (ngay sau Step 2.5 GuardGate, trước Focused Tests).
- **Phân loại Fix Commit xác định:** Dùng regex có word boundary `\b` (`^(?:\[L2-surgery\]|\b(?:fix|hotfix|bugfix|bug)\b)`), flags `--fix`, claims JSON, hoặc phát hiện diff có xóa code trong file `.py` mã nguồn.
- **2 Cửa Khép Kín (Bắt buộc chọn 1, không được để trống):**
  1. **Cửa A (Rule Mới):**
     - Phải có rule mới xuất hiện trong `rules.json` so với `base_ref`.
     - Rule's `scope.paths` bắt buộc phải bao phủ ít nhất một file mã nguồn bị sửa trong diff.
     - Hệ thống tự động dựng `reverse_diff` (chuyển các dòng `-` thành `+` để mô phỏng đoạn code lỗi trước khi sửa).
     - **Thẩm định tự động qua Engine:** Rule mới BẮT BUỘC phải **DENY `reverse_diff`** và **ALLOW `current_diff`**.
     - Nếu fix thuần thêm code (additive): Bắt buộc rule phải khai báo `params.incident_diff` và engine phải DENY payload này.
  2. **Cửa B (Waiver Một Lần Có Thẩm Quyền):**
     - Đăng ký qua `rule.py waive`.
     - Bắt buộc gắn chặt (`bind`) với `repo_name` và `diff_sha256`.
     - Ghi nhận vào ledger bất biến một chiều `consumed_waivers.jsonl`. Đã consume thì cấm tái sử dụng.
     - `NO_BEHAVIOR_RISK`: Diff tuyệt đối không được chạm vào file mã nguồn thực thi (`.py`, `.js`, v.v.).
     - `COVERED_BY_TEST`: Bắt buộc diff phải chứa file test thực tế (`test_*.py` / `*_test.py` / `tests/`) VÀ có câu lệnh test (`assert` / `def test_`).
     - `OPERATOR_OVERRIDE`: Bắt buộc phải có token ủy quyền từ User/Operator.

---

### Trụ cột 2: Cơ Chế Ratchet Nới Lỏng Khi Có Side-Effect (`rule.py amend`)
- **Vấn đề:** Rule cấm pattern có thể vô tình chặn nhầm một tính năng hợp lệ mới (False-Positive).
- **Giải pháp Bánh Cóc 1 Chiều (Ratchet):**
  - Agent chạy lệnh:
    ```bash
    python D:/Taadaa/tools/guardgate/rule.py amend <rule_id> --reason "<lý do >= 15 ký tự>" --fp-diff "<proof_diff>" --rules-path <path_rules.json> [--new-pattern "<regex>"] [--exclude-paths ...]
    ```
  - **2 Điều Kiện Ratchet Bắt Buộc:**
    1. Pattern mới bắt buộc phải **ALLOW `fp_diff`** (giải phóng tính năng hợp lệ).
    2. NHƯNG pattern mới bắt buộc **VẪN TIẾP TỤC BẮT ĐƯỢC (DENY) `incident_diff` GỐC 100%**. Tuyệt đối cấm làm yếu rule để bug cũ sống lại.
  - Cấm `exclude_paths` dạng wildcard bypass (`"."`, `"/"`, `"*"`, hoặc chuỗi < 3 ký tự).
  - Cấm sửa `rules.json` toàn cục của Farm.

---

### Trụ cột 3: Bảo Vệ Toàn Vẹn Monotonic Integrity
- Hàm `check_rules_monotonic_integrity()` thực hiện so sánh sâu toàn bộ rule từ `base_ref`:
  - Cấm xóa rule đã có ở base.
  - Cấm sửa pattern thành rỗng hoặc vô hiệu hóa (`.*`, `.+`, `(?!)`, `zzz_never`).
  - Cấm xóa file `rules.json` khỏi working tree.
  - `base_ref` bắt buộc phải resolve được qua `git rev-parse --verify {base_ref}`, nếu lỗi thì **Fail-Closed** ngay.

---

### Trụ cột 4: Giám Sát Vi Phạm Khép Kín Qua Watchdog (`gate_compliance_watchdog.py`)
- Mở rộng `LOG_DIRS` bao gồm `tools/guardgate` để quét `ledger.jsonl`, `blocks.jsonl`, `amendments.jsonl`.
- Cập nhật Gate G4 (Invariant GuardGate) và G5 (Closeout Gate):
  - Bắt toàn bộ các lỗi `INVARIANT_OR_WAIVER_MISSING`, `GUARDGATE_INVARIANT_VIOLATION`, `RULES_INTEGRITY_VIOLATION`.
- Cronjob `farm-gate-compliance-6h-report` (chạy mỗi 6h) tự động gửi cảnh báo về Telegram Farm Alert nếu phát hiện vi phạm.
