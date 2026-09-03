# Nối Follow vào Feed Session — contract (chốt 2026-08-16)

Plan: `D:\Taadaa\tiktok-luot nuoi acc\.hermes\plans\2026-08-15_follow-integration-from-follow-repo.md`

## Cấu trúc 1 acc/ngày (3 phiên) — chốt

| Phiên | Feed (lướt) | Organic follow | Cross follow (gọi runner) |
|---|---|---|---|
| S1 | 15–30 video | ~10–12% | random 5–10 |
| S2 | 15–30 video | ~10–12% | random 5–10 |
| S3 | 15–30 video | ~10–12% | random 5–10 |
| **Ngày** | 45–90 video | ~5–10 | ~15–30 (TB ~22) |

- Gap giữa phiên: 60–90' (giữ nguyên account-block hiện tại)
- 1 phiên lướt thật ≈ **11–12 phút** (đo thật pilot 9C.2 máy 5/6, 2026-08-16 — nhanh hơn
  ước lượng 12–24' cũ); 1 máy 3 acc ≈ ~100 phút/ngày = **15–20% budget 9–13.5h**
- **User chốt: KHÔNG tăng phiên dù thừa time** — 6 phiên/acc/ngày (~66') khớp TB người
  dùng thật (~95'/ngày); tăng phiên không tăng follow vì `budget_per_day: 30` là trần.
  Giữ nguyên 15–30 video (lướt dài = tự nhiên).

## Hook gọi follow cuối phiên (subprocess, không import)

Vị trí: cuối feed session, sau khi feed success/degraded → trong
`multi_machine_feed_session.py` sau `child_result = _result_from_child_context(...)`
(~dòng 909), khi `child_result.final_status in {"success", "degraded"}`:

```bash
python "D:\Taadaa\tiktok-follow\follow_runner\run_follow.py" \
  --machine N --config "D:\Taadaa\tiktok-follow\follow_runner\config.example.yaml" \
  --account-row-index R
```

- `N` = máy vừa lướt, `R` = account row index (đã switcher nick xong — follow runner
  chỉ verify identity, không đổi nick)
- **UID target = random trong toàn bộ cột ID hợp lệ của `taikhoan_run_safe.xlsx`**
  (follow runner đọc workbook, không cần truyền)
- Budget 5–10/phiên nằm trong config follow — repo nuôi acc KHÔNG truyền
- **Gate sensitive:** feed fail vì login/OTP/2FA/captcha/security → KHÔNG gọi follow
  (account-level, follow vô ích); fail không-sensitive (kẹt UI/ATX/capture) → VẪN gọi
  (follow runner tự force-stop + relaunch app sạch)
- Đọc exit code (0=OK, 1=lỗi) + stdout `FOLLOW_RESULT <json>` → ghi vào kết quả phiên
- **FOLLOW_FAILED** (TikTok không nhận follow) → dừng phiên đó (follow runner tự xử lý,
  repo này chỉ đọc exit code)

## Ghi follower MỖI PHIÊN (user đổi 2026-08-16 — không đợi cuối ngày)

- Sau mỗi phiên feed xong → gọi tracker ghi state JSON per-machine ngay
  (`record_follower_in_state` bên follow repo)
- State JSON riêng per-machine (không race khi nhiều máy song song)
- Export Excel gom vẫn là `python -m follow_runner.export_follower_tracking
  --state-dir runs/state --output ...` — nhưng chạy sau mỗi phiên hoặc 1 lần/ngày tùy
  cần (user: "cuối ngày ms ghi trễ quá k xong mỗi phiên thì ghi luôn")

## KHÔNG được làm

- KHÔNG import chéo `follow_runner` (2 PYTHONPATH/core khác nhau)
- KHÔNG sửa code follow repo (đã commit `a74019e`)
- KHÔNG thêm cột vào `taikhoan_run_safe.xlsx` (sync assert đúng 3 cột — vỡ)
- KHÔNG đọc credential/workbook nhạy cảm

## Lịch: 2 phiên → 3 phiên/acc/ngày

- Hiện tại account-block = 3 block × 2 phiên (6 phiên/ngày/máy, 3 acc)
- Cần: 3 phiên/acc/ngày (9 phiên/ngày/máy, vẫn 3 acc)
- Sửa picker sinh 3 phiên/acc (giữ pair-gap 60–90')

## Mode 1 vs Mode 2 (đã phân tích 2026-08-16)

- **Mode 1 (search-follow):** search UID trong list → follow trực tiếp = **follow chéo
  nội bộ** (giữa nick mình) — nguồn follower CHÍNH
- **Mode 2 (follow-followers):** search seed → tab Follower → follow follower của người
  đó = follow người LẠ (giống organic) — ngụy trang tốt hơn
- Khuyến nghị: `mode: "both"` — Mode 1 chính (follow chéo), Mode 2 phụ (ngụy trang +
  tăng organic). Nếu tối giản an toàn: Mode 1 đủ (nick đã có organic từ Đề xuất)

## TDD bắt buộc

- Task nào cũng viết test trước (RED → GREEN), full suite xanh trước commit
- Sau khi xong: canary 1 máy (feed 3 phiên + follow gắn cuối phiên + export) trước farm
