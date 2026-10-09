# Triage Cụm Lỗi ADB Offline, Masked Serial & USB Hub Micro-Drop Khi Chạy Batch Nuôi Acc

## 1. Bản Chất Chuỗi `device:<hash>` Trong Farm Alert
- Khi nhận Farm Alert có signature:
  `focus-device-issue:Device serial 'device:<hash>' was not found in adb devices.`
- **Bản chất kỹ thuật:** Chuỗi `'device:<hash>'` (ví dụ `device:d8ee2315ef`) là do hàm `mask_value(serial, prefix='device')` tại dòng 1762 file `python_runner/flows/multi_machine_feed_session.py` sinh ra khi ghi log và export manifest:
  ```python
  last_error = f"Device serial {mask_value(serial, prefix='device')!r} was not found in adb devices."
  ```
- **Lưu ý quan trọng:** Đây KHÔNG PHẢI lỗi nối chuỗi prefix sai trong code runner hay Excel mapping. Không mất thời gian đi tìm chỗ nối chuỗi `"device:" + serial`.

## 2. Truy Vết Thời Gian Trong Log Để Nhận Diện Micro-Drop USB Hub
- Mở file `log.jsonl` hoặc `summary.txt` của run gần nhất (tại `D:\Taadaa\runtime\kibe\live\...\<timestamp>\`).
- Kiểm tra các dòng có `result="config-error"`:
  - Nếu xuất hiện hiện tượng nhiều máy (ví dụ 8-12 máy) fail tại **cùng một giây duy nhất** (ví dụ `07:08:47`), và thời gian thực thi của từng máy từ `start_time` đến `end_time` chỉ vỏn vẹn **100ms - 200ms**:
  - **Khẳng định 100% nguyên nhân:** Hiện tượng sụt áp / controller reset tức thời của USB Hub khi kích hoạt hàng loạt workers song song dồn dập (40 workers), kết hợp với việc kiểm tra preflight ADB không có độ trễ nghỉ (`time.sleep` = 0).

## 3. Rà Soát Tức Thì O(1) Hiện Trạng Toàn Fleet
- Dùng lệnh Python kiểm tra nhanh danh sách máy trong alert đối chiếu `machine-map-80.txt` với đầu ra của `adb devices`.
- Phân nhóm rõ ràng:
  - **Nhóm tự phục hồi (ONLINE lại):** Do sụt áp tạm thời, sau vài giây USB bus đã nhận lại thiết bị. Nhóm này hoàn toàn an toàn để tiếp tục chạy batch hoặc canary test.
  - **Nhóm mất kết nối thực sự (OFFLINE):** Không có trong danh sách `adb devices`. Cần báo rõ số máy cụ thể để kỹ thuật viên cắm lại cáp USB / cấp lại nguồn hub.

## 4. Kỹ Thuật Vá Code Chuẩn (Patch Pattern)
- Trong `python_runner/flows/multi_machine_feed_session.py` hàm `_validate_child_adb`:
  Bổ sung khoảng trễ `time.sleep(1.0)` giữa các lần thử trong vòng lặp retry (`_attempt < ADB_ONLINE_ATTEMPTS`) để cho phép bus USB có thời gian hoàn tất quá trình handshake/re-enumerate khi gặp micro-drop.
