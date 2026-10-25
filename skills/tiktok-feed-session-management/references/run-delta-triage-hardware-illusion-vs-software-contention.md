# Run Delta Triage: Hardware USB Illusion vs. Software Contention

## Core Diagnostic Principle
Khi phát hiện tình trạng **chênh lệch lớn giữa 2 phiên/ca liên tiếp** (Phiên 1 lỗi hàng loạt 30-40+ máy, Phiên 2 giảm lỗi mạnh hoặc chạy mượt >90% success) mà **người vận hành KHÔNG hề reboot máy hay chạm vào dây cáp**:

> **ĐỊNH LUẬT BẤT BIẾN:** Lỗi phần cứng vật lý (rớt cáp, cháy nguồn USB Hub) **KHÔNG BAO GIỜ TỰ KHỎI** giữa 2 ca chạy. Nếu phiên sau tự xanh mà không reboot, nguyên nhân 100% là **XUNG ĐỘT PHẦN MỀM (SOFTWARE CONTENTION / STALE LOCKS / ADB SATURATION)**. Tuyệt đối cấm kết luận ẩu là "hỏng hub/lỏng cáp".

---

## 3 Thủ Phạm Gây "Ảo Giác Rớt Mạng ADB"

1. **Tranh chấp JIT Device Lock (`skipped-device-locked`):**
   - Các batch job nền (2FA, đăng bài, dọn cache, follow session trước) chưa kịp nhả lock khi phiên feed mới bắt đầu.
   - Runner kiểm tra `device_locks/` thấy máy bị khóa nên tự động gắn cờ `skipped-device-locked` hoặc timeout handshake.
   - Khi hết hạn TTL của lock hoặc tiến trình cũ kết thúc, phiên tiếp theo lập tức bốc được máy và chạy thành công.

2. **Bão tiến trình & Nghẽn hàng đợi ADB Server (Port 5037 Queue Saturation):**
   - Khi có tác vụ dispatch hàng loạt (ví dụ: 25 worker SSH sang Admin, hoặc quét ADB song song), hàng trăm lệnh `uiautomator dump`, `screencap`, `dumpsys` dồn vào daemon `adb server`.
   - ADB server bị quá tải (queue saturation / socket drop), trả về lỗi `device offline` hoặc `connection reset by peer`, khiến watchdog phân loại nhầm thành "Mất kết nối ADB/USB".

3. **Cửa sổ Console chớp nháy làm treo tiến trình (Windows Console Spawning):**
   - Các tiến trình Python subprocess không có cờ `CREATE_NO_WINDOW = 0x08000000` tạo ra hàng chục `conhost.exe` trong thời gian ngắn, làm Desktop Window Manager (DWM) và hệ điều hành bị nghẽn I/O.

---

## Quy Trình Triage Chuẩn (3 Bước O(1))

1. **So sánh Manifest giữa 2 đợt chạy cùng ngày:**
   - Đọc `multi_machine_summary` và `event_counts` trong `run_manifest.json` của 2 thư mục `row-0-HHMMSS`:
   - Kiểm tra số lượng `skipped-device-locked` và loại lỗi cụ thể của từng máy.

2. **Đối soát mốc thời gian với các Cronjob khác:**
   - Kiểm tra xem tại thời điểm bắt đầu phiên lỗi có cronjob nào chạy song song không (dọn cache, backup, upload batch).

3. **Giải pháp khắc phục:**
   - **Tối ưu JIT Lock TTL:** Không để lock tồn tại quá thời gian chạy thực tế của job.
   - **Bọc `sitecustomize.py`:** Ép cờ ẩn console cho mọi tiến trình gọi ADB.
   - **Restart ADB Server khi có dấu hiệu bão:** `adb kill-server && adb start-server` để reset socket queue sau các đợt tải nặng.

---

## 4. Bẫy Ngộ Nhận & Checklist Xác Nhận Ca Tiếp Theo (Next-Shift Readiness)

### CẢNH BÁO: Bẫy "Đổ lỗi cho nguồn Hub USB" khi gặp dải máy liên tiếp
Khi thấy một dải máy liên tiếp báo mất kết nối ADB (ví dụ: M1-M14, M53-M66):
- **Phản xạ sai:** Vội vàng bảo User đi cắm lại nguồn Hub USB hoặc thay cáp.
- **Bản chất thực tế:** ADB handshake theo luồng tuần tự/bão song song trên cùng USB controller. Khi ADB daemon bị nghẽn queue socket hoặc các máy trong dãy bị giữ lock chùm từ ca trước, toàn bộ dải cổng trên hub đó sẽ handshake thất bại cùng lúc, tạo ra **ảo giác sụp nguồn hub vật lý**.
- **Quy tắc:** Nếu đợt chạy liền kề sau đó tự động xanh lại (>90% success) mà không reboot hay cắm lại dây, khẳng định 100% là nghẽn ADB server / lock queue, cấm báo lỗi phần cứng.

### Checklist 4 Điểm Đánh Giá Ca Tiếp Theo Đã Sạch Lỗi Chưa
Khi User hỏi "Ca tiếp theo đã hết lỗi chưa?", Coordinator BẮT BUỘC kiểm tra đủ 4 điểm thực tế trước khi kết luận:
1. **Device Lock (`device_locks/`):** Thư mục lock sạch 100%, không còn file lock mồ côi (hoặc lock cũ đã vượt quá TTL).
2. **Số máy Online thực tế:** Chạy `adb devices` xác nhận đủ số lượng máy fleet đang `device` (không dính `offline` hay `unauthorized`).
3. **Trạng thái kết thúc của ca trước:** Ca trước đã tạo đủ `run_manifest.json`, không còn worker bị treo dở dang.
4. **Tiêu diệt bão tiến trình (Console / SSH):** Đảm bảo `sitecustomize.py` đã tiêm `CREATE_NO_WINDOW = 0x08000000` trên cả Kibe và Admin để không tái diễn bão `conhost.exe` làm nghẽn ADB socket.
