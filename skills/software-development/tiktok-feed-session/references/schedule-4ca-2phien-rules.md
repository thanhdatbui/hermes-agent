# Lịch trình & Quy chuẩn vận hành 4 Ca x 2 Phiên (Migrated 11/09/2026)

## 1. Cấu trúc 4 Ca x 2 Phiên (8 window/ngày)
Toàn bộ hệ thống chạy $O(1)$ gọi trực tiếp `run-feed-session.ps1`, không qua picker/cohort/manifest.

- **Ca 1 (Sáng):**
  - Phiên 1 lúc `06:00` (Row 1 ngày lẻ / Row 2 ngày chẵn): Feed + Follow 1 (15–18 lượt)
  - Gap A nghỉ giữa 2 phiên: `~75 phút`
  - Phiên 2 lúc `08:00` (Row 1 ngày lẻ / Row 2 ngày chẵn): Feed + Follow 2 + Đăng video
  - Gap B nghỉ chuyển ca: `~3 tiếng 10 phút` (từ 08:50 đến 12:00)
- **Ca 2 (Trưa):**
  - Phiên 1 lúc `12:00` (Row 3 ngày lẻ / Row 4 ngày chẵn): Feed + Follow 1
  - Gap A: `~75 phút`
  - Phiên 2 lúc `14:00` (Row 3 ngày lẻ / Row 4 ngày chẵn): Feed + Follow 2 + Đăng video
  - Gap B: `~3 tiếng 10 phút` (từ 14:50 đến 18:00)
- **Ca 3 (Tối):**
  - Phiên 1 lúc `18:00` (Row 5 ngày lẻ / Row 6 ngày chẵn): Feed + Follow 1
  - Gap A: `~75 phút`
  - Phiên 2 lúc `20:00` (Row 5 ngày lẻ / Row 6 ngày chẵn): Feed + Follow 2 + Đăng video
  - Gap B: `~3 tiếng 10 phút` (từ 20:50 đến 00:00)
- **Ca 4 (Đêm):**
  - Phiên 1 lúc `00:00` (Row 7 ngày lẻ / Row 8 ngày chẵn): Feed + Follow 1
  - Gap A: `~45 phút`
  - Phiên 2 lúc `01:30` (Row 7 ngày lẻ / Row 8 ngày chẵn): Feed + Follow 2 + Đăng video
  - Dead zone: `02:30 -> 05:59` (dọn cache toàn farm lúc 04:00 sáng).

## 2. Nguyên tắc Gap & Chống Account Linking
- **Gap A (trong ca) < Gap B (chuyển ca):** 
  - Trong cùng ca (cùng 1 nick), mở app 2 lần cách nhau 45–75 phút mô phỏng hành vi tự nhiên của người thật trong 1 buổi sinh hoạt.
  - Chuyển giữa 2 ca (đổi sang nick khác trên cùng máy) bắt buộc cách nhau `>= 3 tiếng` để máy nguội sâu và chống TikTok phát hiện dấu chân liên đới thiết bị/IP (Co-location farm footprint).
- **Quy tắc Switch Account:**
  - Tuyệt đối KHÔNG switch nick sớm ở cuối ca trước rồi để idle hàng giờ.
  - Bắt buộc switch ở **ĐẦU CA TIẾP THEO** theo quy trình: `Rotate IP/Verify VPN -> Switch/Open Nick -> Warmup 30s -> Chạy`.

## 3. Cơ chế Jitter
- **Jitter máy:** PowerShell runner luôn truyền `-RandomizeMachineOrder` + `-MachineStartStaggerMs "2000,8000"` (80 máy trải đều trong 5–8 phút).
- **Jitter start:** Cron tick `*/15 * * * *`, runner dedup theo `window_key` (`<date-iso>T06`, `T08`, `T12`, `T14`, `T18`, `T20`, `T00`, `T0130`).
