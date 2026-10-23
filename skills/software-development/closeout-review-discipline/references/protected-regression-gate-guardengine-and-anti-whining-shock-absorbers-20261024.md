# Protected Regression Gate (GuardEngine) & 3-Shock-Absorber Anti-Whining Architecture (2026-10-24)

## 1. Bối Cảnh & Vấn Đề Gốc Rễ (Session-to-Session Flip-Flop Loop)
- **Triệu chứng lặp lại:** Session trước khắc phục sự cố sập hàng loạt 16 máy do micro-drop USB Hub bằng cách nâng `connection_wait_timeout >= 20.0s`, `connection_retry_attempts >= 3` (Case 162). Sang session sau, khi thấy máy mất cáp thật bị chờ 50 phút, Agent tự ý hạ `connection_wait_timeout` xuống 4.0s để "fail-fast", xóa sạch thành quả của session trước.
- **Tại sao text policy trong AGENTS.md thất bại:** Text policy là xác suất (probabilistic nudge). Attention của LLM suy giảm khi context dài hoặc khi model tự tin vào suy luận cục bộ của mình. Reviewer LLM nhìn diff thấy "hạ timeout để fail-fast" hợp lý nên vẫn APPROVED nếu không có test cơ học khóa cứng.
- **Yêu cầu bắt buộc:** Bắt buộc phải có Compulsion Gate cơ học tất định (GuardEngine), chạy $O(1)$ bằng so sánh tĩnh diff trước khi cho phép commit/push.

## 2. Nguy Cơ "Khóc Lóc" & 3 Chốt Giảm Xóc Cơ Học (Claude Sonnet Verdict)
Nếu GuardEngine chỉ ném `DENY` + `sys.exit(1)`, Agent tưởng bị bắt lỗi và sẽ quay sang viết sớ phân trần theo Rule 8 thay vì hành động tiếp. Để biến `DENY` thành điểm rẽ hành động bắt buộc, hệ thống tích hợp 3 chốt giảm xóc:

1. **Chốt 1: Message Mandate Enum Đóng & Điền Sẵn Path O(1)**
   In duy nhất 2 lựa chọn máy đọc được, điền sẵn file path cụ thể, không in text mô tả chung chung:
   ```text
   [GuardEngine DENY] rule=<rule_id>
   VIOLATION: <reason>
   REQUIRED_NEXT_ACTION (chọn đúng 1, không có lựa chọn thứ 3):
     (a) REVERT_EXACT   -> git checkout -- "<target_file>"
     (b) JUSTIFIED_BYPASS -> gọi sol_repair với evidence_bundle={'rule_id': '...', 'reason': '...'}
   NO_OTHER_ACTION_VALID. Không có hành động thứ 3 (bao gồm: viết văn giải thích, xin lỗi, báo cáo rồi dừng).
   ```

2. **Chốt 2: Auto-Quarantine O(1) Qua `git stash`**
   Khi bật cờ `auto_quarantine=True`, Gate tự động chạy `git stash push --keep-index -m guardgate-quarantine-<rule_id>-<ts> -- <file>`. File mã nguồn lập tức trở về trạng thái sạch trước vi phạm, triệt tiêu khoảng trống nhận thức khiến Agent loay hoay tự sửa.

3. **Chốt 3: Strike 3 Cơ Học & Handoff sang `sol_repair_queue.jsonl`**
   Đếm số lần vi phạm cùng `rule_id` trong phiên qua `ledger.jsonl`. Nếu vi phạm liên tiếp 3 lần:
   - Tự động ghi record mở ticket vào `sol_repair_queue.jsonl`.
   - Khóa cứng phát ngôn của Agent: Chỉ được in đúng 1 câu:
     `[STRIKE-3-HANDOFF] Đã 3 lần vi phạm cùng rule trong phiên này. Đã mở ticket sol_repair #<id>. KHÔNG tự sửa thêm lần thứ 4 — chỉ cần báo User: 'Đã mở sol_repair #<id> cho rule <rule_id>, chờ review.'`

## 3. Kiến Trúc Triển Khai (`D:/Taadaa/tools/guardgate`)
- `rules.json`: Danh mục bất biến (Case 162 USB timeout $\ge 20s$, Case 161 follow limit $\le 0$).
- `predicates.py`: Các hàm kiểm tra AST/Regex tĩnh $O(1)$ (`check_case_162_timeout_floor`, `check_case_161_follow_limit_ceiling`).
- `runner.py`: CLI runner có HMAC signed receipt, local ledger và 3 chốt giảm xóc.
- Kiểm tra toàn bộ diff phiên qua lệnh:
  ```bash
  python guardgate/runner.py --repo <path_repo> --base HEAD~1
  ```

## 4. Bẫy Grace File Budget Ceiling (`max_files <= 4`)
- Trong `closeout_policy.json`, ngân sách Grace quy định `budget: {"max_files": 4, "max_lines": 500}`.
- Nếu một commit gộp quá 4 files (ví dụ 5 files), dù điểm số đạt 80-84 điểm (Grace Band), Gate vẫn từ chối cấp token với lỗi `[CLOSEOUT_TOKEN_SKIPPED: score 82 rejected: grace_conditions_unmet]`.
- **Khắc phục:** Bắt buộc tách nhỏ thành các commit nguyên tử $\le 4$ files theo đúng phạm vi nghiệp vụ (ví dụ tách riêng commit sửa flow thiết bị 2 files và commit sửa flow feed 3 files).
