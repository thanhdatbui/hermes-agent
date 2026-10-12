# Xiaowei ADB Reset & Offline Device Triage Protocol (2026-10-12)

## 1. Hiện tượng & Bối cảnh
- Khi operator/user phát hiện thiết bị ADB xuất hiện `offline` hoặc nghi ngờ XiaoWei (Tiểu Vi - con gấu) làm loạn danh sách ADB (`adb devices` báo tùm lum / văng device).
- XiaoWei (`xiaowei.exe`) tự khởi chạy daemon ADB / scrcpy nội bộ và hook vào bus USB để stream màn hình hàng loạt máy Android.
- Khi XiaoWei được bật/tắt (hoặc watchdog `xiaowei_idle_auto_close_watchdog.py` đóng tiến trình), các socket transport USB bị ngắt đột ngột, có thể khiến 1–2 máy rơi vào trạng thái `offline` tạm thời.

## 2. Quy trình điều tra O(1) chuẩn — Không can thiệp mò mẫm

### Bước 1: Kiểm tra trạng thái tiến trình XiaoWei & ADB PC
Kiểm tra nhanh xem XiaoWei có thực sự đang chạy hay đã tắt:
```cmd
tasklist /FI "IMAGENAME eq xiaowei*"
tasklist /FI "IMAGENAME eq adb*"
```
- Nếu `xiaowei.exe` không còn chạy: XiaoWei đã được đóng sạch sẽ, không có xung đột active.

### Bước 2: Truy vết Serial bị `offline` về Số Máy (Machine Index) O(1)
**CẤM TUYỆT ĐỐI** chạy `adb shell` trần vào máy offline (sẽ bị Guard chặn vì thiếu Device Lock) hoặc quét đĩa diện rộng để tìm serial.
Tra cứu trực tiếp số máy từ file SoT Excel:
```python
import openpyxl

wb = openpyxl.load_workbook(r"D:/OneDrive/TaadaaData/kibe/PROXYgandienthoai.xlsx", read_only=True)
ws = wb.active
for r in range(1, 85):
    if "<TARGET_SERIAL>" in str(ws.cell(r, 2).value):
        print(f"Row {r}: Máy {ws.cell(r, 1).value} -> {ws.cell(r, 2).value}")
        break
```

### Bước 3: Đọc hiện trường máy an toàn qua công cụ chuẩn
Dùng đúng script chuẩn của farm để kiểm tra máy mà không vi phạm Device Lock:
```cmd
python D:/Taadaa/tools/inspect_machine.py <N>
```
Kết quả sẽ chỉ rõ:
- Máy có phản hồi hay bị kẹt transport (`adb.EXE: device offline`).
- Tình trạng sạc / pin / màn hình.

### Bước 4: Nguyên tắc phục hồi (Anti-Panic)
- Không kill ADB server thủ công khi farm đang chạy ca nuôi (sẽ làm đứt session của 70+ máy khác).
- Để watchdog chuyên trách `farm-adb-transport-healer` (chạy định kỳ 3 phút/lần) tự động giải phóng socket transport và reconnect máy bị kẹt.
- Báo cáo rõ ràng: số máy đang online (`device`), số máy `offline` (kèm số máy cụ thể), và xác nhận trạng thái tiến trình XiaoWei.
