# Case Study: False Farm Alert do Watchdog Race Condition & Safety Gate Skip Follow

## Bối cảnh & Hiện tượng
- Telegram nhận Farm Alert:
  `🚨 [FARM ALERT] PHÁT HIỆN LỖI DIỆN RỘNG (>10 MÁY)`
  `Follow Hook Lỗi UI/Script (22 máy): 1, 5, 6, 8, 10, 11, 12, 14, 15, 17, 18, 19, 21, 23, 25, 28, 35, 38, 59, 66, 75, 77`
- Danh sách 22 máy bị cảnh báo hoàn toàn trùng khớp với danh sách các máy đã hoàn tất lướt Feed thành công (`status == "success"`).

## Nguyên nhân gốc rễ (Root Cause)
1. **Grace Period Expiry vs Batch Finish Delay**:
   - Phiên 1 kết thúc khung giờ lý thuyết lúc 01:30.
   - Watchdog có cơ chế `grace period = 20 phút`, tới đúng 01:50:00 là ép chốt báo cáo (`can_report_session == True`).
   - Lúc 01:50:21, 22 máy chạy nhanh đã xong Feed thành công. Các máy còn lại (M2, M3, M4, M7, M9, M16, M26, M29, M31...) kết thúc trong khoảng từ 01:50:23 đến 01:52:36 (chỉ trễ hơn 20s đến 2 phút).
2. **Safety Gate Skip Follow (Nick < 5 video)**:
   - Quy tắc an toàn farm: Nick chưa đủ 5 video đăng không được follow chéo nhằm chống bị TikTok nhả follow hàng loạt. Code sinh `follow_result.json` với `status: "skipped"` và `reason: "under-5-videos-follow-disabled"`.
   - Trong quá trình runner đang ghi chốt hoặc watchdog quét đợt đầu lúc hết grace period, việc đối chiếu giữa `all_machines[m]` (feed success) và `all_follows[m]` bị lệch pha thời điểm (race condition), khiến watchdog coi các máy Feed thành công mà chưa load được follow kết quả là lỗi script/xác minh (`fl_error`).
   - Ngưỡng kích hoạt Farm Alert là `> 10 máy`, dẫn đến việc bắn Red Alert giả về nhóm điều hành.

## Quy tắc Coordinator khi nhận Farm Alert "Follow Hook Lỗi UI/Script (>10 máy)"
1. **Kiểm tra tương quan danh sách máy**:
   - So sánh danh sách máy bị báo lỗi Follow với danh sách máy thành công Feed ở báo cáo phiên. Nếu 100% trùng khớp hoặc gần như toàn bộ máy xong Feed bị gán lỗi Follow, nghi ngờ ngay race condition hoặc watchdog parsing.
2. **Inspect O(1) file `follow_result.json` của 1-2 máy canary**:
   - Đọc trực tiếp `follow_result.json` tại `live/<date>/<run>/machines/machine_<N>/<timestamp>/follow_result.json`.
   - Nếu `status == "skipped"` với reason `under-5-videos-follow-disabled` hoặc `sensitive-skip`: Đây là hành vi ĐÚNG THIẾT KẾ của Farm Safety Gate, KHÔNG phải lỗi script hay sập UI.
3. **Kiểm tra phiên kế tiếp / summary hoàn chỉnh**:
   - Khi runner hoàn tất toàn bộ các máy và phiên tiếp theo chạy, các máy đều trả về log sạch và về trạng thái nghỉ (`Dozing`, sleep, lock released).
