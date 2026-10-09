# No-Cap Remediation Loop Trap & Candidate Bloat Discipline

## 1. Bản chất sự cố (Session Incident 2026-10-05)
User phàn nàn: *"t thấy cứ đẻ ra task r sửa suốt đéo hiểu lắm do cơ chế closeout gate update bị ngu à, mỗi lần chốt phiên có khi nửa ngày đéo xong"*.

Qua điều tra hiện trường và audit log (`gate_audit.jsonl`):
- Reviewer trả về `REJECTED` liên tục (score dao động 57 -> 77 qua hơn 10 vòng review từ 14:18 đến 16:13).
- Mỗi lần reject, Coordinator lại tự động lập một Patch Contract mới và dispatch Worker sửa tiếp, rơi vào vòng lặp vô tận kéo dài cả buổi.

## 2. Ba nguyên nhân kỹ thuật cốt lõi

### A. Bẫy tư duy "No-Cap Remediation" (Vòng lặp không trần)
- Khi policy ghi *"No-cap remediation loop: tới APPROVED hoặc hard blocker thật"* nhằm chống bỏ cuộc sớm, Coordinator hiểu máy móc thành: **phải liên tục đẻ task sửa code** chừng nào điểm chưa >= 85.
- Thực tế: `closeout_gate.py` không tự đẻ task; chính Coordinator điều phối đẻ task lặp đi lặp lại.

### B. Vòng xoáy phình to Diff (Candidate Bloat Feedback Loop)
- Candidate sửa đổi chính `closeout_gate.py` và test tích hợp có diff lên tới 92 KB (+612 / -70 lines).
- Mỗi vòng remediation nhằm khắc phục nhận xét của reviewer lại thêm code xử lý ngoại lệ, thêm telemetry, thêm test mock -> **diff càng ngày càng to ra**.
- Diff càng to, bề mặt rủi ro (risk surface) càng rộng, Reviewer càng phát hiện thêm góc khuất để trừ điểm (Code Architecture, Farm Safety, Telemetry).

### C. Tràn Sol Web -> Fallback Terra Codex gây chậm trễ cực nặng
- Sol Web (`review` / `:20129`) có ngưỡng trần an toàn `SOL_WEB_DIFF_FALLBACK_BYTES = 24_000` (24 KB).
- Với diff 70-92 KB, gate 100% tự động fallback sang `cx/gpt-5.6-terra-high` để gửi un-truncated payload 4 MiB.
- Terra Codex nuốt diff khổng lồ mất 1-3 phút mỗi lượt review. Khi gặp lỗi kết nối hoặc timeout (như `192.168.110.123:20129` connection refused lúc 15:44, read timeout lúc 15:50), mỗi lần thử lại nhân đôi thời gian chờ.
- Kết quả: 10 vòng review + sửa code + chạy test ngốn hàng giờ đồng hồ.

## 3. Quy tắc ngăn chặn bắt buộc (Anti-Spin & Scope Ceiling Invariants)

1. **Ngăn chặn Candidate Bloat trước Gate:**
   - Nếu diff của candidate vượt quá **25 KB** hoặc **> 2 files / > 100 lines**, CẤM tiếp tục vá chắp vá (patch on patch).
   - Phải dừng lại rà soát: Candidate có đang bundle quá nhiều việc không? Có đang tự sửa chính công cụ gate trong khi làm task khác không?
   - Nếu candidate bị phình to, bắt buộc phân rã (decompose) hoặc thu gọn diff trước khi chạy lại review.

2. **Chặn vòng lặp Remediation vô hạn (Anti-Spin Ceiling):**
   - Không được hiểu "no-cap" thành "đẻ task vô hạn".
   - Sau **3 vòng remediation liên tiếp** mà điểm số vẫn không cải thiện (dao động dưới 85) hoặc diff tăng thêm mà không hội tụ:
     - BẮT BUỘC coi đây là `NO_VALID_REMEDIATION_PATH` do **Scope Contamination** hoặc **Architecture Defect**.
     - DỪNG đẻ thêm Worker task.
     - Lập báo cáo cô lập: chỉ rõ diff hiện tại, nguyên nhân kẹt điểm (breakdown), và yêu cầu phân rã scope thay vì cố chấp vá tiếp.

3. **Tách biệt hoàn toàn Candidate Code và Tooling/Rule:**
   - Tuyệt đối không để diff của `closeout_gate.py`, hook, hoặc file rule (`TIERED_WORKFLOW.md`) đi chung vào candidate của task nghiệp vụ farm.
   - Luôn dùng `--files <file1> <file2>` để cô lập 100% diff dưới 15-20 KB, giữ Sol Web review nhanh trong 15-30 giây.
