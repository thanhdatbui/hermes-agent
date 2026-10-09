# Closeout Remediation Drift, Executable Verification & Test Contract Discipline

## Bối cảnh & Bài học thực tế

Trong phiên điều phối closeout gate:
1. **Lầm tưởng Executable Path đã có Auto-Remediation**:
   - Tài liệu/kỹ năng (`session-close-protocol`, `auto-remediation-until-approved-gate-loop.md`) mô tả rằng khi điểm review `< 85`, script `closeout_gate.py` sẽ tự động sửa qua `--auto-remediate` cho đến khi đạt điểm.
   - Tuy nhiên, trong thực tế lệnh `closeout_gate.py --help` **không hề có** flag `--auto-remediate`. Script chạy một lần, thấy `< 85` thì ném exit 1 và thoát.
   - **Bài học**: Không được tin tưởng vào mô tả chính sách/tài liệu để suy diễn rằng công cụ thực thi (executable binary/script) đã tự động làm việc đó. Coordinator BẮT BUỘC phải kiểm tra trực tiếp CLI flags (`--help`), và nếu công cụ không tự lặp thì chính Coordinator phải chủ động thực thi vòng lặp Remediation (Đọc review findings → Dispatch sửa / vá hiện trường O(1) → Chạy focused test → Gọi lại gate).

2. **Cấm vội vã báo BLOCKED khi nhận điểm < 85 lần đầu**:
   - Khi Sol Auditor chấm `80/100` hoặc `82/100` (`REJECTED`), đây là **trạng thái chuyển tiếp cần sửa (recoverable transient state)**, không phải là kết thúc phiên hay một lý do để Coordinator dừng lại báo BLOCKED và chờ User giục.
   - User phản ứng gay gắt khi thấy Coordinator vừa nhận `REJECTED` đã vội báo dừng/blocked thay vì tiếp tục sửa tiếp các điểm bị trừ.
   - Coordinator phải bám đuổi: trích xuất `key_findings`, xác định xem thiếu test case, thiếu telemetry hay rủi ro logic, tiến hành sửa dứt điểm, rồi chạy lại gate.

3. **Kỷ luật sửa Test vs Sửa Code (Chống sửa test để lách Gate)**:
   - Khi reviewer chấm điểm và có test fail trong focused test suite, cần phân biệt rõ:
     - (a) **Lỗi logic thực tế**: Phải sửa code production, không được sửa test để lách.
     - (b) **Test contract cũ / stale expectation**: Ví dụ test suite cũ assert rằng `ready_to_close=False` thì phải trả `REJECTED`, trong khi quy tắc mới là `Score Supremacy` (điểm rubric >= 85 thì ghi đè `ready_to_close=True`). Chỉ khi có quy tắc/contract mới được chứng minh và phê duyệt thì mới cập nhật test expectation tương ứng.
     - (c) **Bảo vệ tính trung thực**: Mọi thay đổi test suite phải đi kèm lý do rõ ràng, pass focused test sạch sẽ, không được xóa bỏ assertion để né lỗi.

4. **Tách biệt Trạng thái Vận hành Farm vs Trạng thái Closeout Code**:
   - Vận hành farm thật (M3 Row 8 nạp nick mới `@oanhuong7758`, verify profile ảnh thật, Excel đồng bộ) có thể đã hoàn tất 100%.
   - Nhưng trạng thái Code / Git vẫn CHƯA XONG nếu chưa vượt qua Closeout Gate (`APPROVED >= 85`) và chưa commit/push.
   - Báo cáo cho User phải rành mạch: máy móc đã an toàn, nhưng phiên code đang ở vòng remediation gate, không báo "xong hết" khi chưa qua gate và cũng không báo "blocked" khi chưa đi hết các vòng tự sửa.
