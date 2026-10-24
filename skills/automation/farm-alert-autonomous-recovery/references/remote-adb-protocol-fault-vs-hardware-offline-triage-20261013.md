# Remote ADB Protocol Fault vs Hardware Offline Triage Protocol (2026-10-13)

## 1. Hiện tượng & Bối cảnh
- Watchdog `tiktok-feed-session-watchdog` hoặc alert bot báo cáo lỗi hàng loạt (ví dụ: 69/80 máy báo "Mất kết nối ADB/USB" trên cụm Admin Remote 201-280).
- Dễ gây hoang mang lầm tưởng toàn bộ cụm máy bị rớt mạng, sập switch hoặc rớt cáp USB vật lý.

## 2. Quy trình điều tra O(1) chuẩn

### Bước 1: Kiểm tra `summary.txt` của 1 máy đại diện
Đọc file `summary.txt` trong run artifact tương ứng:
```text
D:\Taadaa\runtime\admin\live\<DATE>\<SESSION>\machines\machine_201\<RUN_ID>\summary.txt
```
Phân loại nguyên nhân:
- **Transient Protocol Fault**: `stop_reason` chứa `protocol fault (couldn't read status): connection reset` hoặc `cannot connect to daemon`. Xảy ra khi daemon ADB từ xa (192.168.110.119:5037) bị nghẽn socket hoặc vừa khởi động lại sau mốc reboot, dẫn đến connection reset hàng loạt do concurrency spike từ runner.
- **True Hardware Offline**: `stop_reason` báo `device '<serial>' not found` hoặc `device offline` liên tục trên từng serial cụ thể.

### Bước 2: Kiểm tra liveness trực tiếp qua `inspect_machine.py`
Chạy lệnh kiểm tra O(1) không tham số hoặc theo số máy:
```cmd
python D:/Taadaa/tools/inspect_machine.py
python D:/Taadaa/tools/inspect_machine.py <N>
```
Nếu danh sách ADB Remote vẫn trả về đầy đủ `device` (75+ máy online), kết nối mạng LAN và ADB server vẫn hoàn toàn bình thường.

### Bước 3: Đối soát trạng thái phiên kế tiếp (Session Concurrency)
Kiểm tra thư mục phiên tiếp theo trong `runtime/<cluster>/live/<DATE>`:
- Nếu phiên tiếp theo đang chạy và các máy hoàn tất với `final_status: success`, sự cố ở phiên trước chỉ là Transient Glitch cục bộ đã tự phục hồi.
- Không can thiệp thô bạo (không kill ADB daemon, không gõ `adb reconnect`).

## 3. Quy tắc an toàn & Xử lý phần cứng
- Đối với máy rớt USB thật sự (như M10, M30, M35 do kẹt thanh ghi Intel X99): **CẤM** chạy soft reconnect làm bung cửa sổ đen phá game TFT.
- Đợi mốc Preflight Auto-Reboot định kỳ gần nhất để System Bus Reset từ BIOS tự động kéo máy lên xanh.

## 4. Cơ chế Warmup Buffer chống Connection Reset (Root Cause Fix)
- **Cơ chế gây lỗi:**
  - Mốc reboot farm quá sát giờ ca (ví dụ 11:35 reboot -> 12:00 chạy ca, chỉ có 25 phút đệm).
  - Chipset USB Intel X99 điều khiển 80 máy: sau reboot, Windows, WireGuard, XiaoWei và ADB server cần 15–20 phút để hoàn tất USB descriptor enumeration.
  - Khi runner spawn 25–40 threads đồng thời vào port 5037 từ xa, daemon ADB chưa ổn định sẽ bị sập socket (`protocol fault: connection reset`).
- **Quy chuẩn Warmup Buffer:**
  - Lùi lịch Auto-Reboot sớm hơn tối thiểu **40 phút** trước giờ ca (chuyển sang **05:20 | 11:20 | 17:20** thay vì 05:45 | 11:35 | 17:45).
  - Khoảng đệm 40 phút đảm bảo:
    1. Cả 2 host thông mạng LAN / WireGuard ổn định.
    2. XiaoWei nhận diện đủ 100% cổng USB và giải phóng bus.
    3. Daemon ADB server nguội máy, sẵn sàng nhận tải concurrency cao mà không bị reset socket.
