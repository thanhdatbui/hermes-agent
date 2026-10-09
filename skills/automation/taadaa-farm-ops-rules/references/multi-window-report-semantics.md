# Multi-Window Watchdog Report Semantics & Timezone Gating

## Bối Cảnh Lỗi
Watchdog hỗ trợ nhiều khung giờ (ca sáng 08:30–11:15 và ca tối 20:15–23:45). Khi hết khung ca sáng lúc 11:26, điều kiện `after_window` được kích hoạt đúng nhưng hàm format báo cáo lại hard-code:
`Hết khung giờ ca tối (sau 23:30)` và `Kết quả ca tối nay`.
Hậu quả: Farm nhận được thông báo sai lệch ngữ cảnh, gây hiểu nhầm hệ thống bị trôi giờ hoặc chạy sai lịch.

## Quy Tắc Bắt Buộc Khi Viết Formatter Dùng Chung Nhiều Khung Giờ
1. **Truyền `now_dt` hoặc nhãn ngữ cảnh cụ thể (Dynamic Period Resolution)**:
   - Formatter hoặc caller phải suy luận nhãn ca động từ `now_dt` thay vì hardcode:
     - Giờ sáng (06:00 đến trước 14:00): nhãn `ca sáng`, cutoff tương ứng (ví dụ `sau 11:15`), session label `ca sáng nay`.
     - Giờ tối/đêm: nhãn `ca tối`, cutoff tương ứng (ví dụ `sau 23:45`), session label `ca tối nay`.
   - Cấm dùng chuỗi tĩnh "ca tối" trong mọi nhánh format áp dụng cho cả ngày.

2. **Bẫy Tái Phát Khi Nâng Cấp Telemetry Mới (Regression via Telemetry Enhancements)**:
   - Khi bổ sung các khối thống kê mới (như phân loại cụm lỗi `session_failed_by_reason`, delta thành công `session_uploaded_machines`, hay khối tổng hợp cụm phụ Admin), lập trình viên rất dễ mắc lỗi copy-paste hardcode chuỗi `ca tối nay` / `CHI TIẾT CỤM LỖI CA TỐI NAY`.
   - BẮT BUỘC: mọi khối text mới thêm vào formatter phải dùng biến `period_label` / `shift_label` (`ca sáng nay` / `ca tối nay`), TUYỆT ĐỐI CẤM gán chuỗi tĩnh.

3. **Đồng bộ giữa trigger logic và report text**:
   - Nếu `is_after_evening_window` hoặc `is_after_window` kích hoạt trên mốc 11:15–11:35 thì thông điệp trạng thái phải nói về ca sáng.
   - Thống kê phiên (`session_stats`) phải hiển thị đúng ca (`ca sáng nay` hoặc `ca tối nay`).

3. **Yêu cầu Test Focused (< 30s)**:
   - Tối thiểu 2 test case cho hàm format report:
     - Case 1: Giờ sáng kết thúc (ví dụ `11:26:00 Asia/Ho_Chi_Minh`) -> Chứa "ca sáng", "sau 11:15", tuyệt đối không chứa "ca tối", "sau 23:30".
     - Case 2: Giờ tối kết thúc (ví dụ `23:45:00 Asia/Ho_Chi_Minh`) -> Chứa "ca tối", "sau 23:30".

4. **Deploy & Đồng Bộ Runtime**:
   - Khi sửa file trong repository (`deploy/hermes-home/scripts/...`), cần kiểm tra xem daemon có đang chạy file tương đương trong runtime local (`~/AppData/Local/hermes/scripts/...`) hay không.
   - Luôn đồng bộ bản sửa sang local runtime sau khi test pass để đảm bảo lần chạy kế tiếp của watchdog nhận đúng logic mới.
