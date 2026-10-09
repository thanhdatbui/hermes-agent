# Sequential Night Chain (Chuỗi ban đêm tuần tự)

## Cấu trúc (Trigger 00:00)

```text
00:00 ──► Phase 1: Ca 4 Feed Row 7/8 (kết thúc ~00:45)
    │
    ▼ (ngay lập tức khi Phase 1 return)
Phase 2: Reg Gmail (run_all.ps1)
    │
    ▼ (ngay lập tức khi Phase 2 return)
Phase 3: Add 2FA TikTok (run_batch_live_2fa.py)
```

## Các thay đổi so với cũ (11/09/2026)

| Cũ (Cố định giờ) | Mới (Nối tiếp) |
|---|---|
| 01:00: Reg Gmail | Phase 2 chạy ngay khi Phase 1 xong |
| 02:00: Reg TikTok | **BỎ HỎA** (chuyển sang on-demand) |
| 03:00: Add 2FA | Phase 3 chạy ngay khi Phase 2 xong |
| 04:00: Clear cache | Tách biệt (cron riêng) |

## Logic xác định Row Ca 4
- Lúc 00:00 thuộc ngày **hôm đó** (chẵn/lẻ của date hiện tại).
- `feed_row = 8 if (now.day % 2 == 0) else 7`.

## Xử lý lỗi (Fail-soft chain)
- Phase 1 fail → log alert → vẫn chạy Phase 2.
- Phase 2 fail → log alert → vẫn chạy Phase 3.
- Không bao giờ block toàn bộ chuỗi vì 1 phase lỗi.

## Cron config
- `night-chain-reg-pipeline`: `0 0 * * *` (chạy đúng 00:00).
- Cron `phase9-runner-tiktok-feed` vẫn chạy `*/15 * * * *` cho các Ca ban ngày (không đụng Ca 4).