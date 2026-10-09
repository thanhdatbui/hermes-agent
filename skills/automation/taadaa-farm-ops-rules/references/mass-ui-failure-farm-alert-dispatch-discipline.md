# Mass UI Failure & Farm Alert Dispatch Discipline

## 1. Triệu chứng & Nguyên nhân thất bại (Báo cáo phiên sáng 14/09/2026)
- **Hiện tượng**: Báo cáo nuôi acc tổng kết Ca 1 - Phiên 2/2 (Row 2) hiển thị tổng thể Feed đạt 67/80 máy OK (83.8%). Tuy nhiên ở tầng Follow Hook: có tới 13/14 máy chạy Mode 2 fail sạch (93% lỗi) do `MANUAL_REVIEW: mở tab Đã follow fail cho <uid> sau ladder (lần 2)`.
- **Lỗ hổng điều phối**:
  1. **Tỷ lệ Feed che khuất tỷ lệ Sub-hook**: Watchdog chỉ nhìn tỷ lệ tổng thể của Feed để kết luận phiên "xong / thành công", làm chìm hoàn toàn sự cố sập đồng loạt ở sub-hook (Follow chéo / Upload video).
  2. **Lệch Target Delivery**: Watchdog cron chạy `deliver: origin` (chỉ gửi về phiên chat/group điều phối chung), không bắn thông báo động viên/cảnh báo đỏ về nhóm Farm Alert (`telegram:-5373649734`).
  3. **Thiếu cơ chế Mass Failure Breaker trong Watchdog**: Gặp lỗi lặp lại giống hệt nhau trên >=5 máy hoặc tỷ lệ lỗi của 1 hook bất kỳ > 30% nhưng watchdog chỉ gom thành 1 dòng text nhỏ `+ Lỗi script/xác minh (13): ...` thay vì bắn RED ALERT với banner `[FARM ALERT]`.

## 2. Quy tắc bắt buộc (Hard Discipline)
1. **Định nghĩa Mass Failure trên Farm**:
   - Bất kỳ sub-hook nào (Feed, Follow, Upload, 2FA, Reg) xuất hiện:
     - **Tỷ lệ lỗi >= 30%** trên tổng số máy tham gia hook đó, HOẶC:
     - **>= 5 máy gặp cùng một mã lỗi / stop_reason / exception** (ví dụ: cùng fail mở tab, cùng timeout ở 1 selector, cùng dính captive portal proxy).
2. **Hành động phản ứng tức thì**:
   - Watchdog / Runner BẮT BUỘC dispatch một message khẩn cấp với cú pháp `[FARM ALERT]` trực tiếp tới target Farm Alert (`telegram:-5373649734`).
   - CẤM TUYỆT ĐỐI che giấu hoặc gộp lỗi diện rộng thành một dòng liệt kê text thụ động trong báo cáo hoàn tất phiên.
   - Khi Coordinator audit log và phát hiện lỗi diện rộng: Phải thừa nhận lỗi báo cáo ngay lập tức, truy vết tận gốc nguyên nhân UI/mạng và phân vai Worker sửa dứt điểm trước ca chạy tiếp theo.
