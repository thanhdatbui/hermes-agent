# Batch Alert: Masked Device Serial & Micro-drop USB Triage

## 1. Bản chất chữ `device:<serial>` trong Alert
Khi nhận Alert có signature:
`Device serial 'device:<serial>' was not found in adb devices.`
- **Nguyên nhân:** KHÔNG PHẢI lỗi nối chuỗi chuỗi prefix hay gõ sai định danh. Đây là do hàm `mask_value(serial, prefix='device')` trong `multi_machine_feed_session.py` (hoặc `core.account_config`) tự động hash/mask chuỗi serial gốc để bảo mật thông tin trước khi gom cụm alert.
- **Cách tra cứu serial gốc:**
  - Tra mapping trong `machine-map-80.txt` hoặc file workbook `taikhoan_run_safe.xlsx` theo số máy (`extra.machine`).
  - Hoặc đối chiếu `device_id` / `serial` trong `run_manifest.json` của phiên chạy tương ứng.

## 2. Quy trình điều tra log chi tiết (Tránh phán đoán vội vã)
Khi gặp alert hàng loạt máy offline / không tìm thấy serial:
1. **Kiểm tra timestamp trong `log.jsonl` hoặc `summary.txt`:**
   - Đọc trực tiếp các dòng lỗi trong thư mục run gần nhất (`D:/Taadaa/runtime/kibe/live/.../log.jsonl`).
   - Nếu nhiều máy (ví dụ 5-10 máy) fail trong **cùng 1 giây duy nhất** (ví dụ cùng lúc 07:08:47): Đây là dấu hiệu kinh điển của **USB Hub controller micro-drop / sụt áp tức thời** khi dồn tải nhiều worker song song.
   - Kiểm tra `start_time` và `end_time` của step: Nếu chỉ diễn ra trong ~100-200ms thì do vòng lặp kiểm tra preflight (`_validate_child_adb`) duyệt `attempts` quá nhanh không có khoảng nghỉ sleep.
2. **Kiểm tra trạng thái hiện tại (O(1)):**
   - Đọc lại `adb devices` ngay lập tức.
   - So sánh danh sách máy báo lỗi với `adb devices`:
     - Máy nào đã xuất hiện lại -> Micro-drop tạm thời, đã tự kết nối lại.
     - Máy nào vẫn vắng mặt -> Mất kết nối vật lý thực sự (lỏng cáp, treo cổng hub, hết pin).
3. **Báo cáo rõ ràng:**
   - Phân loại rõ ràng số máy đã tự online trở lại vs số máy offline vật lý thực sự.
   - Nêu rõ thời điểm văng đồng loạt từ log để người vận hành nắm rõ tình trạng phần cứng hub.
