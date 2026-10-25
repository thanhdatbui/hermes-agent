# Xiaowei Orphan ADB Triage (Port 5037 vs 5038), Proxy Preflight False Alarm & Wi-Fi Threshing Loop

## 1. Xiaowei Orphan ADB Path-Based Triage (Cạm Bẫy Cổng 5037 vs 5038)
- **Vấn đề cốt lõi:**
  Watchdog tự đóng Tiểu Vi (`xiaowei_idle_auto_close_watchdog.py`) trước đây chỉ truy vấn cổng `5038` qua `Get-NetTCPConnection -LocalPort 5038`.
  Tuy nhiên, khi Tiểu Vi khởi động hoặc gặp crash/tắt đột ngột, tiến trình con `C:\Program Files (x86)\xiaowei\tools\adb.exe` có thể bind nhầm hoặc chiếm giữ cổng **5037** (cổng ADB chính của Farm) với commandline:
  `adb -L tcp:localhost:5037 fork-server server`.
- **Hậu quả:**
  Watchdog thấy cổng 5038 trống nên bỏ qua, trong khi tiến trình `adb.exe` của Tiểu Vi kẹt mồ côi trên cổng 5037 ở trạng thái zombie/hang (không phản hồi TCP ACK). Toàn bộ công cụ điều phối (`inspect_machine.py`, runner nuôi acc, upload hook) trên Kibe Local bị tê liệt vì không kết nối được tới ADB server.
- **Quy tắc bất biến (Invariant):**
  Khi `xiaowei.exe` KHÔNG chạy, **BẤT KỲ tiến trình `adb.exe` nào có `ExecutablePath` nằm trong `*\xiaowei\*` đều là tiến trình mồ côi 100%** (vì Farm chuẩn luôn dùng `C:\Users\Kibe\.GemPhoneFarm\app\adb-tool\adb.exe`).
  Bắt buộc lọc theo cả Path và CommandLine:
  ```powershell
  Get-CimInstance Win32_Process -Filter "Name = 'adb.exe'" | Where-Object { ($ports -and $_.ProcessId -in $ports) -or $_.CommandLine -like "*-P 5038*" -or $_.ExecutablePath -like "*\xiaowei\*" }
  ```
  Nếu phát hiện `xiaowei.exe` đã tắt mà còn `adb.exe` của Tiểu Vi: lập tức phát lệnh `kill-server` và dập tắt bằng CIM/WMI.

---

## 2. Bẫy Đặt Tên "Rớt Mạng Proxy" Do Cơ Chế Fail-Closed VPN Preflight
- **Hiện tượng:**
  Operator hoặc Runner báo cáo: `[device-lock] machine X blocked by proxy VPN preflight` hoặc `final_status: blocked-proxy-vpn`, khiến người vận hành lầm tưởng cụm proxy MobiProxy hoặc MikroTik bị sập mạng.
- **Nguyên nhân gốc rễ (Root Cause):**
  Trong `automation-core/src/automation_core/preflight.py`, hàm `check_android_vpn()` thực hiện cơ chế an toàn **Fail-Closed Shield** (chống lộ IP FPT thật khi bật TikTok).
  Trước khi chạy, script bắn lệnh ADB `ip addr show wlan0`. Nếu thiết bị bị:
  1. Lỏng giắc cáp Micro-USB / tiếp xúc chập chờn (`device offline or adb not found`).
  2. ADB server trên host bị treo socket (như case PID 35860 ở mục 1).
  Lệnh ADB văng exception `device offline / connection lost`. Hàm preflight lập tức kích hoạt khóa bảo vệ an toàn và tự động gán nhãn:
  `final_status: blocked-proxy-vpn`.
- **Quy trình chẩn đoán O(1) chống đoán mò:**
  1. Kiểm tra file `summary.txt` của ca chạy: Đọc dòng `stop_reason:` thay vì chỉ nhìn `final_status:`. Nếu thấy `device is offline or ADB/USB disconnected`, thủ phạm là phần cứng/USB/ADB, KHÔNG PHẢI PROXY.
  2. Kiểm tra sức khỏe thật của cụm Proxy qua log của cron healer:
     Đọc `D:/Taadaa/AI-Tools/logs/mobiproxy_healer.log` hoặc `mobiproxy_stats.json`. Nếu thấy `All 32 MobiProxy ports are HEALTHY`, proxy hoàn toàn bình thường.

---

## 3. Cạm Bẫy Vòng Lặp Dập Nhả Wi-Fi (Wi-Fi Threshing Loop) Trên Samsung S7
- **Bản chất sự cố:**
  Các script auto-healer quét định kỳ 5 phút (`farm_wifi_auto_healer.py`) nếu thấy máy chưa có IP mà tự động chạy vòng lặp:
  `svc wifi disable` -> nghỉ 1s -> `svc wifi enable`.
- **Hậu quả phần cứng:**
  Trên dòng Samsung Galaxy S7 (chip Broadcom DHD PCIe), khi radio Wi-Fi bị dập nguồn liên tục mỗi 5 phút, chip chưa kịp hoàn tất bắt tay DHCP với AP Aruba thì đã bị dập tiếp. Sau vài chu kỳ, driver Wi-Fi rơi vào trạng thái ngủ sâu D3 (`state DORMANT / NO-CARRIER`) và AP Aruba kích hoạt từ chối kết nối (`ASSOCIATION_REJECTION`).
- **Quy tắc an toàn (Circuit Breaker):**
  Mọi script tự động phục hồi Wi-Fi BẮT BUỘC phải có Circuit Breaker: tối đa 2 lần heal trong 30 phút cho một thiết bị. Nếu thử 2 lần vẫn không có IP thì phải DỪNG NGAY, ghi log và chuyển sang cảnh báo thủ công, cấm dập nhả vô tận 24/7.

---

## 4. Xử Lý File Video 0-Byte Khiến Upload Hook Bị Bỏ Qua (`video_not_rendered`)
- **Triệu chứng:**
  Tài khoản bị ngưng đăng clip nhiều ngày, `upload_result.json` ghi:
  `"status": "skipped", "reason": "video_not_rendered", "expected_video": "...\\7.mp4"`.
  Nhưng khi kiểm tra folder `D:/TIKTOK-videonuoinick/<folder>/` thì thấy file `7.mp4` vẫn có tên trên đĩa.
- **Nguyên nhân:**
  File `7.mp4` có dung lượng chính xác **0 bytes** do sự cố crash render hoặc mất điện trước đó. Preflight của upload runner kiểm tra `os.path.getsize(path) > 0`, thấy 0 bytes nên skip an toàn.
- **Quy trình cứu hộ O(1):**
  1. Quét tìm và xóa toàn bộ file `.mp4` có dung lượng `0 bytes` trong folder mục tiêu.
  2. Kích hoạt render bù các file thiếu từ folder nguồn (`D:/video goc/<source>/`) bằng `batch_render.py`:
     `python D:/Taadaa/Tiktok-video/scripts/batch_render.py --input-dir "D:/video goc/<src>" --output-dir "D:/TIKTOK-videonuoinick/<dst>" --preset "D:/Taadaa/Tiktok-video/presets/preset_a_capcut_vignette.json" --run-id "render_remedy" --name-format "{stem}" --parallel 1`
  3. Tham số `--name-format "{stem}"` và không dùng `--overwrite` sẽ tự động SKIP toàn bộ các file đã có dung lượng hợp lệ và CHỈ render các file vừa bị xóa 0-byte.
