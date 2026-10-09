# ADB Transport Freeze & Cron Alert Denominator Shrinkage

## 1. ADB Transport Freeze (adbd Socket Hang)

### Hiện tượng:
- Lệnh `adb get-state` trả về `device` (exit 0) bình thường, làm cho các pre-flight check cơ bản ngỡ rằng máy đang online tốt.
- Tuy nhiên, mọi lệnh thực thi tiếp theo qua `adb shell ...` (hoặc `dumpsys`, `screencap`, `input tap`) bị treo đứng vô thời hạn và chỉ thoát khi đụng timeout của runner (ví dụ 240s).
- Gây nghẽn toàn bộ luồng worker hoặc làm cả batch cron bị kéo dài hàng chục phút.

### Cơ chế xử lý chuẩn:
1. **Fast ADB Ping**: Trước khi thực thi tác vụ nặng hoặc trong vòng lặp kết nối, luôn probe nhanh bằng lệnh nhẹ với timeout ngắn:
   ```bash
   adb -s <serial> shell echo 1  # timeout=5s
   ```
2. **Auto-Recovery tức thì (`adb reconnect`)**:
   - Khi fast ping timeout hoặc exit non-zero do transport socket bị treo:
     ```bash
     adb -s <serial> reconnect
     ```
   - Lệnh này reset lại kênh giao tiếp transport ở phía ADB server mà KHÔNG cần reboot máy, KHÔNG làm văng app đang chạy và KHÔNG mất state của người dùng.
   - Ngay sau `adb reconnect`, kiểm tra lại ping trước khi cho script chạy tiếp.

---

## 2. Lỗi Suy Thoái Mẫu Số Cảnh Báo (Cron Alert Denominator Shrinkage)

### Nguyên nhân gây spam cảnh báo ("Clg báo lắm thế"):
- Trong các batch runner có lưu lũy kế (ví dụ dọn cache, quét avatar, đồng bộ trạng thái):
  - 78/80 máy đã chạy thành công ở lượt đầu và được ghi vào state file.
  - Lượt cron tiếp theo lọc ra các máy chưa xong, khiến `target_machines` chỉ còn lại 2 máy bị sót/lỗi mạng.
  - Khi 2 máy này tiếp tục lỗi, nếu script dùng công thức:
    ```python
    # SAI LẦM: Mẫu số bị co cụm về kích thước mẻ retry
    if total_attempted > 0 and f_count > (total_attempted / 2):
        send_farm_alert("Đa số máy thất bại...")
    ```
    → `f_count = 2`, `total_attempted = 2` → 2 > 1 → Script ngộ nhận là toàn farm thất bại và bắn alert P0/pipeline alert liên tục mỗi tick (15 phút/lần).

### Quy tắc Invariant cho Script Cron Watchdog:
1. **Tính tỷ lệ trên tổng quy mô Farm**:
   - Mẫu số bắt buộc phải là tổng số máy farm (`total_farm_machines` hoặc `len(machines)`), KHÔNG lấy `len(target_machines)` của lượt retry.
   - Chỉ được kích hoạt cảnh báo "Đa số thất bại" khi `f_count > total_farm_machines * 0.2` (hoặc ngưỡng cố định tối thiểu, ví dụ `f_count >= 5`).
2. **Kỷ luật chống spam lặp lại (Alert Throttling)**:
   - Nếu danh sách máy fail không đổi so với lượt chạy trước, KHÔNG được bắn lại alert cùng nội dung lên Telegram.
   - Khi tỷ lệ thành công toàn farm đã đạt >90% (ví dụ 78/80), các máy sót chỉ được log WARN vào file report runtime, tuyệt đối cấm bắn alert "Đa số máy thất bại" làm phiền người vận hành.
