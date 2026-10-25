# Xiaowei Orphan ADB Port 5037 Hijack, Runner Preflight Misnomer & Wi-Fi Healer Circuit Breaker

## 1. Bẫy Chiếm Cổng 5037 Của ADB Tiểu Vi (Xiaowei Orphan ADB Port 5037 Trap)
- **Hiện tượng:** Toàn bộ công cụ ADB cục bộ (`inspect_machine.py`, `adb devices`, runner) bị đứng hình hoặc timeout 100% dù điện thoại vẫn cắm đủ cáp USB và máy Admin vẫn kết nối bình thường.
- **Nguyên nhân gốc:** 
  - Phần mềm Tiểu Vi (`xiaowei.exe`) sở hữu file nhị phân ADB riêng tại `C:\Program Files (x86)\xiaowei\tools\adb.exe`.
  - Trong một số phiên khởi chạy, Tiểu Vi spawn tiến trình daemon ở cổng **5037** (`adb -L tcp:localhost:5037 fork-server server`) thay vì cổng phụ 5038.
  - Sau khi tắt giao diện Tiểu Vi, tiến trình `adb.exe` này bị bỏ rơi thành mồ côi (orphan/zombie), giữ socket 5037 ở trạng thái không phản hồi TCP ACK.
  - Watchdog cũ `xiaowei_idle_auto_close_watchdog.py` chỉ quét tìm tiến trình gắn với cổng 5038 (`XIAOWEI_ADB_PORT = 5038`), dẫn đến việc hoàn toàn bỏ sót con ADB zombie trên cổng 5037.
- **Quy chuẩn khắc phục:**
  - Bộ lọc tiến trình `XIAOWEI_ADB_TARGET_PS` bắt buộc nhận diện theo đường dẫn thực thi:
    `$_.CommandLine -like "*-P 5038*" -or $_.ExecutablePath -like "*\xiaowei\*"`
  - Khi `xiaowei.exe` đã tắt, bất kỳ tiến trình ADB nào có nguồn gốc từ thư mục Tiểu Vi (`*\xiaowei\*`) đều phải bị dập tắt triệt để bằng `kill-server` và CIM/WMI terminate để trả lại cổng 5037 cho ADB chuẩn của Farm (`C:\Users\Kibe\.GemPhoneFarm\app\adb-tool\adb.exe`).

## 2. Bẫy Đặt Tên Báo Cáo "Mất Wi-Fi / Proxy" Của Runner (`blocked-proxy-vpn` Misnomer)
- **Hiện tượng:** Báo cáo đối soát hoặc feed session watchdog cảnh báo hàng loạt máy bị `blocked-proxy-vpn` hoặc `Mất Wi-Fi/Proxy`, khiến người vận hành lầm tưởng cụm proxy MobiProxy hoặc MikroTik bị sập.
- **Bản chất hiện trường:**
  - Hàm `check_android_vpn()` trong `automation-core/src/automation_core/preflight.py` là cơ chế an toàn **Fail-Closed Shield**: trước khi bật TikTok, nó dùng lệnh ADB (`ip -4 addr show wlan0`) để kiểm tra IP Wi-Fi và Proxy nhằm chống lộ IP nhà mạng FPT.
  - Khi điện thoại bị lỏng cáp Micro-USB, rớt kết nối ADB hoặc ADB Daemon bị kẹt cổng 5037, lệnh ADB ném ngoại lệ: `device is offline or ADB/USB disconnected for <serial>: adb.exe: device not found`.
  - Hàm preflight bắt ngoại lệ này, trả về `connected=False`, và runner tự động gán nhãn cho toàn bộ lượt chạy là `final_status: blocked-proxy-vpn` kèm `message: [device-lock] machine X blocked by proxy VPN preflight`.
- **Kỷ luật chẩn đoán O(1):**
  - Không vội vàng kết luận mạng Proxy bị sập khi thấy nhãn `blocked-proxy-vpn`.
  - Bắt buộc kiểm tra trường `stop_reason` trong `summary.txt`: nếu chứa `device offline or ADB/USB disconnected`, nguyên nhân thực sự là **hạ tầng cáp USB hoặc ADB daemon**, hoàn toàn không liên quan đến cụm Proxy.
  - Đối soát liveness của cụm MobiProxy qua `D:/Taadaa/AI-Tools/logs/mobiproxy_healer.log` (`All 32 MobiProxy ports are HEALTHY`).

## 3. Tử Huyệt Vòng Lặp Dập Nguồn Wi-Fi & Giải Pháp Circuit Breaker
- **Vấn đề của Auto-Healer không ngắt mạch:**
  - Khi một thiết bị S7 gặp sự cố Wi-Fi thực sự (AP Aruba từ chối bắt tay `ASSOCIATION_REJECTION`, anten lỏng, hoặc mất profile), script `farm_wifi_auto_healer.py` chạy định kỳ 5 phút/lần sẽ liên tục thực thi:
    `svc wifi disable` -> nghỉ 1s -> `svc wifi enable` -> force-join SSID.
  - Việc dập nguồn radio liên tục 288 lần/ngày khiến chip Wi-Fi Broadcom DHD PCIe trên S7 rơi vào trạng thái ngủ sâu (`state DORMANT / NO-CARRIER`), làm tê liệt card mạng vĩnh viễn và buộc phải reboot máy.
- **Chuẩn hóa Circuit Breaker (Ngắt mạch & Cooldown):**
  - Giới hạn dập nhả: Một máy chỉ được phép thử tối đa `MAX_FAILURES = 2` lần liên tiếp.
  - Nếu sau 2 lần dập nhả mà máy vẫn không nhận IP `192.168.110.X`, kích hoạt **Cooldown cách ly 30 phút (`COOLDOWN_SEC = 1800`)**: các chu kỳ cron 5 phút tiếp theo bắt buộc bỏ qua máy này, tạo không gian tĩnh cho stack mạng tự phục hồi.
  - Tự động reset bộ đếm lỗi về 0 ngay khi máy nhận lại IP thành công.

## 4. Phân Định Ranh Giới Đĩa Đệm Video (Kibe Local vs Admin Remote GDrive)
- **Kibe Local (`D:\TIKTOK-videonuoinick\`):** 
  - Ổ D: Kibe dung lượng lớn (3.7 TB, thường dư > 800 GB), lưu trữ trực tiếp các folder video đã render để nạp cho dàn máy 1-80 qua USB.
  - TUYỆT ĐỐI KHÔNG xóa hay dọn video đã render lên Google Drive khi máy chưa đăng xong.
- **Admin Remote (`ADMIN-PC` - `D:\TIKTOK-videonuoinick-admin`):**
  - Ổ SSD nhỏ (1 TB, thường chỉ còn 15-30 GB free), dùng Task Scheduler `Taadaa_Sync_GDrive_Backup` chạy ngầm script `sync_and_clean_gdrive.py` mỗi 2 giờ: khi folder render đủ $\ge 30$ clip, robocopy video gốc từ `D:\video goc may 2` lên ổ `G:\My Drive\video_goc_backup` rồi mới xóa video gốc local để giải phóng đĩa.
