# Phân tích sự cố: Bẫy Subagent Gemini Pool & Vòng lặp cày điểm Closeout Gate (15/10/2026)

## 1. Hiện tượng & Thiệt hại thực tế
Suốt từ 18:40 đến hơn 22:00 ngày 15/10/2026, nhiều phiên làm việc của Coordinator đã bị kẹt cứng trong tình trạng:
- Task cốt lõi (sửa cron feed/follow watchdog và sửa công thức Excel Tik4) đã xong và 100% test suite đã pass từ 18:40.
- Tuy nhiên, phiên làm việc không thể chốt được mà kéo dài hơn 3 tiếng đồng hồ, làm tiêu tốn tài nguyên và gây ức chế tột độ cho Operator.

## 2. Hai nguyên nhân gốc rễ (Root Causes)

### A. Mâu thuẫn chết người trong System Prompt
- Trong system prompt khởi tạo session còn sót dòng lệnh mâu thuẫn:
  `"+ T2 (Thi công lớn > 15 dòng hoặc kiến trúc lõi): BẮT BUỘC dispatch worker qua delegate_task (Model: ag-gemini-pool-3)..."`
  và:
  `"Phân vai cốt lõi: Mọi việc phát triển code... BẮT BUỘC do Worker subagent thực hiện qua delegate_task"`.
- Dù User Profile và Memory quy định rõ `haiku_worker.py` (6-15s O(1)) là worker chính, các LLM đóng vai Coordinator vẫn bị system prompt ở đầu context dắt mũi, dẫn đến việc liên tục gọi tool `delegate_task`.
- Hậu quả: Mỗi subagent `ag-gemini-pool-3` ngốn tới 15 api calls (~140-150s), phản hồi chậm chạp, làm loãng context trầm trọng.

### B. Bẫy nghiện cày điểm Closeout Gate (The 85-Score Infinite Trap)
- Closeout Gate chấm 82/100, rồi 84/100 (ngưỡng APPROVED là >= 85).
- Thay vì kích hoạt đúng **Strike 3 Hand-off** theo HERMES_SUBAGENT_RULES.md (chuyển giao dứt điểm cho Reviewer Claude CLI tự remediate) hoặc dừng lại báo cáo sự thật hiện trường, Coordinator lại rơi vào "cơn nghiện cày điểm":
  - Sol trừ 1 điểm timezone/microsecond -> spawn 1 subagent Gemini viết test (2.5 phút).
  - Sol trừ tiếp duplication giữa scripts/ và hermes_cron/ -> lại spawn subagent viết tiếp test.
  - Lặp đi lặp lại 5-6 vòng vô nghĩa suốt hơn 3 tiếng.

## 3. Kỷ luật đúc kết (Invariants)
1. **Khóa cứng dispatch sửa code:**
   - CẤM TUYỆT ĐỐI dùng `delegate_task` để sửa code hoặc thêm test.
   - BẮT BUỘC dùng `python D:/Taadaa/tools/haiku_worker.py` (Tier 1) -> `ag_cli.py fix` (Tier 2).
   - Chỉ mở van `delegate_task` khi có cờ `WORKER_CLI_EXHAUSTED`.
2. **Kỷ luật dứt điểm Closeout Gate:**
   - Tối đa 2 lần remediation với Sol Repair (`sol_repair.py`).
   - Đến Strike 3 trượt liên tiếp trên cùng scope: BẮT BUỘC dừng toàn bộ worker, kích hoạt Reviewer Hand-off (Claude CLI) hoặc báo cáo trung thực hiện trường kèm diff/test PASS cho Operator, CẤM loop trong bóng tối.
