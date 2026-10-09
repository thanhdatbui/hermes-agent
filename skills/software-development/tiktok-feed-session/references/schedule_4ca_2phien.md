# Quy chuẩn Lịch Trình Nuôi: 4 Ca x 2 Phiên thuần túy (Không Cohort / Không Manifest)

Bỏ hoàn toàn mô hình picker / cohort / manifest. Hệ thống feed session chạy theo mô hình **4 Ca x 2 Phiên** thuần túy (tổng cộng 8 mốc chạy / ngày):

## 1. 8 Mốc Giờ Chạy trong Ngày
- **Ca 1 (Sáng):**
  - Phiên 1 lúc 06:00 (Row 1 / Row 2)
  - Phiên 2 lúc 08:00 (Row 1 / Row 2)
- **Ca 2 (Trưa):**
  - Phiên 1 lúc 12:00 (Row 3 / Row 4)
  - Phiên 2 lúc 14:00 (Row 3 / Row 4)
- **Ca 3 (Tối):**
  - Phiên 1 lúc 18:00 (Row 5 / Row 6)
  - Phiên 2 lúc 20:00 (Row 5 / Row 6)
- **Ca 4 (Đêm):**
  - Phiên 1 lúc 00:00 (Row 7 / Row 8)
  - Phiên 2 lúc 01:30 (Row 7 / Row 8)

## 2. Quy Tắc Parity Ngày (Ngày Chẵn / Lẻ)
- **Ngày Chẵn (`date.day % 2 == 0`):** chạy Row Chẵn.
  - 00h / 01h30 -> Row 8
  - 06h / 08h   -> Row 2
  - 12h / 14h   -> Row 4
  - 18h / 20h   -> Row 6
- **Ngày Lẻ (`date.day % 2 == 1`):** chạy Row Lẻ.
  - 00h / 01h30 -> Row 7
  - 06h / 08h   -> Row 1
  - 12h / 14h   -> Row 3
  - 18h / 20h   -> Row 5

## 3. Dead-zone Bảo Trì
- Sau 02:30 đến trước 06:00 (tức `02:30 -> 05:59`): Dead-zone, runner tuyệt đối không spawn session.

## 4. State Key Phục Vụ Deduplication (`window_key`)
- Giờ chẵn/tròn: `<date-iso>T<hour:02d>` (ví dụ: `2026-09-11T06`, `2026-09-11T08`).
- Mốc có phút lẻ (01:30): `<date-iso>T0130` (ví dụ: `2026-09-11T0130`).

## 5. Pitfall So Sánh Khung Giờ Watchdog / Scheduler
- Sử dụng phép so sánh chuỗi half-open interval `start <= r_hm < end`:
  - Với Ca 3 Phiên 2 (`20:00` đến `00:00`), chuỗi `"00:00"` nhỏ hơn `"20:00"` trong phép so sánh chuỗi lexicon chuẩn, dẫn tới biểu thức `20:00 <= r_hm < 00:00` luôn là `False`.
  - Khắc phục: Dùng `"24:00"` làm `end`, hoặc parse ra tổng số phút trong ngày `h * 60 + m` (với `00:00` kết thúc = 1440 phút).
