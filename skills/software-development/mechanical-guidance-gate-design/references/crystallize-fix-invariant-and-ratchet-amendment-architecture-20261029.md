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
    - GuardEngine phải **DENY** `reverse_diff` (chứng minh code lỗi cũ bị chặn) và **ALLOW** diff thật (bản fix được thông qua).
  * **Trường hợp B (Invariant Waiver):** Khai báo `--waiver-id` trỏ vào bản ghi `guardgate/invariant_waivers.jsonl`:
    - Enum: `NOT_EXPRESSIBLE_AS_PATTERN`, `COVERED_BY_TEST <test_id>`, `ONE_OFF_DATA_FIX`, `ENV_ONLY`, `OPERATOR_OVERRIDE`.
    - Gắn với `diff_sha256`, có TTL, dùng 1 lần. Vượt quá 2 waiver/tuần yêu cầu Operator token.

---

## 3. Cơ Chế Điều Chỉnh Rule Linh Hoạt (Adaptive Rule Tuning / `amend_rule.py`)
Khi một rule đã ban hành vô tình gây false-positive hoặc cản trở tính năng mới:
1. **Ghi nhận sự cố chặn:** Lần bị chặn được ghi vào `guardgate/blocks.jsonl` với `block_id`.
2. **Lệnh nới lỏng hợp lệ:**
   `python D:/Taadaa/tools/guardgate/amend_rule.py <rule_id> --incident-ref <entry_id> --fp-diff <diff> --reason FALSE_POSITIVE`
3. **Thẩm định Ratchet 2 chiều bắt buộc:**
   - Vector ALLOW mới (đoạn diff tính năng mới bị chặn oan) phải được **ALLOW**.
   - Toàn bộ vector DENY cũ (đoạn diff của incident gốc) **BẮT BUỘC VẪN PHẢI BỊ DENY 100%**.
   - Nếu thỏa mãn cả 2: Rule tự động cập nhật nguyên tử, ghi audit trail, không gây bại liệt cho workflow tiếp theo.

---

## 4. Phòng Ngừa False-Positive Trong Predicates
- **Exclude Test Paths:** Bổ sung tham số `exclude_paths` vào `check_generic_prohibited_pattern` để tự động bỏ qua các file `tests/**` (nơi chứa các chuỗi bad fixture dùng để assert), tránh việc rule tự bắn vào chính unit test của nó.
- **Fail-Closed An Toàn:** Loại bỏ `except ImportError: pass` tại Step 2.5 `closeout_gate.py`. Nếu GuardGate bị lỗi import hoặc crash thì báo `BLOCKED_INFRA` ngay, không để lọt qua.
