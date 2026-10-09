# Chu kỳ Vận Hành 6 Ngày & Quy Chuẩn Ngày Dưỡng Sinh Rửa Trust (Chốt 15/09/2026)

## 1. Chu kỳ Xoay Tua 6 Ngày (Modulo 6 - 4 acc/ngày)
Áp dụng đồng bộ cho toàn bộ 80 máy qua `tiktok_runner.py` (tính theo `(now.date() - date(2026, 9, 1)).days % 6`):

- **Day 0:** Row 1, 3, 5, 7 -> Cày Follow (10-20) + Up video.
- **Day 1:** Row 2, 4, 6, 8 -> Cày Follow (10-20) + Up video.
- **Day 2:** Row 1, 3, 5, 7 -> **DƯỠNG SINH RỬA TRUST (100% CHỈ LƯỚT FEED, 0 FOLLOW, KHÔNG UP VIDEO)**.
- **Day 3:** Row 2, 4, 6, 8 -> Cày Follow (10-20) + Up video.
- **Day 4:** Row 1, 3, 5, 7 -> Cày Follow (10-20) + Up video.
- **Day 5:** Row 2, 4, 6, 8 -> **DƯỠNG SINH RỬA TRUST (100% CHỈ LƯỚT FEED, 0 FOLLOW, KHÔNG UP VIDEO)**.
- **Lặp lại:** Hết Day 5 tự động quay về Day 0 vô tận.

## 2. Bản chất Ngày Dưỡng Sinh (Rest Day)
- **Từng nick:** Cứ cày 1 ngày follow -> Nghỉ 2 ngày tiếp theo không đụng vào nút follow (gồm 1 ngày không mở + 1 ngày mở lên CHỈ lướt feed nuôi để rửa trust score). Tức là trọn vẹn 48h Action Cooldown giữa các đợt cày.
- **Toàn farm:** Ngày nào cũng có đúng 4 slot hoạt động mượt mà, lưu lượng mạng phẳng 100%, máy Samsung S7 có 16-18h tắt màn hình nghỉ nhiệt mỗi ngày.
- **Quy tắc Clear Cache:** Dọn dẹp cuốn chiếu hoặc cuối ngày (ca đêm 04:00) để chống phình bộ nhớ S7, tuyệt đối KHÔNG clear cache trước mỗi lần switch nick để tránh tạo signature bot lặp lại.

## 3. Cơ chế Kỹ thuật Tự Động
- **Cờ ngày dưỡng sinh:** `tiktok_runner.py` truyền `TAADAA_REST_DAY_NO_FOLLOW=1` và tắt cờ `-AllowUploadHook`, `multi_machine_feed_session.py` tự động bypass follow-hook với reason `rest-day-follow-disabled-pure-feed`.
- **Auto-sync Expiry & Row Isolation (Chấm 9.3/10):**
  - State cooldown match chính xác `(machine, row)` qua `follow_state_{machine}_row_{row}.json`, cấm fallback machine-level.
  - So sánh thời gian tuyệt đối bằng `now_utc` và `until_dt.astimezone(timezone.utc)`.
  - Khi hết hạn `now_utc >= until_dt`, hàm `is_account_in_follow_cooldown()` tự động dọn sạch cờ `follow_failed = False`, reset các trường timestamp cũ và atomic replace file JSON (`.json.tmp` -> `os.replace`).
