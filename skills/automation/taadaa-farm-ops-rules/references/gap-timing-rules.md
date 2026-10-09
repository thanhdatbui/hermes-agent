# Gap Timing Rules (Khoảng nghỉ giữa Phiên & Ca)

## Nguyên tắc vàng
**Gap A (trong 1 Ca) < Gap B (chuyển Ca)**

| Khoảng cách | Giá trị | Mục đích |
|---|---|---|
| **Gap A** (Phiên 1 → Phiên 2) | 75 - 90 phút | Tự nhiên cho 1 nick (người thật mở app 2 lần/buổi), nguội máy vừa đủ |
| **Gap B** (Phiên 2 Ca N → Phiên 1 Ca N+1) | ≥ 3 tiếng | Tách biệt footprint thiết bị/IP giữa 2 nick khác nhau (chống co-location linking), tản nhiệt sâu, sạc pin |

## Timeline chuẩn 1 Ca (Ví dụ Ca Sáng)

```
06:00 ──► Phiên 1 (Feed + Follow 1) ──► 06:45
    │
    ▼ Gap A ~75-90'
08:00 ──► Phiên 2 (Feed + Follow 2 + Upload) ──► 08:50
    │
    ▼ Gap B ~3h10'
12:00 ──► Ca tiếp theo bắt đầu
```

## Quy tắc Switch Account (BẮT BUỘC)

| Sai (Cấm) | Đúng (Bắt buộc) |
|---|---|
| Switch ngay khi Ca trước xong (nick login rảnh 2-3h) | **Switch ở ĐẦU Ca sau** (phút đầu Phiên 1) |
| Login xong mới xoay IP | **Rotate IP TRƯỚC → Login SAU** |
| Pre-load nick hàng giờ | Warm-up 30-90s tại đầu Ca rồi chạy ngay |

## Rủi ro vi phạm Gap B / Switch sớm
1. **Co-location linking:** TikTok liên kết nick cũ & nick mới trên cùng device/IP hoạt động sát nhau → chết chùm.
2. **Session hijack signal:** Login IP A, chạy IP B (proxy xoay trong lúc idle) → checkpoint/shadowban.
3. **Thermal throttling:** Máy không nghỉ đủ → giật lag → miss element UI → fail rate tăng.

## Jitter bảo vệ (Đã cấu hình)
- **Jitter máy:** `MachineStartStaggerMs 2000,8000` + `RandomizeMachineOrder` (rải 80 máy trong 5-8 phút).
- **Jitter khởi động Ca:** Cron chạy `*/15` + state deduplicate → mỗi Ca spawn ngẫu nhiên trong ±15 phút quanh mốc giờ.