# Chu kỳ Vận Hành 6 Ngày, Budget Follow 10-20 & Opportunistic Upload (Chốt 15/09/2026)

## 1. Nâng Budget Follow
- **Budget phiên:** 10 – 20 follow / phiên (random trong dải `[10, 20]`, default: 20).
- **Trần ngày:** 40 follow / ngày (`budget_per_day = 40`).
- **Gate điều kiện:** Bắt buộc acc có $\ge 10$ video đã đăng mới được đi follow. Dưới 10 video -> budget = 0 (chỉ lướt feed nuôi mồi ~30 ngày đầu).

---

## 2. Chu Kỳ Xoay Tua 6 Ngày (Modulo 6) Cho 80 Máy
Áp dụng cho toàn bộ 80 máy qua `tiktok_runner.py` với mốc epoch `2026-09-01`:
`day_cycle = (now.date() - date(2026, 9, 1)).days % 6`

- **Day 0 & Day 4:** Nhóm lẻ (Row 1, 3, 5, 7) -> **Cày Follow (10-20) + Upload**.
- **Day 1 & Day 3:** Nhóm chẵn (Row 2, 4, 6, 8) -> **Cày Follow (10-20) + Upload**.
- **Day 2:** Nhóm lẻ (Row 1, 3, 5, 7) -> **DƯỠNG SINH RỬA TRUST (100% CHỈ LƯỚT FEED, 0 FOLLOW, KHÔNG UP)**.
- **Day 5:** Nhóm chẵn (Row 2, 4, 6, 8) -> **DƯỠNG SINH RỬA TRUST (100% CHỈ LƯỚT FEED, 0 FOLLOW, KHÔNG UP)**.

**Ý nghĩa:**
- Từng nick sau khi cày 1 ngày sẽ có **trọn vẹn 48h Action Cooldown** để phục hồi trust score.
- Toàn farm ngày nào cũng có đúng 4 slot hoạt động mượt mà, lưu lượng mạng/proxy phẳng 100%.

---

## 3. Cơ Chế Opportunistic Upload (Đăng Video Cả Phiên 1 & 2)
- Thay vì chỉ cho upload ở Phiên 2 (dễ trượt nhịp lên tới 6–8 ngày nếu phiên 2 lỗi), kích hoạt cờ `-AllowUploadHook` cho cả Phiên 1 & 2 (vào ngày cày, NOT rest_day).
- Sổ cái liên tiến trình `shift_upload_history.json` khóa chặn: Phiên 1 đăng thành công thì Phiên 2 tự động bỏ qua (`already_uploaded_in_shift`); nếu Phiên 1 lỗi thì Phiên 2 tự động đăng bù.
- Ngày dưỡng sinh (`is_rest_day`): Tắt cờ upload 100%.

---

## 4. Vá State Cooldown: Pure Read & Chuẩn UTC
- Hàm `is_account_in_follow_cooldown()` là pure read-only, không mutate ghi đè file JSON khi đọc để chống race condition.
- Chuẩn hóa 100% theo UTC, match chính xác cặp `(machine, row)`, loại bỏ fallback cấp máy `follow_state_{machine}.json`.
- Khi `cooldown_until_at` hết hạn, không return ngay mà tiếp tục rơi xuống kiểm tra các cờ ngày (`cooldown_until_date`, `follow_failed_date`, `follow_failed`) để tránh false negative.
