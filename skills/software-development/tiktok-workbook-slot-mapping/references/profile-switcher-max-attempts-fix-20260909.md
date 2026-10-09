# Profile Switcher MAX_ATTEMPTS Fix — 2026-09-09

## Triệu chứng

Ca nuôi Row 7 đêm 09/09 báo 2 cụm lỗi:
- **Cụm 1 (60/80 máy, 75%):** `account row 7 is empty (no username) for <device>, skipping`
- **Cụm 2 (15/80 máy, 18.8%):** `profile username still mismatched after switch`

## Cụm 1 — BÌNH THƯỜNG, không phải bug

Thiết kế có trong `eight-slot-incubator-and-night-chain-feed-fallback.md`:
> Máy nào chỉ mới có 6 hoặc 7 acc, khi chạy ca Row 7/8 thì account_id rỗng → runner tự động skip an toàn

Phần lớn farm (60 máy) chưa reg được nick Slot 7 → Row 7 trống → skip đúng. Không can thiệp.

## Cụm 2 — LỖI THỰC, đã fix

**Root cause:** `PROFILE_SWITCH_MAX_ATTEMPTS = 2` (dòng 625, `python_runner/flows/feed_swipe_smoke.py`) không đủ cho nick Slot 7/8 mới reg.

Từ log M3 (serial `5ade3fd615`):
- Nick cần chạy: `brifeqme954` (Slot 7)
- Nick đang hiển thị: `Kylarwpw` (Slot khác)
- Runner tìm thấy `brifeqme954` trong switcher, tap 2 lần nhưng profile vẫn không đổi
- Auto-reconcile kích hoạt `reconcile_tiktok_accounts.py` — timeout 900s → thất bại

Chuỗi events per attempt:
1. Tap switch_anchor (display name) → mở Account Switcher modal
2. Tìm `brifeqme954` trong switcher (thành công: `content_desc="brifeqme954"`)  
3. Tap nick đó → switcher đóng
4. Navigate về profile → đọc identity → vẫn thấy nick khác
5. Lần 2 lặp lại → vẫn thất bại → `mismatched after switch`

Nguyên nhân sâu: Nick mới reg lần đầu chạy feed, TikToggle chưa flush session/cookie → cần thêm lần retry thứ 3 để settle.

**Fix:** Tăng `PROFILE_SWITCH_MAX_ATTEMPTS = 2` → `= 3`

```python
# python_runner/flows/feed_swipe_smoke.py, dòng 625
PROFILE_SWITCH_MAX_ATTEMPTS = 3  # was 2 — raised 2026-09-09 for Slot 7/8 new-reg nicks
```

**Commit:** `fix: raise PROFILE_SWITCH_MAX_ATTEMPTS 2→3 to fix profile switcher mismatch on Row 7`

## Phân loại nhanh khi nhận batch alert Row 7/8

| Signature | Tỷ lệ | Đánh giá | Hành động |
|-----------|--------|----------|------------|
| `account row 7 is empty (no username)` | 60-75% fleet | ✅ Normal | Bỏ qua |
| `profile username still mismatched after switch` | 15-20% fleet | ⚠️ Bug | Check MAX_ATTEMPTS, kiểm tra nick mới reg |

## File liên quan

- `python_runner/flows/feed_swipe_smoke.py` dòng 625: `PROFILE_SWITCH_MAX_ATTEMPTS`
- `python_runner/flows/feed_swipe_smoke.py` hàm `verify_and_switch_profile()` (~dòng 16642)  
- `automation-core/src/automation_core/tiktok/account_switcher.py` — `find_exact_account`, `verify_selected_account`
