# Crystallize Fix Invariant & Ratchet Amendment Architecture (2026-10-29)

## 1. Bản Chất Bài Toán & Triết Lý Vận Hành
Khi sửa lỗi (bugfix / incident recovery), agent thường mắc lỗi:
1. Sửa code xong là coi như xong việc, không đóng đinh quy tắc phòng ngừa vào hệ thống cơ giới (GuardGate / rules.json), dẫn đến agent phiên sau vào sửa/refactor làm tái phát đúng lỗi cũ (regression).
2. Lưu bài học vào LLM memory text suông: không có hiệu lực cưỡng chế thực tế, context dài là trôi mất.
3. Thiết lập GuardGate rule quá cứng nhắc hoặc regex lỗi: gây bại liệt (paralysis), khóa cứng tay chân agent khi gặp ca nghiệp vụ mới hợp lệ hoặc tính năng mới cần mở rộng.

### 3 Nguyên Tắc Cốt Lõi (Đồng Thuận Coordinator & Claude Code):
1. **Gate chỉ kiểm tra lúc Closeout, không khóa tay agent lúc đang sửa code:** Trong quá trình mổ xẻ, thử nghiệm, agent hoàn toàn tự do sửa file, chạy test mà không bị hook chặn ngang gây bại liệt.
2. **Quy tắc phân loại xác định (Deterministic, không đoán mò):** Dùng regex cứng trên commit message (`^\[L2-surgery\]`, `^(fix|hotfix)`) để nhận diện commit sửa lỗi, không dùng LLM để suy đoán.
3. **Cơ chế Ratchet (Bánh cóc 1 chiều):** Rule sinh ra để chống tái phát đúng cái bug đó (Vector DENY). Nếu sau này gặp case nghiệp vụ mới cần mở rộng, agent được phép nới lỏng (Vector ALLOW mới) miễn là không làm sống lại cái bug cũ.

---

## 2. Thiết Kế Cơ Giới Hóa Step 2.6 Trong `closeout_gate.py`
Chèn Step 2.6 ngay sau Step 2.5 (GuardGate check) và trước Step 3 (Focused test execution):
* **Nhận diện fix:** Commit subject khớp `^(fix|hotfix|bugfix)` hoặc `^\[L2-surgery\]`.
* **Điều kiện tiên quyết để PASS Gate:**
  * **Trường hợp A (Có Invariant Rule mới):** Tập rule ID hiện tại có thêm rule mới so với base ref (`git show <base>:rules.json`). Rule mới phải thỏa mãn **Regression Proof O(1)**:
    - Tạo `reverse_diff` (đảo ngược dòng `-` thành `+` của bản fix).
    - GuardEngine phải **DENY** `reverse_diff` (chứng minh code lỗi cũ bị chặn bởi chính rule_id mới) và **ALLOW** diff thật (bản fix được thông qua).
    - Nếu là fix thuần thêm code (additive - không có dòng xóa trong diff): Bắt buộc rule phải khai báo danh sách `params.incident_diff` và GuardEngine phải DENY synthetic diff của incident_diff này.
    - Scope của rule BẮT BUỘC phải bao phủ ít nhất 1 file mã nguồn đang được sửa trong diff (chống rule ảo phạm vi zzz.py che cho fix app.py).
    - **Monotonic Integrity Sâu Sắc:** Toàn bộ rule từ base_ref không được phép bị xóa, không được làm rỗng pattern, không được đổi pattern thành wildcard vô hiệu hóa (`.*`, `(?!)`, `zzz_never`).
  * **Trường hợp B (Invariant Waiver Hợp Lệ):** Khai báo `--waiver-id` trỏ vào bản ghi `guardgate/invariant_waivers.jsonl`:
    - Ràng buộc cứng: Bắt buộc bind với `repo_name` và `diff_sha256` (cấm waiver không bind).
    - Single-use: Lưu vào append-only ledger `consumed_waivers.jsonl`. Đã dùng là không thể dùng lại.
    - `COVERED_BY_TEST`: Bắt buộc diff chạm file test thực tế (`test_*.py` / `*_test.py` / `tests/`) VÀ diff có câu lệnh test thực tế (`assert ` hoặc `def test_`).
    - `NO_BEHAVIOR_RISK`: Chỉ áp dụng cho docs (`.md`, `.txt`) hoặc config; TUYỆT ĐỐI KHÔNG được chạm file mã nguồn (`.py`, v.v.).
    - `OPERATOR_OVERRIDE`: Bắt buộc xác thực đúng `OPERATOR_TOKEN_SECRET` của User Sudo.

---

## 3. Cơ Chế Điều Chỉnh Rule Linh Hoạt (Adaptive Rule Tuning / `rule.py amend`)
Khi một rule đã ban hành vô tình gây false-positive hoặc cản trở tính năng mới:
1. **Lệnh nới lỏng hợp lệ:**
   `python D:/Taadaa/tools/guardgate/rule.py amend <rule_id> --rules-path <repo/rules.json> --fp-diff "<proof_diff>" --new-pattern "<regex>" --reason "<lý do >= 15 ký tự>"`
2. **Thẩm định Ratchet 2 chiều bắt buộc:**
   - Vector ALLOW mới (đoạn diff tính năng mới bị chặn oan `--fp-diff`) bắt buộc phải được **ALLOW**.
   - Mẫu lỗi gốc `params.incident_diff` **BẮT BUỘC VẪN PHẢI BỊ DENY 100%** bởi pattern mới. Nếu pattern mới buông lỏng bug cũ -> Bị từ chối ngay lập tức: `RATCHET REJECTED`.
   - Cấm `exclude_paths` chứa `"."`, `"/"`, `"*"` hoặc chuỗi < 3 ký tự.
   - Cấm amend đụng vào `rules.json` toàn cục của Farm.
   - Nếu thỏa mãn: Rule tự động cập nhật nguyên tử, tăng version, ghi audit trail, nới lỏng đúng chỗ mà không làm tái phát bug cũ.

---

## 4. Phòng Ngừa False-Positive Trong Predicates
- **Exclude Test Paths:** Bổ sung tham số `exclude_paths` vào `check_generic_prohibited_pattern` để tự động bỏ qua các file `tests/**` (nơi chứa các chuỗi bad fixture dùng để assert), tránh việc rule tự bắn vào chính unit test của nó.
- **Fail-Closed An Toàn:** Loại bỏ `except ImportError: pass` tại Step 2.5 `closeout_gate.py`. Nếu GuardGate bị lỗi import hoặc crash thì báo `BLOCKED_INFRA` ngay, không để lọt qua.
