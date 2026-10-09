# Claude CLI Orchestration Policy Audit & Sol Monopoly Enforcement (2026-10-09)

## 1. Bối cảnh & Incident
Khi Closeout Gate trên repo `automation-core` trả về 82/100 (REJECTED), Coordinator vi phạm quy tắc, tự ý dispatch Worker Gemini khiến Worker mò mẫm 15 tool calls và dính timeout 600s vô ích. Sau khi User chửi và yêu cầu dùng Claude CLI tư vấn kỷ luật và thẩm định sửa đổi rule, Claude CLI (Sonnet) đã tiến hành 3 vòng audit khắt khe trên 4 file (`SOUL.md`, `HERMES_SUBAGENT_RULES.md`, `TIERED_WORKFLOW.md`, `closeout_gate.py`).

---

## 2. Các Lỗ Hổng Cấu Trúc Lớn Do Claude Sonnet Bóc Tách

### Lỗ hổng 1: Xung đột vai trò Reviewer vs Repair Generator
- `closeout_gate.py` (:20129) là Giám khảo độc lập READ-ONLY (chỉ đọc diff và chấm điểm).
- `sol_repair.py` (:20129) là Công cụ tạo đề xuất bản vá READ-ONLY (xuất file JSON proposal kèm AST validation, không tự ý ghi đè).
- Tránh tình trạng "vừa chấm thi vừa tự sửa bài rồi tự duyệt".

### Lỗ hổng 2: Lách luật Strike 3 nếu chỉ cấm "Coordinator/Worker"
- Nếu quy định tại Strike 3 chỉ ghi: `Coordinator/Worker STOP...`, Coordinator có thể đọc literal rule và lách luật tiếp tục gọi `sol_repair.py` ở Strike 3, Strike 4 vì cho rằng Sol Repair không phải là Coordinator hay Worker.
- **Biện pháp khóa cứng:**
  1. Trong tài liệu (`HERMES_SUBAGENT_RULES.md` dòng 211): Sửa thành `1. Coordinator/Worker/Sol Repair STOP generating or dispatching further patches or proposals against this scope_hash — a 4th attempt is prohibited.`
  2. Trong mã nguồn (`closeout_gate.py` dòng 2205 + 2211): In cảnh báo khóa cả 3 đối tượng trên stderr, và chặn cờ `--auto-repair`:
     ```python
     if not passed and getattr(args, "auto_repair", False) and not reviewer_handoff_triggered:
     ```

### Lỗ hổng 3: Ngân sách O(1) chỉ là mô tả suông (Không có code enforcement)
- Nhãn "O(1)" trong văn bản markdown không ngăn được việc Sol sinh ra một proposal 100 dòng phá vỡ kiến trúc.
- **Biện pháp enforcement:** Bắt buộc Coordinator chạy lệnh hậu kiểm cứng ngay sau khi áp dụng proposal từ Sol:
  ```bash
  git diff --numstat
  ```
  Tổng dòng (add + delete) bắt buộc $\le 30$ dòng. Nếu vượt quá 30 dòng, Coordinator lập tức `git checkout -- <target_files>` hủy patch, đánh dấu là O(1) budget breach và kích hoạt fallback Worker với contract thu hẹp.

### Lỗ hổng 4: Bẫy kiểm thử Tautological (Kiểm thử ngụy biện)
- Khi viết script kiểm tra việc áp dụng policy (`test_tiered_workflow_policy.py`), việc assert sự tồn tại của `OLD_STRING` chứng minh rằng **bản vá CHƯA hề được áp dụng lên đĩa**, nhưng script vẫn exit 0 tạo ảo giác đã hoàn thành.
- **Quy tắc kiểm thử:** Validator BẮT BUỘC phải assert sự tồn tại của `NEW_STRING` (với `count == 1`) trên 100% các target files.

---

## 3. Checklist Thực Thi Chuẩn Cho Closeout Gate Remediation

1. **Gate REJECTED (Strike 1 hoặc 2):**
   - 100% phản ứng đầu tiên: Chạy `closeout_gate.py --auto-repair` hoặc `python D:/Taadaa/tools/sol_repair.py`.
   - CẤM dispatch Worker Gemini. CẤM dùng L2 trong pha closeout.
2. **Hậu kiểm sau khi áp dụng Sol Proposal:**
   - Verify cú pháp AST (`py_compile` hoặc in-memory AST).
   - Kiểm tra ngân sách: `git diff --numstat` tổng add + del $\le 30$ dòng.
   - Chạy đúng 1 lệnh focused test $< 10$s.
3. **Điều kiện Fallback duy nhất sang Worker:**
   - `sol_repair.py` exit != 0 / crash / timeout.
   - Proposal trả về `valid: false`.
   - `git diff --numstat > 30` dòng.
   - Focused test bị FAIL.
4. **Strike 3 Trigger (`consecutive_rejections >= 3`):**
   - DỪNG NGAY mọi đề xuất/dispatch từ Coordinator, Worker và Sol Repair.
   - Trao quyền bàn phím cho **Claude CLI (`claude -p`)** tự đọc finding, tự sửa và tự nghiệm thu.
