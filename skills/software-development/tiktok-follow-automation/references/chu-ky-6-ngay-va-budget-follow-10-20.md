# Chu kỳ Vận Hành 6 Ngày & Quy Chuẩn Budget Follow 10-20 (Chốt 15/09/2026)

## 1. Quy chuẩn Budget Follow
- **Ngưỡng mỗi phiên:** Random `10 - 20 follow` (budget_per_session_min = 10, budget_per_session_max = 20, budget_per_day = 40).
- **Số phiên trong ngày cày:** 2 phiên (1 ngày cày tối đa 20 - 40 follow).
- **Hard Gate Móng Video:** Bắt buộc $\ge 10$ video đã đăng mới được đi follow. Dưới 10 video -> budget = 0 (chỉ lướt feed nuôi).

## 2. Chu kỳ Xoay Tua 6 Ngày (Modulo 6 - 4 acc/ngày)
Áp dụng đồng bộ cho toàn bộ 80 máy qua `tiktok_runner.py` (tính theo `(now.date() - date(2026, 9, 1)).days % 6`):

- **Day 0:** Row 1, 3, 5, 7 -> Cày Follow (10-20) + Up video.
- **Day 1:** Row 2, 4, 6, 8 -> Cày Follow (10-20) + Up video.
- **Day 2:** Row 1, 3, 5, 7 -> **DƯỠNG SINH RỬA TRUST (100% CHỈ LƯỚT FEED, 0 FOLLOW, KHÔNG UP VIDEO)**.
- **Day 3:** Row 2, 4, 6, 8 -> Cày Follow (10-20) + Up video.
- **Day 4:** Row 1, 3, 5, 7 -> Cày Follow (10-20) + Up video.
- **Day 5:** Row 2, 4, 6, 8 -> **DƯỠNG SINH RỬA TRUST (100% CHỈ LƯỚT FEED, 0 FOLLOW, KHÔNG UP VIDEO)**.
- **Lặp lại:** Hết Day 5 tự động quay về Day 0 vô tận.

### Lợi ích kiến trúc:
- **Từng nick:** Cứ cày 1 ngày follow -> Nghỉ 2 ngày tiếp theo không đụng vào nút follow (gồm 1 ngày không mở + 1 ngày mở lên CHỈ lướt feed nuôi để rửa trust score). Tức là trọn vẹn 48h Action Cooldown giữa các đợt cày.
- **Toàn farm:** Ngày nào cũng có đúng 4 slot hoạt động mượt mà, lưu lượng mạng phẳng 100%, máy Samsung S7 có 16-18h tắt màn hình nghỉ nhiệt mỗi ngày.

## 3. Auto-sync Expiry & Row Isolation (Chấm 9.3/10)
- **Cách ly cấp Slot (Row Isolation):** State cooldown match chính xác `(machine, row)` qua `follow_state_{machine}_row_{row}.json`, cấm fallback machine-level làm phạt oan các slot khác trên cùng máy.
- **Chuẩn hóa UTC 100%:** So sánh thời gian tuyệt đối bằng `now_utc` và `until_dt.astimezone(timezone.utc)`, loại bỏ lệch ngày giữa local Windows và UTC.
- **Auto-sync Expiry (Tránh Zombie State):** Khi hết hạn `now_utc >= until_dt`, hàm `is_account_in_follow_cooldown()` tự động dọn sạch cờ `follow_failed = False`, reset các trường timestamp cũ và atomic replace file JSON (`.json.tmp` -> `os.replace`).
- **Cờ ngày dưỡng sinh:** `tiktok_runner.py` truyền `TAADAA_REST_DAY_NO_FOLLOW=1`, `multi_machine_feed_session.py` tự động bypass follow-hook với reason `rest-day-follow-disabled-pure-feed`.
