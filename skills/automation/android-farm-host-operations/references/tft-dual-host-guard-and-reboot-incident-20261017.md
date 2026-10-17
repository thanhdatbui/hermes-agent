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

## 4. Quy Chuẩn Warcraft 3 Game Guard (User Invariant Bổ Sung 17/10/2026)
- **Quy tắc người dùng:** *"Khi tao đang chơi warcraft cũng đéo được phép reboot máy, miễn là app warcraft3 mở"*.
- **Khác biệt quan trọng so với TFT:** Với TFT, ở client/sảnh chờ thì được phép reboot. Với Warcraft 3, **MIỄN LÀ APP ĐANG MỞ** (bất kể ở menu chính, sảnh custom map hay trong ván đấu) $\rightarrow$ **CẤM TUYỆT ĐỐI REBOOT MÁY**.
- **Bộ tiến trình nhận diện Warcraft 3:**
  ```python
  WARCRAFT_PROCESSES = {
      "war3.exe",
      "w3l.exe",
      "warcraft iii.exe",
      "frozen throne.exe",
  }
  ```
- **Phạm vi kiểm tra:** Quét song song trên cả Kibe PC (`_running_image_names()`) và Admin PC qua SSH. Nếu phát hiện bất kỳ tiến trình nào trong `WARCRAFT_PROCESSES` trên máy nào $\rightarrow$ lập tức hủy bỏ chuỗi reboot (`ABORT`).

## 5. Kiến Trúc Sentinel Độc Lập Admin/Kibe, Single-Instance Lock & Error Contract Hermes (Closeout Hardening 17/10/2026)
- **Tách Sentinel độc lập theo từng máy (`reboot_sentinel_{shift}_{machine}.flag`):**
  * *Bẫy sentinel chung:* Nếu Admin reboot thành công (qua SSH) nhưng Kibe reboot thất bại hoặc abort do lỗi bảo toàn session, sentinel chung bị ghi sẽ khiến Kibe mất lượt reboot; nếu không ghi sentinel thì Admin bị reboot lặp lại ở lần chạy tiếp theo trong ca.
  * *Giải pháp:* Tách cờ `..._admin.flag` và `..._kibe.flag`. Máy nào dispatch thành công thì ghi cờ máy đó. Lần chạy sau chỉ retry máy chưa reboot.
- **Khóa Single-Instance OS-Level (`farm_preflight_daily_reset.lock`):**
  * Dùng `msvcrt.locking` trên Windows (hoặc `fcntl.flock` trên POSIX) khóa file lock nhị phân khi bắt đầu `main()`.
  * Nếu có tiến trình thứ 2 kích hoạt cùng lúc (do trigger trùng hoặc user chạy tay), tiến trình mới tự thoát mã 0 với cờ `skipped_concurrent_run`, chống xung đột race condition. Khóa tự nhả khi tiến trình kết thúc (kể cả khi crash).
- **Error Contract Nghiêm Ngặt của `preserve_in_flight_sessions()`:**
  * CẤM nuốt ngoại lệ âm thầm và trả về 0. Nếu SQLite SessionDB bị lỗi hoặc không thể đọc ghi, hàm BẮT BUỘC raise `RuntimeError` để luồng preflight lập tức **HỦY REBOOT (Fail-Closed, `outcome = 'aborted_preserve_failed'`)**, bảo vệ an toàn tuyệt đối cho các session chat dang dở của user.
  * Chỉ xóa file marker `.clean_shutdown` khi và chỉ khi `marked > 0` (đã thực sự đánh dấu bảo toàn thành công ít nhất 1 session).
- **Structured Summary JSON Telemetry:**
  * Kết thúc mỗi lần chạy (kể cả khi gặp exception trong `try...finally`), script luôn xuất ra 1 dòng log có cấu trúc:
    `[SUMMARY] {"outcome": "...", "admin": "...", "kibe": "...", "admin_sentinel": "...", "kibe_sentinel": "...", "check_only": bool}` giúp hệ thống giám sát tự động kiểm toán kết quả end-to-end mà không cần parse text tự do.
- **Triệt tiêu Deprecation Warning Pytest (`asyncio_default_fixture_loop_scope`):**
  * Cấu hình trong `D:/Taadaa/tools/pytest.ini`: `asyncio_default_fixture_loop_scope = function` để giữ log test suite sạch 100%, không bị Reviewer trừ điểm Observability.

