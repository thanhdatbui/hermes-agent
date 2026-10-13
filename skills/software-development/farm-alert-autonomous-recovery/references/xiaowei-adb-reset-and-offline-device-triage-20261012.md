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
- Không kill ADB server thủ công khi farm đang chạy ca nuôi (sẽ làm đứt session của các máy khác).
- **CẤM gõ `adb reconnect` trần:** Hard Gate #5 sẽ chặn vì thiếu `-s <serial>` và thiếu Device Lock.
- **Khai tử soft-reconnect / transport-healer:** Cronjob `farm-adb-transport-healer` và `safe_usb_guard.py` đã bị xóa sổ vì lệnh mềm không thể giải phóng thanh ghi phần cứng Intel X99 (lỗi `HRESULT 0x8004100c`) và làm bung cửa sổ đen phá game TFT.
- **Cơ chế phục hồi chuẩn tự động (User Invariant):** Áp dụng **Preflight Auto-Reboot 3 Ca trước mỗi ca chạy** (3 mốc chuẩn: **05:20, 11:20, 17:20**, đệm 40 phút trước các Ca 06:00, 12:00, 18:00) qua Task `Taadaa_Farm_Daily_Reboot_1135` (`farm_preflight_daily_reset.py`). Mốc đệm 40 phút là bắt buộc để tránh socket storm `connection reset` (khi 25+ worker kết nối cùng lúc lúc daemon ADB/WireGuard vừa khởi động lại). Script có TFT Game Guard chỉ hủy reboot khi đang trong trận đấu 3D `League of Legends.exe`. Sau reboot (~60s), System Bus Reset từ BIOS sẽ giải phóng hoàn toàn thanh ghi EHCI USB và kéo 100% thiết bị lên xanh sạch sẽ trước ca chạy.
- Báo cáo rõ ràng: số máy đang online (`device`), số máy `offline` (kèm số máy cụ thể), và xác nhận trạng thái tiến trình XiaoWei.
