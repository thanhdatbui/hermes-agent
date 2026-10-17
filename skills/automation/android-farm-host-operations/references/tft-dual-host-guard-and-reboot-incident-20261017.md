# Bẫy Tử Huyệt TFT Game Guard Chỉ Quét Máy Cục Bộ & Client 3D Khiến Reboot Máy Admin Trong Trận Rank (17/10/2026)

## 1. Hiện Trường Sự Cố (17:20:01 - 17/10/2026)
- **Hành vi xảy ra:** Đúng mốc reboot 17:20 trước Ca 3 tối, Task Scheduler `Taadaa_Farm_Daily_Reboot_1135` trên Kibe PC kích hoạt `farm_preflight_daily_reset.py`.
- **Hệ quả nghiêm trọng:** Máy Admin (`admin-farm`) bị gửi lệnh `shutdown /r /t 2` và sập nguồn sau 2 giây khi User đang trong trận đấu xếp hạng (Rank) Đấu Trường Chân Lý (TFT), dẫn tới bị xử thua AFK.

## 2. Phân Tích 3 Lỗ Hổng Cốt Lõi (Root Causes)
1. **Lỗ hổng 1 — Mù hoàn toàn máy Admin (Local-Only Detection):**
   - User chơi game trực tiếp trên máy Admin (`D:\x\Riot Games\League of Legends` và overlay `D:\TFTAcademy\TFTAcademy.exe`).
   - Hàm `is_tft_match_in_progress()` trong `farm_preflight_daily_reset.py` chỉ chạy `psutil` trên máy Kibe. Script mù hoàn toàn hiện trạng tiến trình trên máy Admin nhưng lại gửi lệnh SSH reboot máy Admin trước tiên:
     `ssh -o ConnectTimeout=5 admin-farm "shutdown /r /t 2"`
2. **Lỗ hổng 2 — Danh sách tiến trình bị bóp ngu dốt (Narrow Process Set):**
   - Trong code chỉ khai báo: `TFT_ACTIVE_MATCH_PROCESSES = {"league of legends.exe"}`.
   - Bỏ qua hoàn toàn:
     * `tftclient-win64-shipping.exe` & `tftclient.exe` (Client TFT độc lập mới của Riot).
     * `leagueclient.exe` & `leagueclientux.exe` (Client LMHT / sảnh chờ / chọn tướng / màn hình loading).
     * `tftacademy.exe` (Tool overlay phân tích đội hình TFT).
     * `riotclientservices.exe`.
3. **Lỗ hổng 3 — Bỏ sót binary engine match của client TFT mới:**
   - Client TFT độc lập của Riot khi vào trận thực tế chạy binary `TFTClient-Win64-Shipping.exe`, không phải `League of Legends.exe`. Nếu chỉ kiểm tra `League of Legends.exe` thì game TFT mới vào trận vẫn bị coi là không có match.

## 3. Quy Chuẩn TFT Game Guard Bắt Buộc (Invariant v2.0 - Chuẩn hóa 17/10/2026)
1. **Quét song song 2 máy (Dual-Host Scan):**
   - Phải kiểm tra danh sách tiến trình trên CẢ Kibe PC VÀ Admin PC (qua SSH `tasklist /FO CSV /NH`).
   - Nếu kết nối SSH sang Admin PC timeout hoặc lỗi -> BẮT BUỘC Fail-Safe: coi như Admin PC đang bận/đang chơi game, HỦY REBOOT NGAY LẬP TỨC.
2. **Bộ tiến trình in-match chặn reboot:**
   ```python
   TFT_ACTIVE_MATCH_PROCESSES = {
       "league of legends.exe",
       "tftclient-win64-shipping.exe",
   }
   ```
3. **Quy tắc phân định Client/Lobby vs In-Match (User Clarified 17/10/2026: "Đang ở client, sảnh chờ thì được reboot"):**
   - Các tiến trình sảnh chờ / client nền / companion (`LeagueClient.exe`, `LeagueClientUx.exe`, `RiotClientServices.exe`, `TFTAcademy.exe`) **KHÔNG CHẶN REBOOT**. Khi sếp chỉ mở client hoặc đang ở sảnh chờ ngoài, máy vẫn được reboot làm sạch RAM/USB trước ca.
   - **CHỈ KHI engine 3D in-match thực sự xuất hiện** (`league of legends.exe` hoặc `tftclient-win64-shipping.exe`) trên **bất kỳ máy nào (Kibe hoặc Admin)** $\rightarrow$ **HỦY REBOOT NGAY LẬP TỨC (`ABORT`)** để không bị AFK / xử thua ván cờ.
