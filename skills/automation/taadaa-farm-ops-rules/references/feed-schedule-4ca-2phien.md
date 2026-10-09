# Feed Schedule: 4 Ca × 2 Phiên (Migrated 11/09/2026)

## Lịch trình chính xác

| Ca | Phiên | Giờ bắt đầu | Row (Chẵn / Lẻ) | Nội dung |
|----|----|----|----|----|
| **Ca 1 (Sáng)** | Phiên 1 | 06:00 | Row 2 / Row 1 | Feed + Follow đợt 1 (15-18 lượt) |
| | Phiên 2 | 08:00 | Row 2 / Row 1 | Feed + Follow đợt 2 + **Đăng Video** |
| **Ca 2 (Trưa)** | Phiên 1 | 12:00 | Row 4 / Row 3 | Feed + Follow đợt 1 |
| | Phiên 2 | 14:00 | Row 4 / Row 3 | Feed + Follow đợt 2 + **Đăng Video** |
| **Ca 3 (Tối)** | Phiên 1 | 18:00 | Row 6 / Row 5 | Feed + Follow đợt 1 |
| | Phiên 2 | 20:00 | Row 6 / Row 5 | Feed + Follow đợt 2 + **Đăng Video** |
| **Ca 4 (Đêm)** | Phiên 1 | 00:00 | Row 8 / Row 7 | Feed + Follow đợt 1 |
| | Phiên 2 | 01:30 | Row 8 / Row 7 | Feed + Follow đợt 2 + **Đăng Video** |

## Các quy tắc kỹ thuật

- **Dead zone:** 02:30 - 05:59 (không spawn, không dọn cache, backup lúc 04:00 riêng biệt).
- **Gap A (trong Ca):** ~75-90 phút (phiên 1 xong nghỉ 1h15' trước phiên 2).
- **Gap B (chuyển Ca):** ~3h+ (máy nghỉ tản nhiệt, reset IP, switch acc).
- **Runner:** `tiktok_runner.py` thuần O(1), đọc giờ → xác định Row/Phiên → spawn `run-feed-session.ps1` trực tiếp. **CẤM cohort/manifest/picker**.
- **Watchdog:** `feed_session_watchdog.py` theo dõi 8 window riêng biệt, báo cáo Telegram tách bạch Phiên 1/Phiên 2.
- **Follow budget:** 15-18/phiên → 30-36/ngày/nick (min 15, max 18 theo config máy).
- **Upload hook:** Chỉ kích hoạt ở **Phiên 2** (session_index == 2).