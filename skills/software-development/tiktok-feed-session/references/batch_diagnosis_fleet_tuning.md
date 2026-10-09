# Hướng Dẫn Chẩn Đoán Lỗi Batch Multi-Machine & Điều Phối Fleet (Tuning & Root Cause)

## 1. Vị Trí Lưu Log Multi-Machine Chuẩn Xác O(1)
Khi batch nuôi feed kết thúc hoặc gửi cảnh báo Farm Alert, **CẤM TUYỆT ĐỐI** dùng `find`, `os.walk` quét diện rộng hay tìm trong `.ai-runs/`.
Thư mục gốc lưu trữ log batch là:
```
D:/Taadaa/runtime/<cluster>/live/<YYYY-MM-DD>/row-<Row>-<HHMMSS>/<timestamp>/
```
Trong đó `<cluster>` là `kibe` (máy 1-80) hoặc `admin` (máy 201-280).

Các file cần đọc ngay:
1. **`summary.txt`**: Tóm tắt tổng quan số lượng máy success, manual-needed, failed, tổng số lượt swipe.
2. **`run_manifest.json`**: Cực kỳ quan trọng, chứa mảng chi tiết trạng thái từng máy:
   - `machine`: số máy (1..80 hoặc 201..280).
   - `final_status`: `success`, `manual-needed`, `fail`, `config-error`.
   - `stop_reason`: lý do dừng chi tiết (ví dụ: `network/error/retry marker detected`, `startup ad/splash marker detected`, `known TikTok screen`).
   - `blocker_type`: phân loại blocker (`detector-miss`, `script-blocker`, v.v.).
3. **Log chi tiết từng máy lẻ**:
   - `machines/machine_<N>/<timestamp>/summary.txt`
   - `machines/machine_<N>/<timestamp>/log.jsonl`

---

## 2. Bản Đồ Lỗi & Cách Xử Lý Chuẩn Xác (Không Đoán Mò)

### A. Lỗi `detector-miss:network/error/retry marker detected`
- **Hiện tượng**: Màn hình TikTok xuất hiện chữ *"Thử lại"*, *"Không có kết nối Internet"*, *"Lỗi mạng"*.
- **Nguyên nhân**: Spike độ trễ proxy 4G/Mikrotik khi có quá nhiều worker cùng lúc bắn request nạp video.
- **Tuning Fleet chuẩn**:
  - Không chạy quá 30 worker song song: `max_workers = 30` (trước đây là 40).
  - Tăng độ trễ khởi động máy (stagger): `stagger = (4000, 10000)` (4-10 giây giữa các máy) trong `multi_machine_feed_session.py` và `run_tiktok.py`.
- **Cơ chế script**: Tự động tap nút *"Thử lại"* hoặc force-stop recovery và chờ nạp lại video.

### B. Cảnh Báo "ViChanger" Là Nhãn Legacy — Farm ĐÃ DẸP VICHANGER
- **Lưu ý tối quan trọng**: Hệ thống Farm hiện tại chạy **Global HTTP Proxy** (`192.168.110.2:200xx`). Đã dẹp bỏ hoàn toàn app ViChanger.
- Khi thấy log ghi nhãn `blocked-proxy-vpn`: Đây chỉ là tên category lịch sử của `vpn_preflight.py` khi máy bị offline ADB hoặc không ping được proxy/DNS.
- **CẤM TUYỆT ĐỐI**: Không bao giờ được báo user "restart ViChanger" hay tìm cách bật ViChanger.

### C. Phân Biệt App Crash (Văng) vs Kẹt UI Bridge / Delay Launch (Vụ Máy 19)
- Khi `verify_tiktok_focus` báo fail vì `focused package is com.sec.android.app.launcher`:
  - **CẤM** vội vàng kết luận bản app bị văng/crash.
  - Kiểm tra crash log thật bằng `adb -s <serial> logcat -d -t 500` tìm `FATAL EXCEPTION` hoặc `am_crash`.
  - Trên thiết bị Samsung Galaxy S7 (Android 8), tiến trình `uiautomator stub` cũ hoặc service ngầm có thể gây kẹt IO / pause timeout, làm app lên foreground trễ.
  - **Khắc phục chuẩn**:
    - Trong `_verify_tiktok_focus_with_retries`: Bổ sung re-launch lệnh `monkey` tại attempt 3 và 6 nếu package vẫn chưa phải là TikTok.
    - Dọn dẹp tiến trình `pkill -f uiautomator` khi cần thiết.

---

## 3. Kỷ Luật Phân Tích Của Coordinator Khi Gặp Farm Alert
1. **Không tuyên bố "không có lỗi / không cần sửa" khi chỉ kiểm tra thấy proxy hiện tại đang live**: Lỗi xảy ra trong quá khứ lúc batch chạy, phải mở đúng `run_manifest.json` xem máy nào fail cả 2 phiên liên tiếp.
2. **Lọc ra danh sách máy fail cả 2 phiên**: Đó là các máy có vấn đề thực sự (rớt USB, kẹt app, cấu hình sai) cần can thiệp xử lý ngay.
3. **Máy `device not found`**: Báo rõ user kiểm tra cáp/cổng USB vật lý, không nhầm lẫn với lỗi script.
