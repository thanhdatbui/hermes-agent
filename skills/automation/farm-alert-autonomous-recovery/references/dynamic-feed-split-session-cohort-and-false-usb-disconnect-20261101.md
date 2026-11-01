# Dynamic Feed Split Session Cohort & False USB Disconnect Triage (01/11/2026)

## 1. Hiện Tượng Farm Alert Hàng Loạt
- **Báo cáo từ Watchdog:** `🚨 [FARM ALERT] PHÁT HIỆN LỖI NUÔI FEED HÀNG LOẠT (109 máy lỗi) - Ca 1 - Phiên 1/2 (Sáng) (Pool {1, 2, 7})`.
- **Phân loại lỗi từ Watchdog:**
  * Kibe (Máy 1-80): 51 máy báo "Mất kết nối ADB/USB".
  * Admin (Máy 201-280): 34 máy báo "Mất kết nối ADB/USB".
  * Kèm một số máy kẹt Device Lock hoặc Wi-Fi.

## 2. Nguyên Nhân Gốc: Cơ Chế Cohort 2 Phiên & Phân Nhóm False Positive
1. **Chia phiên liên hoàn trong Ca (Split Session Cohorts):**
   - Farm vận hành chế độ **Dynamic Feed** (`USE_DYNAMIC_FEED=1`) với định dạng thư mục `row-0-HHMMSS`.
   - Mỗi ca chuẩn gồm 2 phiên:
     * **Phiên 1/2 (06:00 – 08:00):** Chạy cohort 1 (khoảng 38 máy Kibe, 51 máy Admin) tại thư mục `row-0-060025`.
     * **Phiên 2/2 (08:00 – 12:00):** Chạy tiếp cohort 2 tại thư mục `row-0-080051`.
2. **Lỗi logic tính toán Expected Machines của Watchdog:**
   - Lúc 08:16, watchdog quét thư mục `row-0-060025` khi Phiên 1/2 đóng cửa.
   - Hàm `get_expected_machines_for_cluster(cluster, row_num=0)` tính toán `slot_idx = int(row_num) - 1 = -1`. Python list negative index lấy phần tử cuối cùng (Slot 8) thay vì Pool {1, 2, 7}, sau đó fallback ra toàn bộ 80 máy (`fleet`).
   - Mọi máy không thuộc cohort 1 (chưa chạy ở Phiên 1) bị gán nhãn trạng thái `no-run-recorded`.
3. **Cạm bẫy quy kết phân loại lỗi (`classify_feed_failure`):**
   - Trong `scripts/watchdog/formatters.py`, bộ lọc phân loại lỗi có điều kiện:
     `if any(k in r for k in (..., "no-run-recorded", ...)): return "Mất kết nối ADB/USB"`
   - Việc gom `no-run-recorded` vào category "Mất kết nối ADB/USB" khiến các máy chưa đến lượt chạy bị vu khống là rớt cáp/sụt hub USB.

## 3. Quy Trình Điều Phối Triage O(1) Cho Coordinator
1. **Xác minh Fleet tổng O(1) ngay lập tức:**
   - Khi nhận Farm Alert báo mất ADB/USB hàng chục máy, BẮT BUỘC gọi:
     `python D:/Taadaa/tools/inspect_machine.py` (không tham số, timeout=30s).
   - Nếu output xác nhận Kibe đạt ~77/80 và Admin đạt ~79/80 thiết bị `device`, kết luận ngay **False Alarm** về phần cứng/USB.
2. **Đối soát hiện trường thư mục Live:**
   - Kiểm tra `D:/Taadaa/runtime/<cluster>/live/<date>/`:
     Xem thư mục Phiên 2 (`row-0-080051`) đã được tạo lúc 08:00 chưa.
   - Kiểm tra thư mục con `machines/` của Phiên 2: xác nhận danh sách máy đang chạy chính là các máy vừa bị báo `no-run-recorded` ở Phiên 1.
3. **Kỷ luật an toàn tuyệt đối:**
   - CẤM tự ý kill tiến trình `multi-machine-feed-session` hoặc `run_tiktok.py` đang nuôi Phiên 2.
   - CẤM báo cáo hoảng loạn hoặc đề xuất sửa phần cứng/cáp USB khi chưa đối soát qua `inspect_machine.py`.
