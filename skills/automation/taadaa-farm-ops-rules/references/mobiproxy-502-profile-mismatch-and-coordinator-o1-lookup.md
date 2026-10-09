# MobiProxy 502 Bad Gateway, False-Positive UI Mismatch & Coordinator O(1) Process Inspection (08/09/2026)

## 1. Sự cố thực tế & Bài học Kỷ luật Coordinator (08/09/2026)

- **Hiện tượng:** Batch nuôi acc Ca 3 Row 6 (ngày chẵn 08/09) báo lỗi lan rộng:
  `❌ Signature: script-blocker:profile username still mismatched after switch` trên 39/68 máy (57.4%).
- **Anti-Pattern Coordinator (CỰC KỲ NGUY HIỂM):**
  - Coordinator trong session chính gõ lệnh `find "D:/Taadaa/tiktok-luot nuoi acc/.ai-runs" -name "run_manifest.json"` trên hệ thống tệp Windows.
  - Lệnh quét đĩa bị nghẽn I/O và treo timeout 900 giây (15 phút), làm đóng băng toàn bộ tiến trình điều phối, khiến User bức xúc phản ánh.
- **Kỷ luật O(1) Tra cứu Hiện trường Batch đang chạy:**
  - Tuyệt đối CẤM `find`, `grep -r`, `search_files` quét đĩa sâu tìm file log.
  - Tra cứu O(1) qua tiến trình hệ thống bằng PowerShell (thời gian phản hồi < 0.3s):
    ```powershell
    Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*run-feed-session*' -or $_.CommandLine -like '*run_tiktok*' } | Select-Object ProcessId, CommandLine
    ```
  - Lệnh trên bóc tách ngay lập tức đường dẫn `--artifact-root` chính xác của batch đang chạy (ví dụ: `D:\Taadaa\runtime\kibe\live\2026-09-08\row-6-203020`), từ đó mở thẳng file `summary.txt` hoặc `log.jsonl` mà không quét bất kỳ thư mục nào.

---

## 2. Cạm bẫy False-Positive: Mismatch Username thực chất là Chết Proxy (502 Bad Gateway)

- **Triệu chứng lừa mắt:**
  - Runner báo lỗi `profile username still mismatched after switch`.
  - Màn hình điện thoại hiện các bước nhập liệu/đăng nhập do cơ chế Auto-Login Reconcile (`reconcile_tiktok_accounts.py`) tự động kích hoạt để cứu nick. Dễ bị ngộ nhận là cron reg chạy đè vào cron nuôi hoặc tài khoản bị die/văng session.
- **Ground Truth từ hiện trường:**
  1. Tài khoản Row 6 (`@ahmetsguthe17`) đã hiện diện sẵn trong danh sách Account Switcher tại bounds `[0,1248][1080,1464]`.
  2. Runner đã tap trúng tâm container `Button` (`540, 1356`).
  3. Tuy nhiên, cổng proxy upstream (MobiProxy 4G qua Sing-box `192.168.110.2:20001`) trả về lỗi **`HTTP/1.1 502 Bad Gateway`**.
  4. Thanh trạng thái thiết bị ghi nhận: `Tín hiệu Wi-Fi ba vạch.,Không có Internet.`.
  5. **Cơ chế lỗi của TikTok:** Khi không có kết nối Internet, thao tác tap đổi tài khoản trong switcher bị TikTok âm thầm bỏ qua (không nạp được profile session mới từ server). App giữ nguyên tài khoản cũ (`Giang Han` - Row 4). Khi runner kiểm tra lại profile, username không đổi $\rightarrow$ ném lỗi mismatch username.

---

## 3. Cạm bẫy Dashboard Web MobiProxy: "29 Active" nhưng Cổng Đã Ngắt / Socket Treo

- **Hiện tượng Dashboard:**
  - Web quản trị MobiProxy có thể báo 29/32 proxy "Đang hoạt động", nhưng kiểm tra chi tiết:
    + `proxy01` (Lan1 - port 5101 cấp cho Máy 1): Báo đỏ **`Đã ngắt — Chưa có IPv4`**.
    + Các proxy khác báo uptime chỉ "7 phút" $\rightarrow$ vừa bị mất kết nối / redial hàng loạt.
  - Ngoài ra, có tình trạng API web báo `status: true` nhưng socket TCP trên server proxy bị kẹt/refused (`connect_ex=10035`), khiến Singbox proxy trả về `502 Bad Gateway`.
- **Quy trình Chẩn đoán & Khắc phục chuẩn:**
  1. **Kiểm tra Egress thực tế từ thiết bị (hoặc host):**
     ```bash
     curl -v -m 5 -x http://192.168.110.2:20001 http://api.ipify.org
     ```
     Nếu trả về `502 Bad Gateway` hoặc timeout $\rightarrow$ xác định 100% nguyên nhân do hạ tầng proxy, không phải do code automation hay tài khoản TikTok.
  2. **Thao tác phục hồi:**
     - Bấm nút **`Reset tất cả`** hoặc **`Reset bỏ proxy đầu`** trên web MobiProxy để modem 4G redial nhận lại IPv4.
     - Hoặc chạy script watchdog tự phục hồi:
       ```bash
       python D:/Taadaa/AI-Tools/scripts/mobiproxy_auto_healer.py --check-and-heal
       ```
     - Chờ modem redial hoàn tất (khoảng 15-30s), kiểm tra lại `curl` qua Sing-box đạt HTTP 200 trước khi kích hoạt Canary hoặc resume batch.

---

## 4. Cạm bẫy Auto-Healer Spam Gây Sập Toàn Bộ Box (Spam Recreate Storm & ERR_CONNECTION_REFUSED)

- **Thắc mắc thường gặp:**
  - *"API reset IP mỗi cổng là một API riêng (`/proxy_recreat?proxy=host:port`), tại sao lại làm sập/mất kết nối tất cả các cổng?"*
- **Nguyên nhân cốt lõi (3 tầng gây nghẽn phần cứng):**
  1. **Thiếu Single-Instance Lock (Tích tụ tiến trình chồng chéo):**
     - Cronjob chạy mỗi 1 phút (`*/1 * * * *`). Nếu một lượt quét phát hiện nhiều cổng die và mất > 1 phút (thời gian probe timeout + recreate + chờ redial), các tick cron tiếp theo sẽ tiếp tục sinh tiến trình mới chạy song song.
     - Thực tế ghi nhận: Có tới 4 tiến trình Python `mobiproxy_auto_healer.py` chạy cùng lúc, cùng spam HTTP request vào web server của Box.
  2. **Thiếu Per-Port Cooldown & Max Heals Cap (Bão Request làm tê liệt Daemon):**
     - Khi 22 cổng cùng die, script bắn liên tiếp 22 lệnh `/proxy_recreat` không giãn cách.
     - Modem 4G LTE cần 10–20s để nhả trạm và quay số lại. Nếu không có cooldown (300s / 5 phút), các lượt quét kế tiếp thấy modem chưa kịp có IP lại tiếp tục bắn lệnh recreate đè lên, khiến modem bị kẹt trong vòng lặp reset vô tận (flapping).
     - Daemon quản lý USB 4G trên Box bị nghẽn I/O và treo cứng, Nginx từ chối kết nối (`ERR_CONNECTION_REFUSED` / `WinError 10061`).
  3. **Cạm bẫy Chrome Auto-Upgrade HTTPS (Port 443 Refused):**
     - Box MobiProxy chỉ chạy web HTTP cổng 80 (`http://test.taadaa.click`), không có SSL/HTTPS.
     - Khi Box bị nghẽn hoặc người dùng nhập `test.taadaa.click` trên thanh địa chỉ, Chrome tự động chuyển hướng sang `https://...` (port 443). Do cổng 443 đóng, Chrome hiển thị lỗi `ERR_CONNECTION_REFUSED` khiến người dùng tưởng toàn bộ Box đã sập nguồn.
- **Quy chuẩn Bảo vệ 4 Tầng Bắt buộc cho Watchdog Hardware:**
  1. **Single-Instance Lock (`SingleInstanceLock`):** Dùng kernel-level file lock (`msvcrt.locking` trên Windows, `fcntl` trên Linux) trên file lock chuyên dụng (`mobiproxy_auto_healer.lock`). Nếu lock đang bị giữ, tiến trình mới log info và thoát ngay (exit 0).
  2. **Per-Port Cooldown (`COOLDOWN_SECONDS = 300`):** Lưu `last_heal_time` trong `mobiproxy_stats.json`. Nếu một cổng vừa được recreate dưới 5 phút, bỏ qua không gọi lại.
  3. **Giới hạn số lượng reset mỗi chu kỳ (`MAX_HEALS_PER_RUN = 4`):** Mỗi lượt chạy chỉ heal tối đa 4 cổng, các cổng còn lại để lượt sau để tránh dồn tải phần cứng.
  4. **Giãn cách API & Tăng thời gian chờ (`HEAL_API_DELAY = 2.0s`, `HEAL_WAIT_TIME = 15.0s`):** Giãn cách 2s giữa các request recreate và chờ tối thiểu 15s trước khi probe lại socket/IP.
  5. **Giãn lịch Cron:** Đặt lịch cron tối thiểu 5 phút (`*/5 * * * *`) thay vì 1 phút.

---

## 5. Cạm bẫy Gán Cứng Domain với Cổng 1 (Proxy01 / Port 5101) & Hiệu Ứng Cascading Reset Storm (09/09/2026)

- **Bản chất hạ tầng Box MobiProxy (`test.taadaa.click` — OpenWrt PPPoE Viettel):**
  - **LƯU Ý CỐT LÕI (CẤM NHẦM VỚI SIM 4G):** Box tại Thái Bình là router OpenWrt (MT7621) quay số đa phiên PPPoE (`pppoe-proxy01`..`38`) trực tiếp trên đường cáp quang Viettel để nhận dải IP dân cư động (`117.1.x`, `116.107.x`, `171.224.x`...), **KHÔNG PHẢI SIM/USB 4G**.
  1. **Domain `test.taadaa.click` ăn theo Default Gateway của Cổng 1 (`proxy01` - port 5101):**
     - Trên Box OpenWrt, dịch vụ Cloudflare DDNS (`cloudflare.run`) tự động đồng bộ IP WAN của Box lên tên miền `test.taadaa.click`.
     - Tuy nhiên, Default Gateway / card mạng chính mà Box dùng để lấy IP ra ngoài internet lại ăn chung IP với Cổng 1 (`proxy01` - port 5101, IP public `171.240.99.104` trùng khớp 1:1 với IP domain).
     - Hãng MobiProxy thiết kế sẵn nút riêng trên web quản trị: **`"Reset tất cả và bỏ qua proxy đầu tiên"`** (`action: reset-all-skip`, cờ `skip_first: true`).
  2. **Hiệu ứng sập dây chuyền (Cascading Failure Storm) khi Auto-Healer reset Cổng 1:**
     - Khi Cổng 1 bị reset / ngắt mạng: Domain `test.taadaa.click` lập tức bị mất kết nối / khựng DNS / ngắt tạm thời.
     - Script auto-healer lúc này gửi gói TCP socket probe (với timeout ngắn 1.5s) tới các cổng khác (`5102`, `5103`, `5104`...) qua domain `test.taadaa.click`. Do domain đang bị nghẽn/khựng, **100% các cổng khác đều bị timeout**.
     - Auto-healer hiểu nhầm toàn bộ đàn proxy 32 cổng đã chết, lập tức kích hoạt vòng lặp nhồi tiếp lệnh reset cổng 2, cổng 3, cổng 4... gây bão request (storm) đánh sập hoàn toàn CPU, Nginx và USB hub của Box.
  3. **Kỷ luật vận hành & Bảo vệ Watchdog:**
     - **TẠM DỪNG (PAUSE) auto-healer tự động reset qua cron** khi hệ thống mạng đang bất ổn hoặc chưa có preflight domain.
     - **CẤM TUYỆT ĐỐI TỰ ĐỘNG RESET CỔNG 1 (5101)** trong bất kỳ script watchdog/auto-healer nào (phải luôn set `skip_first = true` hoặc bỏ qua cổng 5101).
     - **Preflight domain trước khi kiểm tra từng port:** Trước khi probe từng cổng proxy qua domain, watchdog bắt buộc phải kiểm tra liveness của chính domain/IP WAN. Nếu domain/gateway không thông, PHẢI FAST-FAIL/SKIP NGAY, cấm kết luận các cổng khác chết để kích hoạt reset.
     - **Kỷ luật giao tiếp khi nhận lệnh User:** Khi user hỏi tình trạng ("Đang pause ... chưa v"), PHẢI trả lời ngay lập tức hiện trạng (Đang chạy / Đã pause) ngắn gọn, dứt khoát, không giải thích vòng vo trước khi hành động.

---

## 6. Cơ Chế Lock Handoff 'blocked' & Cạm Bẫy 'skipped-device-locked' Khi Batch Kế Tiếp Chạy

- **Hiện tượng:**
  - Khi batch đầu tiên (VD: `row-1-060027`) bị lỗi `profile username still mismatched after switch` do proxy 502, runner kết thúc với trạng thái `manual-needed` và thực hiện lock handoff:
    + Tạo `recovery_lock_handoff.json` với `final_status: "blocked"`, `lock_status: "blocked"`.
    + Giữ nguyên file lock tại `C:\Users\Kibe\.codex\device-locks\serial_<serial>.lock.json` với `"status": "blocked"`, `"owner_active": false` (thời hạn tối đa 60 phút theo watchdog để bảo toàn hiện trường).
  - Khi batch kế tiếp (VD: `row-1-071519`) kích hoạt, runner lập tức bỏ qua máy này với kết quả `skipped-device-locked` (`device lock active ... command=run_tiktok.py ... reservation`).
- **Bài học điều phối:**
  - Khi thấy máy bị `skipped-device-locked`, không kết luận nhầm là máy đang bận chạy feed session khác.
  - Phải kiểm tra file lock `.codex/device-locks/serial_<serial>.lock.json`: nếu `status == "blocked"` và PID đã chết (`owner_active == false`), đây là hiện trường của batch trước bị khóa do lỗi kẹt proxy/reconcile.
  - Sau khi heal proxy thành công và xác minh canary, trạng thái lock `blocked` được gỡ bỏ an toàn để đàn máy mở lại hoạt động bình thường.

---

## 7. Quy trình Phục Hồi & Nghiệm Thu Canary 4 Bước Chuẩn (09/09/2026)

- **Cạm bẫy False-Negative 'HEAL_FAILED' / 'timed out' do Modem Redial Lag:**
  - Khi script auto-healer gửi lệnh `/proxy_recreat`, modem 4G LTE bắt đầu ngắt sóng và quay số lại với trạm BTS (thực tế mất 20–35s).
  - Probe của healer sau 15s (`HEAL_WAIT_TIME = 15.0s`) có thể thấy socket còn đóng và ghi nhận `HEAL_FAILED` hoặc API bị timeout nhẹ do CPU Box OpenWrt đang bận chuyển mạch USB.
  - **Kỷ luật:** Tuyệt đối KHÔNG kết luận modem hỏng và KHÔNG gửi lệnh reset dồn dập (tránh vi phạm cooldown 300s và gây bão request). Chờ thêm 15–30s rồi chạy nghiệm thu bằng `--check-only`.
- **Quy trình 4 Bước Nghiệm Thu & Canary:**
  1. **Kích hoạt phục hồi:**
     ```bash
     python D:/Taadaa/AI-Tools/scripts/mobiproxy_auto_healer.py --check-and-heal
     ```
     (Chạy heal có cap tối đa 4 cổng/lượt, giãn cách 2s và cooldown 300s).
  2. **Nghiệm thu trạng thái cluster:**
     ```bash
     python D:/Taadaa/AI-Tools/scripts/mobiproxy_auto_healer.py --check-only
     ```
     (Xác nhận cổng chỉ định đã chuyển sang `OPEN (0)` và `HEALTHY`).
  3. **Kiểm tra Egress thực tế qua Sing-box cho Máy MX:**
     ```bash
     curl -v -m 5 -x http://192.168.110.2:2000X http://api.ipify.org
     ```
     (Đảm bảo trả về HTTP 200 OK và IP công khai khớp với public IP mới của modem).
  4. **Chạy Canary Test đại diện:**
     ```bash
     python D:/Taadaa/tools/inspect_machine.py MX
     ```
     (Kiểm tra hiện trường máy MX qua ADB an toàn O(1) trước khi resume hoặc mở lại batch).

---

## 8. Quy tắc Bắt buộc: Tự Động Change Proxy Khi Rớt Mạng & Bảo Vệ Tuyệt Đối Cổng 1 (5101)

- **Nguyên tắc cốt lõi:**
  - Khi phát hiện rớt proxy (`DEAD` do TCP socket refused `connect_ex=10035` hoặc API status != 'true'), hệ thống tự động kích hoạt **change proxy** (gọi `/proxy_recreat` để modem 4G redial lấy IP mới).
  - **CẤM TUYỆT ĐỐI ĐỤNG ĐẾN CỔNG 1 (`5101`):** Cổng 5101 là cổng gắn cứng với Default Gateway WAN và Cloudflare DDNS (`test.taadaa.click`). Nếu reset cổng 5101, toàn bộ 31 cổng khác sẽ bị timeout và gây ra cascading reset storm đánh sập Box.
- **Cơ chế Bảo vệ 2 Tầng Cứng trong Code (`PROTECTED_HEAL_PORTS = {5101}`):**
  1. **Tầng Client (`MobiProxyClient.recreate_proxy`):**
     Nếu `port in PROTECTED_HEAL_PORTS` $\rightarrow$ raise `ValueError` ngay lập tức, ngăn chặn mọi request `/proxy_recreat` tới cổng 5101 ở mức protocol.
  2. **Tầng Auto-Healer (`MobiProxyAutoHealer.run_scan`):**
     Khi duyệt danh sách `dead_results`, nếu `dead_res.port in PROTECTED_HEAL_PORTS` $\rightarrow$ log cảnh báo `[PROTECTED]` và bỏ qua (`skip`), không đưa vào hàng đợi heal (`uncooled_dead` / `to_heal`).
- **Tuân thủ Giới hạn Vận hành (Error Budget & Hardware Safety):**
  - Giữ nguyên `MAX_HEALS_PER_RUN = 4` (không dồn tải USB Hub).
  - Giữ nguyên `COOLDOWN_SECONDS = 300` (5 phút cooldown tránh modem flapping).
  - Giãn cách API `HEAL_API_DELAY = 2.0s` và `HEAL_WAIT_TIME = 15.0s`.
- **Unit Test & Verification Suite (Focused):**
  - File test: `D:/Taadaa/AI-Tools/scripts/test_mobiproxy_protect_5101.py`
  - Lệnh chạy: `D:/Taadaa/python-envs/automation/Scripts/python.exe -m pytest D:/Taadaa/AI-Tools/scripts/test_mobiproxy_protect_5101.py -x -q` (2/2 passed) kiểm chứng cả 2 tầng Client raise ValueError và Scanner skip 5101.

---

## 9. Nút 'Bật NAT Cổng Proxy' (BẮT BUỘC BẬT) & Kỷ Luật Cấm Võ Đoán Khi Chưa Test Thiết Bị (09/09/2026)

- **Vị trí cài đặt:** Giao diện web Box (`http://test.taadaa.click`) -> tab FIREWALL -> "NAT cổng proxy" (`legacy.nat_port`, form `id="nat-form"`).
- **Cạm bẫy lý thuyết vs Thực tế trên thiết bị S7:**
  - *Cạm bẫy võ đoán lý thuyết:* Tưởng rằng proxy daemon L7 tự bind socket ra interface PPPoE nên tắt NAT cổng proxy vẫn có mạng. CẤM TUYỆT ĐỐI trả lời user khi chưa chạy probe thực tế trên thiết bị.
  - *Thực tế kiểm chứng trên S7 (Máy 1):*
    + **Khi TẮT NAT (`nat_port: 0`):** Firewall OpenWrt trên Box chặn không cho lưu lượng từ WAN (Đà Nẵng) đi vào các cổng proxy `5101..5138` (`WinError 10061`). Sing-box Đà Nẵng lập tức trả về `HTTP/1.1 502 Bad Gateway`. Toàn bộ dàn máy S7 **MẤT MẠNG HOÀN TOÀN** (`dumpsys connectivity` chuyển sang `lastValidated{false}`).
    + **Khi BẬT NAT (`nat_port: 1`):** Firewall mở luồng Port Forwarding cho các cổng 51xx. S7 **CÓ MẠNG NGAY LẬP TỨC** (`dumpsys connectivity` chuyển sang `lastValidated{true}`) và `curl` qua Sing-box `192.168.110.2:2000X` trả về `200 OK` kèm đúng IP Public dân cư Viettel của từng luồng PPPoE.
- **Quy tắc bất biến:**
  - **BẮT BUỘC PHẢI BẬT (`nat_port: 1`).**
  - Khi dàn máy báo `502 Bad Gateway` và mất mạng hàng loạt: Kiểm tra ngay `settings.get` xem `legacy.nat_port` có bị tắt về 0 hay không.
  - Nếu bị tắt, kích hoạt lại bằng API: `POST api.php?action=proxy.nat` với `{"enabled": true}` kèm header `X-CSRF-Token` lấy từ `<meta name="csrf-token">` trong `index.php`.



