# Shift-Aware Sentinel & In-Flight Lock Guard Protocol (2026-10-15)

## 1. Bẫy Bỏ Qua Reboot Trưa/Tối Do Sentinel Theo Ngày (The Daily Sentinel Trap)
- **Hiện tượng thực tế (Sự cố 15/10/2026):**
  * Task Scheduler Windows đã cài đặt đúng 3 mốc trigger reboot: `05:20`, `11:20`, `17:20`.
  * Ca sáng lúc 05:20 chạy reboot thành công và ghi file cờ: `reboot_sentinel_YYYY-MM-DD.flag`.
  * Đến mốc 11:20 (trước Ca 2 Trưa), script `farm_preflight_daily_reset.py` kiểm tra `sentinel.exists()`. Do tên file chỉ chứa ngày `YYYY-MM-DD`, script thấy file đã tồn tại $\rightarrow$ log `[SKIP] Hom nay da reboot (...)` và thoát `exit 0`!
  * Hậu quả: Mốc 11:20 và 17:20 hoàn toàn bị bỏ qua, thanh ghi USB 2.0 EHCI không được giải phóng sau ca sáng $\rightarrow$ Ca trưa chạy dồn dập 80 máy tiếp tục gây nghẽn bus và văng thiết bị.

## 2. Quy Chuẩn Đặt Tên Sentinel Theo Ca (Shift-Aware Sentinel)
- **Quy tắc phân định khung giờ chuẩn 3 Ca:**
  * Ca 1 (Sáng / morning): `hour < 9` (Mốc reboot 05:20, đệm trước Ca 06:00).
  * Ca 2 (Trưa / noon): `9 <= hour < 15` (Mốc reboot 11:20, đệm trước Ca 12:00).
  * Ca 3 (Tối / evening): `hour >= 15` (Mốc reboot 17:20, đệm trước Ca 18:00).
- **Cấu trúc tên file cờ:**
  `reboot_sentinel_{YYYY-MM-DD}_{shift}.flag` (ví dụ: `reboot_sentinel_2026-10-15_morning.flag`, `..._noon.flag`, `..._evening.flag`).
- Đảm bảo mỗi mốc trong ngày có 1 cờ riêng biệt, chống reboot lặp trong cùng một ca nhưng không chặn các ca tiếp theo.

## 3. Khóa Bảo Vệ Ca Chạy Dở (In-Flight Active Device Lock Guard)
- **Tình huống kích hoạt:** Khi mốc reboot 11:20 hoặc 17:20 kích hoạt nhưng trên farm vẫn còn ca nuôi/reg/2FA đang chạy dở chưa dứt điểm (ví dụ phiên trễ kéo dài qua 11:20, hoặc user kích hoạt ca lúc 12:02).
- **Cơ chế kiểm tra an toàn trước khi nã reboot:**
  * Quét thư mục `~/.codex/device-locks/*.lock.json`.
  * Nếu phát hiện bất kỳ file lock nào có `status: "running"` và PID tương ứng còn sống (`psutil.pid_exists(pid) == True`):
    $\rightarrow$ **`[SKIP]` ngay lập tức**, không phát lệnh reboot để tránh làm gãy dở tiến trình nuôi acc, tránh rách session TikTok hoặc mất dữ liệu.

## 4. Bản Chất Lỗi "Prepare-Tiktok Failed To Focus" Khi Chạy Batch
- Trong `device_prepare.py` và `automation_core.startup`, runner ĐÃ CÓ sẵn cơ chế tự phục hồi 10 lần (`PREPARE_FOCUS_MAX_ATTEMPTS = 10`), delay 1.5s/lần, tự bấm lại monkey ở attempt 4 & 7, và gọi `dismiss_tiktok_popups`.
- Khi 80 máy cùng chạy trên 2 chip controller USB 2.0 EHCI, lệnh shell `dumpsys window` bị timeout ngầm liên tiếp qua bus USB, khiến `focus_reader` trả về `focused_package = None (unknown)` trong cả 10 lần thử.
- Đây là lỗi do nghẽn bus USB phần cứng của PC Host, không phải do script thiếu logic retry hay do app TikTok bị hỏng.
