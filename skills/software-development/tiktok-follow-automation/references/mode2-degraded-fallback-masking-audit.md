# Chẩn Đoán Lệch Pha: Watchdog Báo "Đã Follow Sẵn" Do Mode 2 Degrade Sang Mode 1

## 1. Bản Chất Hiện Tượng & Cạm Bẫy Phân Tích (Anti-Pattern)
Khi báo cáo Watchdog Telegram ghi nhận:
`• Bỏ qua (...): Đã follow sẵn (N máy)`

Tuyệt đối **CẤM** suy diễn hoặc trả lời user theo các giả định sai lầm sau:
- *Giả định sai 1:* "Anchor follow dạo người ngoài nhiều nên cuộn 25 lần không ra nick farm."
  (Thực tế: 99.5% list following của Anchor Tik1/Tik2 là nick nội bộ farm).
- *Giả định sai 2:* "Nick farm đã follow hết danh sách của anchor."
  (Thực tế: Anchor có 150–300 following farm, trong khi nick non/mới chỉ follow 2–10 người, còn hàng trăm nick chưa follow).
- *Giả định sai 3:* "Máy đã follow hết quota."

## 2. Cơ Chế Thật Dưới Mã Nguồn (Root Cause Mechanism)
1. **Mode 2 (Kênh chính) bị gãy:**
   - Khi vào Profile Anchor hoặc cào danh sách Following, script vấp lỗi UI/selector:
     - `MANUAL_REVIEW: follower row không có nút follow semantic` (TikTok đổi ID nút hoặc lệch toạ độ cluster row).
     - Không mở được tab Following (`_open_following_tab` fail hoặc timeout).
   - Mode 2 kết thúc với 0 lượt follow (`mode2_followed_count: 0`).
2. **Kích hoạt Fallback tự động sang Mode 1 (`follow_engine.py`):**
   - Script đánh dấu `mode2_degraded = True`, reset status về `OK` để chuyển sang Mode 1 chạy bù ngân sách.
3. **Mode 1 search nick bù:**
   - Mode 1 lấy danh sách UID từ workbook, search từng nick.
   - Các nick search này tài khoản đã từng follow ở các ngày trước -> Mode 1 trả về `status: "skipped", reason: "đã follow sẵn (skip)"`.
4. **Watchdog nuốt lỗi (Telemetry Masking):**
   - Watchdog đọc `follow_result.json`, thấy status `OK` và reason cuối cùng là `đã follow sẵn (skip)`.
   - Watchdog phân loại máy vào nhóm `Đã follow sẵn (N máy)`, che giấu hoàn toàn việc Mode 2 thực chất đã bị gãy trước đó!

## 3. Checklist Điều Tra Hiện Trường O(1)
Khi thấy máy báo `Đã follow sẵn (N)` hoặc `followed_count == 0`:
1. Kiểm tra ngay `follow_result.json` tại `details`:
   - `details.mode2_degraded == True`?
   - `details.mode2_degraded_reasons`: Xem lý do gãy thật của Mode 2 (ví dụ: `MANUAL_REVIEW: follower row không có nút follow semantic`).
2. Nếu `mode2_degraded == True`:
   - Kết luận ngay: **Mode 2 bị lỗi UI/Selector trên anchor**, Mode 1 search bù trúng nick cũ nên mới ra nhãn "Đã follow sẵn".
   - Kiểm tra log XML / selector nút follow (`FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS`, `_cluster_follower_rows`) trên TikTok app version hiện tại.
