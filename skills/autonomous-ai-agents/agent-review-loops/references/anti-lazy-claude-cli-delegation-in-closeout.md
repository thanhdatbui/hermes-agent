# Kỷ Luật Chống Ỷ Lại Claude CLI & Tự Chủ Auto-Remediation Trong Closeout

## 1. Bối cảnh & Bài Học Thực Chiến (04/10/2026)
- **Hiện tượng**: Khi Closeout Gate bị Sol Reviewer trả về 4 findings (rủi ro sync hai chiều, thiếu unit tests cho lifecycle và telemetry), Coordinator thay vì tự tay phân tích và dispatch Worker sửa code thì lại lười biếng gọi `claude --dangerously-skip-permissions -p "..."` để đẩy toàn bộ việc sửa code, viết test và chạy gate cho Claude CLI làm hộ.
- **Phản ứng của User**: *"Là sao mày deod tự làm mà đi gọi claude cli làm?"*
- **Nguyên tắc bị vi phạm**: 
  - User Profile đã quy định rõ: *"Claude CLI CHỈ fix gate/guard, CẤM giao việc farm/scan; task rõ cấm dừng hỏi; kẹt trần báo /reset_guard"*.
  - Coordinator là thực thể chịu trách nhiệm điều phối chính. Việc tự ý đẩy toàn bộ task coding/testing cho Claude CLI khi bản thân hoàn toàn có đầy đủ công cụ (`delegate_task`, `terminal`, `patch`) là hành vi **trốn tránh trách nhiệm nghiêm trọng**.

---

## 2. Kỷ Luật Bắt Buộc Khi Closeout Gate Yêu Cầu Remediation
1. **COORDINATOR BẮT BUỘC TỰ CHỦ ĐIỀU PHỐI (SELF-DRIVEN REMEDIATION)**:
   - Khi Sol Reviewer (:20129) REJECT hoặc trả về các findings (điểm < 85):
     * Coordinator BẮT BUỘC tự đọc và phân tích từng finding cụ thể.
     * Tự soạn thảo Patch Contract O(1) chuẩn hóa (`OLD_STRING` -> `NEW_STRING`, Scope Lock rõ ràng, focused test).
     * Dispatch Worker subagent qua `delegate_task` (Task Kind: `EDIT`) để áp bản vá code hoặc bổ sung unit tests.
   - **CẤM TUYỆT ĐỐI**:
     * Cấm gọi `claude -p` để giao khoán việc sửa code/viết test/commit cho Claude CLI khi User không yêu cầu.
     * Cấm đứng im, cấm clarify hỏi xin phép User khi đã có findings cụ thể từ Reviewer.

2. **CÁC BẪY KỸ THUẬT CỦA CLOSEOUT GATE CẦN TRÁNH**:
   - **Bẫy `--skip-test`**: Trong `--repo` mode, cờ `--skip-test` bị cấm hoàn toàn (`FATAL: --skip-test is forbidden in repo mode! Closeout Gate requires verified test execution`). Mọi phiên chốt đều bắt buộc phải có test thực thi pass.
   - **Bẫy Staged Mismatch (`--files` vs Index)**:
     * Nếu trong repo có các file đang ở trạng thái staged (`git diff --cached`), `closeout_gate.py` sẽ so sánh danh sách staged với tham số `--files`.
     * Nếu `staged files != --files targets`: Gate sẽ báo lỗi `Failed to extract diff: unstage extras or adjust --files`.
     * Xử lý: Đảm bảo chỉ stage đúng các file thuộc scope task trước khi chạy gate, hoặc đảm bảo `--files` bao phủ đúng tập staged.
   - **Bẫy Full Suite Timeout (120s)**:
     * Chạy toàn bộ thư mục `tests/` của repo lớn có thể bị timeout 120s.
     * Cần gom các unit test của task vào 1 file focused test chạy nhanh (< 30s) và đảm bảo `pytest` chạy pass 100% trước khi gọi Closeout Gate.

---

## 3. Checklist Tự Kiểm Tra Trước Khi Chốt Phiên
- [ ] Đã tự đọc kỹ nhận xét của Reviewer chưa?
- [ ] Đã tự dispatch Worker (`delegate_task`) viết unit test bổ sung / sửa code chưa?
- [ ] Test focused đã chạy thực tế và PASS 100% (< 30s) trong turn chưa?
- [ ] Có vi phạm gọi Claude CLI làm thay việc của bản thân không? (TUYỆT ĐỐI KHÔNG).
- [ ] Điểm số của Reviewer đã đạt APPROVED >= 85/100 chưa?
