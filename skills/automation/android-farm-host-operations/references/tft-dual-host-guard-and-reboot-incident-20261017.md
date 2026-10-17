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
3. **Lỗ hổng 3 — Ảo tưởng "chỉ chặn khi trong trận 3D, ở sảnh vẫn reboot":**
   - Tư duy tự ý chia nhỏ "lobby vs in-match" là sai lầm chết người. Game có giai đoạn tìm trận, cấm chọn, loading screen (chưa sinh process 3D) hoặc giữa 2 ván đấu liên tiếp. Bất kỳ tiến trình nào của Riot/TFT đang chạy đều chứng minh User đang trong phiên chơi game (Gaming Session).

## 3. Quy Chuẩn TFT Game Guard Bắt Buộc (Invariant v2.0)
1. **Quét song song 2 máy (Dual-Host Scan):**
   - Phải kiểm tra danh sách tiến trình trên CẢ Kibe PC VÀ Admin PC (qua SSH PowerShell / tasklist).
   - Nếu kết nối SSH sang Admin PC timeout hoặc lỗi -> BẮT BUỘC Fail-Safe: coi như Admin PC đang bận/đang chơi game, HỦY REBOOT NGAY LẬP TỨC.
2. **Bắt toàn bộ họ tiến trình TFT / League / Riot:**
   ```python
   TFT_GAME_PROCESSES = {
       "league of legends.exe",
       "leagueclient.exe",
       "leagueclientux.exe",
       "leagueclientuxrender.exe",
       "riotclientservices.exe",
       "tftclient.exe",
       "tftclient-win64-shipping.exe",
       "tftacademy.exe",
   }
   ```
3. **Chỉ cần 1 tiến trình tồn tại trên BẤT KỲ máy nào -> HỦY REBOOT NGAY (`ABORT`):**
   - Tuyệt đối không phân biệt sảnh chờ hay trong trận.
   - Bảo toàn tuyệt đối trải nghiệm của User là ưu tiên tối cao.
