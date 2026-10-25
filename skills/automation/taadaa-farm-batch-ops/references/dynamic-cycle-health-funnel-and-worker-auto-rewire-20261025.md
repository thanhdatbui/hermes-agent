# Tri thức Vận hành Ca Nuôi TikTok Dynamic & Auto-Rewire Worker

## 1. Cơ Chế Bốc Nick Dynamic Tuần Tự (Chống Bỏ Đói)
- **Ranh giới Pool cố định:**
  - Ca 1 (Sáng: 06:00 & 08:00): Pool `{Row 1, Row 2, Row 7}`
  - Ca 2 (Trưa: 12:00 & 14:00): Pool `{Row 3, Row 4, Row 8}`
  - Ca 3 (Tối: 18:00 & 20:00): Lượt 1 & 2 chạy `{Row 5, Row 6}`. Lượt 3 chạy Row Động (Dynamic Nurture).
- **Thứ bậc Phễu Sức Khỏe 6 Tầng (đọc từ `follow_state` & `tiktok_tracker.db`):**
  1. Rank 1: Khỏe (`healthy` / `graduated=True`)
  2. Rank 2: Đề xuất (`is_account_boosted=True`)
  3. Rank 3: Hồi phục 2 (`probation_clean_days >= 1`)
  4. Rank 4: Hồi phục 1 (`probation_clean_days == 0` và `fail_streak > 0`)
  5. Rank 5: Nhả follow (`is_in_cooldown=True` hoặc `cooldown_until_date`)
  6. Rank 6: Yếu / Non (ít video nhất, nick mới)
- **Quy tắc Sống Còn (Anti-Starvation):**
  - Trong Pool của ca, máy bốc nick có thứ hạng tốt nhất chưa chạy trong chu kỳ.
  - **Nick chạy bị LỖI (rớt mạng, timeout, crash):** Ca/ngày tiếp theo máy TIẾP TỤC BỐC LẠI NICK ĐÓ cho đến khi thành công ít nhất 1 lần, tuyệt đối không nhảy nick làm mất lượt nick xịn.
  - Chỉ khi nick chạy THÀNH CÔNG (SUCCESS) mới ghi nhận hoàn thành và chuyển sang nick tiếp theo.
  - Chạy hết pool của ca mới tự động reset danh sách `used` để bắt đầu vòng tuần tự mới.

## 2. Hai Tầng Cooldown Tách Biệt: Feed vs Follow
- **Nuôi Feed & Đăng Video:** Hoàn toàn tự do theo Ca, KHÔNG áp dụng cooldown 48h.
- **Quyền Đi Follow (Độc quyền dính Cooldown):**
  - **Tầng Farm:** Cooldown 48h tự nhiên giữa các lần follow thành công.
  - **Tầng Account (Streak Riêng):** Nick dính án phạt nhả follow bắt buộc tuân thủ đúng streak riêng của nick đó (Streak 1: nghỉ 1 ngày; Streak 2-3: nghỉ 3 ngày; Streak 4+: nghỉ 15 ngày). Hết 48h toàn farm nhưng streak riêng chưa hết thì VẪN TẮT FOLLOW.
  - **Row Động Ca 3:** Tự động TẮT FOLLOW (`reason: dynamic-nurture-row-follow-disabled`), chỉ thuần túy lướt feed và up clip để tăng Trust cho kênh.

## 3. Cơ Chế Auto-Rewire Worker (Chống Nhảy Cóc Sang Claude)
- **Thang Luân Chuyển Bắt Buộc:**
  `Sol Worker (Tier 1)` -> `Agy CLI (Tier 2)` -> `Haiku / Claude (Tier 3)`
- **Auto-Rewire trong `haiku_worker.py`:**
  - Nếu Coordinator cố tình hoặc lỡ tay gọi trực tiếp `python D:/Taadaa/tools/haiku_worker.py` mà KHÔNG có cờ `--on-demand` từ User hoặc cờ `--from-dispatch` từ thang luân chuyển:
  - Script TỰ ĐỘNG BẺ LÁI (REWIRE) 100% sang `D:/Taadaa/tools/dispatch_worker.py` để ép chạy Sol Worker trước.
  - Tuyệt đối cấm nhảy cóc sang Claude khi chưa có audit receipt chứng minh Sol và Agy đều đã thất bại.

## 4. Cơ Chế Two-Phase Commit trong Feed Session Watchdog
- **Lỗi At-Most-Once cũ:** Watchdog ghi nhận session đã report TRƯỚC khi in ra stdout; khi Hermes gặp lỗi mạng Telegram (`httpx.ProxyError`) thì report bị mất vĩnh viễn vì các lần chạy sau bỏ qua.
- **Cơ chế 2 pha mới:**
  1. Pha 1: Lưu vào `pending_delivery` (chưa tick `reported_sessions`) rồi mới xuất stdout.
  2. Pha 2: Lần chạy sau kiểm tra `jobs.json` của Hermes:
     - Nếu có `last_delivery_error`: Re-emit ngay nội dung cũ từ `pending_delivery` để Hermes retry phát tin.
     - Chỉ khi `last_delivery_error is None`: Mới chính thức commit session vào `reported_sessions` an toàn.
