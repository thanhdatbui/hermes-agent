# Triage: Feed Session Failures, USB Transport Drop & Stuck Live Activity Recovery

## 1. Context & Incidents
Trong phiên nuôi TikTok Ca 3 Phiên 1 (Tối), hệ thống báo cáo:
- **Kibe (M1-M80)**: 71 Success, 9 Fail (M7, M10, M13, M30, M44, M50, M66, M71, M74).
  - Mất kết nối Wi-Fi (AP): M7
  - Mất kết nối ADB/USB: M10, M30, M50
  - Lỗi App TikTok/Script: M13, M44, M66, M71, M74
- **Admin (M201-M280)**: 62 Success, 17 Fail (văng app TikTok/script).

## 2. Root Cause & Triage Workflow

### A. Stuck LivePlayActivity / Hybrid SparkActivity ADB Block (M74, M71, M44)
- **Triệu chứng**:
  - `inspect_machine.py <N>` hoặc lệnh `adb shell` bị timeout (exit 124) hoặc treo vĩnh viễn không nhả stdout.
  - Device lock bị kẹt dạng pinned với tiến trình trước đó.
  - Máy vẫn phản hồi `adb get-state` trả về `device` nhưng các lệnh dumpsys/am/pm bị block.
- **Root Cause**:
  - TikTok đang chạy `com.ss.android.ugc.aweme.live.LivePlayActivity` (xem live stream) hoặc `com.bytedance.hybrid.spark.page.SparkActivity`.
  - Luồng video/live socket chiếm giữ input thread và surface rendering của Android, khiến `dumpsys window` hoặc adb bridge bị stall.
- **Quy trình cứu hộ chuẩn**:
  - Dùng công cụ phân tầng: `python D:/Taadaa/tools/recover_stuck_s7.py --machine <N>`.
  - Level 1: `am force-stop com.ss.android.ugc.trill` + kill background tasks.
  - Level 2: `pkill -f trill` + reset window manager.
  - Level 3: `adb reconnect` nếu bridge bị nghẽn transport.
  - Kết quả trên M74: Level 1 & 2 fail do socket nghẽn, Level 3 `reconnect` giải phóng thành công transport trong 2.1s, đưa máy về trạng thái `device` và hoạt động bình thường.

### B. USB Transport Drop / Hub Port Disconnect (M10, M30, M50)
- **Triệu chứng**:
  - `inspect_machine.py <N>` báo `adb.EXE: device '<serial>' not found`.
  - `recover_stuck_s7.py` báo `failed_transport` ngay từ bước preflight (`state: unknown`, latency ~0.06s).
  - Thử `adb reconnect` trả về `Device unresponsive after reconnect attempt`.
- **Phân loại**:
  - Đây là lỗi **Hardware / Physical Link Drop** ở cấp độ cổng USB trên Hub, cáp sạc lỏng hoặc controller USB bị ngắt cấp nguồn cổng.
  - CẤM TUYỆT ĐỐI agent thử vòng lặp reconnect liên tục trong phần mềm làm nghẽn host USB stack.
  - Báo cáo rõ danh sách serial và máy rớt link vật lý để Operator kiểm tra giắc cắm hoặc reset port hub.

### C. Wi-Fi Re-roam & Aruba 5GHz Association Rejection (M7)
- **Triệu chứng**:
  - Máy kết nối được vài giây nhận IP `192.168.110.124` rồi lập tức ngắt, `wlan0` chuyển sang `state DORMANT / NO-CARRIER`.
  - Dumpsys ghi nhận liên tục: `level2FailureCode=ASSOCIATION_REJECTION` (RSSI -72dBm) và `disableReason=NETWORK_SELECTION_DISABLED_AUTHENTICATION_FAILURE`.
- **Root Cause**:
  - Sóng AP Aruba `.253` (`kibe 1`) tại vị trí máy bị suy hao nặng (-72dBm).
  - Có SSID ngoài farm (`Dat`) phát sóng rất mạnh (đo được trong danh sách quét mạng MẠNG ĐANG CÓ).
  - Máy tồn tại profile rác mở không mật khẩu `kibe` (Net ID 1) xung đột với `kibe 1` (Net ID 0), gây dao động quét mạng liên tục.
- **Khắc phục**:
  - Purge profile rác: `service call wifi 14 i32 1`.
  - Force-stop adbjoinwifi vòng lặp: `am force-stop com.steinwurf.adbjoinwifi`.
  - Khởi động lại stack mạng sạch: `adb reboot`.
