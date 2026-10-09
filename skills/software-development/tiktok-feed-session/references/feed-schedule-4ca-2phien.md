# TikTok Feed Schedule: 4 Ca × 2 Phiên (Migrated 11/09/2026)

## Schedule Table
| Ca | Phiên | Giờ | Row (偶/奇) | Nội dung | Gap sau |
|---|---|---|---|---|---|
| Ca 1 (Sáng) | P1 | 06:00 | Row2/Row1 | Feed + Follow 1 (15-18) | ~75p (Gap A) |
| Ca 1 (Sáng) | P2 | 08:00 | Row2/Row1 | Feed + Follow 2 + Upload | ~3h10 (Gap B) |
| Ca 2 (Trưa) | P1 | 12:00 | Row4/Row3 | Feed + Follow 1 (15-18) | ~75p (Gap A) |
| Ca 2 (Trưa) | P2 | 14:00 | Row4/Row3 | Feed + Follow 2 + Upload | ~3h10 (Gap B) |
| Ca 3 (Tối) | P1 | 18:00 | Row6/Row5 | Feed + Follow 1 (15-18) | ~75p (Gap A) |
| Ca 3 (Tối) | P2 | 20:00 | Row6/Row5 | Feed + Follow 2 + Upload | ~3h10 (Gap B) |
| Ca 4 (Đêm) | P1 | 00:00 | Row8/Row7 | Feed + Follow 1 (15-18) | ~45p (Gap A) |
| Ca 4 (Đêm) | P2 | 01:30 | Row8/Row7 | Feed + Follow 2 + Upload | ~3h40 (dead zone) |

Dead zone: 02:30→05:59 (cache cleanup 04:00)

## Gap Rules (User approved 11/09/2026)
- **Gap A** (P1→P2 trong 1 Ca) = 75–90 phút (Ca 4: 45 phút)
- **Gap B** (phiên cuối Ca trước → phiên đầu Ca sau) = 3+ giờ
- **Gap A < Gap B** — lượt cuối Ca này KHÔNG được quá sát lượt đầu Ca sau
- Switch account: Luôn switch ở ĐẦU Ca sau, KHÔNG switch sớm hàng giờ

## Design Rationale (Claude CLI Opus High tư vấn 11/09/2026)
1. **TikTok Anti-spam**: 15-18 follow/phiên × 2 = 30-36 follow/ngày/nick. 
   Gap A ngắn vừa phải không tăng risk, chỉ burst rate trong phiên mới là thứ thuật toán soi.
2. **Co-location linking**: Gap B dài (3h+) tách bạch dấu足 giữa 2 nick dùng chung device fingerprint + IP.
3. **Device thermal**: Gap B dài = cửa sổ vàng để nguội sâu + sạc pin + wear-leveling.
4. **Desync 80 máy**: Rải start ±20-30 phút quanh mốc Ca, jitter mọi gap ±15%.

## Files Updated
- `C:/Users/Kibe/AppData/Local/hermes/scripts/tiktok_runner.py`: 8 slot `_SCHEDULE` dict
- `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py`: 8 SESSION_WINDOWS

## Night Chain Pipeline (Sequential)
- Ca 4 (00:00) do `tiktok_runner.py` xử lý (P1 + P2)
- `night_chain_reg_pipeline` chỉ chạy: Ca 4 xong → Reg Gmail → Add 2FA (nối tiếp)
- Reg TikTok đã chuyển sang on-demand (máy thiếu acc → tự mua mail + reg trong Ca đó)
