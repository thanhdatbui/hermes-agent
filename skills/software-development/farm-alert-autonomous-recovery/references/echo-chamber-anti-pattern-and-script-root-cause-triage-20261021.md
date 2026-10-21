# Case Study: Anti-Pattern Báo Cáo Suông (Echo-Chamber) & Kỷ Luật Điều Tra Tận Gốc Script Khi Nhận Alert (2026-10-21)

## 1. Bài Học Chấn Chỉnh Từ Operator
- **Tình huống thực tế:** Khi cronjob watchdog gửi báo cáo tổng kết phiên nuôi acc/lướt feed có các máy fail (M24 kẹt switcher, M65 lỗi app, M74 timeout, M10/M30 offline), Coordinator chỉ đơn thuần tóm tắt lại nội dung bằng tiếng Việt rồi thông báo cho người dùng mà không có bất kỳ hành động điều tra hay can thiệp kỹ thuật nào.
- **Phản hồi gắt gao của Operator:**
  > *"Là sao mày đéo fix lỗi mà thông báo ăn lồn à"*
  > *"Là mày phải điều tra script r fix chứ"*

## 2. Phân Định Trách Nhiệm Cốt Lõi Của Coordinator
1. **Triệt tiêu vai trò Echo-Chamber:** Báo cáo watchdog gửi vào chat là tín hiệu vận hành tự động (Alert), KHÔNG PHẢI câu hỏi của User. Mục tiêu tối thượng của Coordinator là đưa các máy lỗi trở lại trạng thái sẵn sàng (READY / DONE) hoặc xác định chính xác blocker kèm chứng cứ thực tế. Việc ngồi im phiên dịch log là vi phạm nghiêm trọng.
2. **Quy trình 4 bước bắt buộc khi nhận Farm Alert:**
   - **Bước 1 - Phân loại O(1):**
     * Lỗi phần cứng/vật lý: Dùng `python D:/Taadaa/tools/inspect_machine.py <N>` để kiểm tra. Nếu báo `device not found`, xác nhận cáp lỏng/mất ADB vật lý. Phân nhóm này chỉ ghi nhận blocker vật lý, không cố gõ lệnh vô ích.
     * Lỗi phần mềm/logic: Kiểm tra ngay các máy còn lại (màn hình, current focus, ATX server).
   - **Bước 2 - Lật ngược Call-stack & Artifacts:**
     * Truy cập thư mục live run mới nhất (`D:/Taadaa/runtime/<cluster>/live/<date>/<row-time>/`).
     * Đọc `log.jsonl`, `summary.txt`, và các file `fail_*.xml` / screenshot tại thời điểm văng lỗi.
     * Đối chiếu call-stack xem script dừng ở step nào (`STOPPED: [06]`, `ACCOUNT_MISSING`, `ATX_SESSION_UNAVAILABLE`).
   - **Bước 3 - Điều tra tận gốc mã nguồn Script:**
     * Đọc hàm tương ứng trong mã nguồn script runner (`social_reg_v1.py`, `feed_swipe_smoke.py`, `tiktok_login_v1.py`).
     * Tìm ra vì sao điều kiện if/else trong script bị sai lệch trên thiết bị thực tế (ví dụ: nút bị che ở mép đáy 1920px, hoặc marker Profile bị nhận nhầm thành Home Feed).
   - **Bước 4 - Thi công bản vá O(1) & Canary kiểm chứng:**
     * Vá đúng ốc lỏng (ngân sách T1 <= 15 dòng, hoặc T2 dispatch worker Haiku).
     * Chạy script kiểm chứng trên đúng máy lỗi.
     * Chỉ báo cáo kết quả khi có bằng chứng thật (`final_status: success` hoặc log/receipt). CẤM báo "đã fix" khi chưa qua canary.
