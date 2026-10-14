# Quy hoạch Cuốn Chiếu Ban Đêm (Bỏ Ca 4 Nuôi Acc), Chạy Avatar & 2FA Tới 05:15 Sáng và Trọng Tài Dọn Cache (15/10/2026)

## 1. Bối cảnh & Thay đổi Kiến Trúc Lịch Nuôi (Bỏ Ca 4 Đêm)
- **Lịch nuôi acc TikTok chính thức:** Đã bỏ hoàn toàn Ca 4 ban đêm (00:00 - 02:00). Farm vận hành theo chu kỳ 3 Ca x 2 Phiên/ngày:
  * Ca 1 (Sáng): Phiên 1 lúc `06:00`, Phiên 2 lúc `08:00` (kết thúc toàn bộ trước `09:30`).
  * Ca 2 (Trưa): Phiên 1 lúc `12:00`, Phiên 2 lúc `14:00` (kết thúc toàn bộ trước `15:30`).
  * Ca 3 (Tối): Phiên 1 lúc `18:00`, Phiên 2 lúc `20:00` (kết thúc toàn bộ trước `21:30`).
- **Khoảng rảnh khổng lồ ban đêm:** Từ `21:30` tối hôm trước đến `05:15` sáng hôm sau (~8 tiếng) được giải phóng toàn bộ tài nguyên thiết bị cho các tác vụ phụ trợ (Upload Avatar, Add 2FA TikTok).

## 2. Quy Tắc Cuốn Chiếu Liên Tục Né Giờ Nuôi (Rolling Continuous Window)
- **Hàm kiểm tra khung giờ an toàn (`is_safe_rolling_window`):**
  * Né 3 ca nuôi chính thức: `05:15 - 09:30`, `11:45 - 15:30`, `17:45 - 21:30`.
  * Khung rảnh ban ngày: `09:30 - 11:45` và `15:30 - 17:45`.
  * Khung rảnh ban đêm: `21:30 - 05:15` (chạy trọn vẹn qua mốc 5h sáng, dừng lúc 05:15 để tạo đệm 30-45 phút làm mát thiết bị trước Ca 1).

## 3. Trọng Tài Chống Va Chạm Với Cron Dọn Cache TikTok Cuối Ngày
- **Cron dọn cache (`cron_clear_tiktok_cache.py`):**
  * Chạy lúc `04:00` sáng (`0 4 * * *`).
  * Kiểm tra điều kiện: Ca 3 tối hôm trước đã xong (`yesterday_ca3_phien2` hoặc `yesterday_ca3`).
  * Khóa thiết bị qua `DeviceLock(serial, machine, project="clear-cache")`, hoàn tất sau 10-15 phút.
- **Hai tầng bảo vệ chống đụng độ cho Avatar & 2FA:**
  1. *Tầng 1 (Time-based Window):* `is_safe_rolling_window` chặn khung giờ `04:00 - 04:30`, nhường tuyệt đối cho dọn cache.
  2. *Tầng 2 (Process-liveness Lockout):* Hàm `is_clear_cache_active()` quét psutil tìm process `clear-tiktok-cache` hoặc `cron_clear_tiktok_cache`. Nếu phát hiện đang chạy ở bất kỳ thời điểm nào $\rightarrow$ lập tức return 0 / nhả khóa, cấm chạy đè.

## 4. Báo Cáo Định Kỳ 6H Về Farm Alert (Chống Spam & Xóa Nhãn Sai)
- **Nhịp báo cáo:** Thay vì báo lắt nhắt từng batch hoặc ngắt ca lúc 23:30, hệ thống chuyển sang nhịp định kỳ **mỗi 6H** (`00:00`, `06:00`, `12:00`, `18:00`) hoặc khi **hoàn tất 100%**.
- **Cấm gán nhãn gây hiểu nhầm:** Tuyệt đối không dùng cụm từ `"nhường lịch nuôi TikTok / lock tiến trình khác"` cho các tài khoản chưa kịp xử lý khi hết giờ. Thay bằng số liệu rõ ràng: `"• Còn lại: N tài khoản chưa up"`.
- **Silent Batch:** Giữa các khung 6H, cron chạy ngầm cuốn chiếu hoàn toàn im lặng trên stdout để giữ sạch kênh thông báo Telegram.

## 5. Kỷ Luật Exit Code Watchdog `no_agent: true` & Đệm Chặn 04:45
- **Exit Code Semantics trong Hermes:**
  * Với job `no_agent: true`, bất kỳ `exit code != 0` nào đều bị Hermes scheduler bắt lại và giật chuông cảnh báo `⚠️ Cron failed: Script exited with code 1`.
  * CẤM script trả về `return 1` khi chỉ dính `fail > 0` (máy lẻ lỗi/timeout là bình thường trong cụm 160 máy). Script BẮT BUỘC lưu `fail_count` vào persistent state JSON để báo cáo vào mốc 6H, nhưng return `0` khi `code in ACCEPTABLE_RETURN_CODES (0, 4)`. Chỉ return non-zero khi chính tiến trình runner bị crash hoàn toàn.
- **Đệm an toàn trước ca sáng (04:45 Hard Cutoff):**
  * Mỗi batch 2FA/Avatar chạy mất từ 15-25 phút. Nếu cho phép khởi chạy lúc `05:00 - 05:07`, tiến trình sẽ kéo dài qua mốc `05:15` và chiếm giữ Device Lock khi Ca 1 bắt đầu lúc `06:00`.
  * `is_safe_rolling_window` BẮT BUỘC chặn khởi chạy batch mới sau `04:45`: `if (h == 4 and m >= 45) or (h == 5 and m >= 15) or h in (6, 7, 8): return False`.

## 6. Khóa Trần Concurrency `--max-workers 15` & SSH PowerShell Exit Code
- **Bắt buộc `--max-workers 15`:** Cả Kibe lẫn Admin đều phải truyền `--max-workers 15` vào `run_batch_live_2fa.py`. Tuyệt đối không dùng `40` để tránh bão tranh chấp lock workbook trên OneDrive.
- **PowerShell SSH `$LASTEXITCODE`:** Khi dispatch cluster Admin qua `ssh admin-farm powershell -EncodedCommand`, PowerShell script BẮT BUỘC có dòng `exit $LASTEXITCODE` ở cuối. Nếu thiếu, PowerShell sẽ nuốt return code của Python (hoặc trả 1 do stderr) làm watchdog nhận diện sai trạng thái thành công.
