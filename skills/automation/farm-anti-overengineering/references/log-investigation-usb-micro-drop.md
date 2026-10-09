# Quy Trình Điều Tra Log Alert Khi Báo Lỗi Thiết Bị Không Thấy / Offline

Khi nhận Farm Alert có signature dạng:
`focus-device-issue:Device serial 'device:<hash>' was not found in adb devices.`

## 1. Không Nhầm Lẫn Chuỗi Masked Serial
- Chuỗi `'device:<hash>'` (ví dụ `device:d8ee2315ef`) là do hàm `mask_value(serial, prefix='device')` của `python_runner` sinh ra để ẩn serial nhạy cảm khi log ra JSONL.
- Đây KHÔNG phải lỗi format hay gán sai prefix trong code. Không mất thời gian đi tìm chỗ nối chuỗi `"device:" + serial`.

## 2. Truy Vết Thời Gian Trong Log Để Xác Định Micro-Drop
- Mở file `log.jsonl` hoặc `summary.txt` của run gần nhất (thường nằm tại `D:\Taadaa\runtime\kibe\live\...`).
- Lọc các sự kiện có `action="feed-session-smoke"` hoặc `result="config-error"`:
  - Nếu nhiều máy (ví dụ 8-10 máy) fail ở **cùng một giây duy nhất** (ví dụ `07:08:47`), và thời gian từ `start_time` đến `end_time` chỉ vài trăm mili-giây (< 500ms):
  - **Khẳng định ngay:** Hiện tượng sụt áp / reset tạm thời của USB Hub kết hợp với việc preflight check retry quá nhanh (`time.sleep` = 0).

## 3. Rà Soát Tức Thì O(1) Hiện Trạng Toàn Fleet
- Chạy lệnh Python kiểm tra nhanh danh sách máy trong alert đối chiếu `machine-map-80.txt` với đầu ra của `adb devices`.
- Phân nhóm dứt khoát:
  - Máy đã tự động Online trở lại: Cho phép tiếp tục batch.
  - Máy vẫn Offline: Báo danh sách chính xác để thao tác vật lý (cắm lại cáp/hub).

## 4. Kỹ Thuật Vá (Patch Pattern)
- Trong hàm `_validate_child_adb`, giữa các lần `_attempt < ADB_ONLINE_ATTEMPTS`, bắt buộc có `time.sleep(1.0)` để tạo khoảng đệm cho bus USB re-enumerate sau các đợt micro-drop.
