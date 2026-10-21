# Quản Trị Cooldown Đếm Trùng, Cô Lập IP Breaker & Chống Phán Bừa Nick Buff Ngoài

## 1. Cơ Chế Chống Đếm Trùng & Lạm Phát Streak (Duplicate Cooldown Inflation Guard)
- **Hiện tượng:** Khi một tài khoản đang chịu cooldown (ví dụ bị phạt 1-3 ngày sau khi ăn nhả đuôi), nếu runner hoặc cron vô tình quét lại và gọi `set_follow_failed()`, code cũ sẽ cộng dồn `fail_streak` từ 1 lên 2, 3... và đẩy ngày phạt xa dần (tù chung thân dù nick chưa từng được thả ra chạy lại).
- **Quy tắc Byte-Level No-Op:**
  Ngay đầu hàm `set_follow_failed()`:
  ```python
  active_cooldown_dt = self.cooldown_until_at
  if active_cooldown_dt is not None and now_utc < active_cooldown_dt:
      return  # Byte-level no-op: không tăng fail_streak, không đổi timestamp, không ghi lại file
  ```
- **Quy tắc Chạm Trần (Ceiling Drop with used > 0):**
  Khi tài khoản đã follow thành công một số lượng nhất định (`used > 0`) rồi mới bị TikTok nhả ở lượt cuối:
  - `streak = max(1, curr_streak)` (giữ nguyên streak hiện tại, không phạt lũy tiến).
  - Cooldown cố định đúng 1 ngày (`today_end_local + timedelta(days=1)`) để xả cache phiên, tuyệt đối không phạt 3 - 15 ngày.

## 2. Cô Lập Ranh Giới: Account Drop vs IP Circuit Breaker
- **Bản chất kỹ thuật:** TikTok silent-drop là hạn mức tác vụ gắn theo phiên hoặc tài khoản (Account/Session rate limit), KHÔNG PHẢI proxy bị cháy IP.
- **Nguyên tắc cấm vạ lây:**
  - `set_follow_failed()` TUYỆT ĐỐI KHÔNG được gọi `trip_ip_breaker()`. Một nick bị nhả không được phép giật sập proxy làm tê liệt các slot/nick khác trên cùng máy.
- **Bảo toàn Startup Check:**
  - Ở entrypoint CLI (`run_follow.py`), vẫn giữ `check_ip_breaker(machine)` ở đầu phiên. Nếu proxy của máy đã bị sập từ trước (do lỗi kết nối mạng thực tế), runner thoát an toàn với:
    ```python
    status = "CIRCUIT_BREAKER_SKIPPED"
    failed = False  # Không coi là lỗi vận hành của account
    exit_code = 0   # Orchestrator ghi nhận hoàn thành an toàn
    ```

## 3. Chống Phán Bừa / Ảo Giác Về Nick Buff Ngoài (`priority_targets.txt`)
- **Tình huống:** File `config/priority_targets.txt` chứa nick ngoài farm (ví dụ `@bangtam2311`) để dàn farm buff chéo view/follow.
- **Bẫy suy diễn của AI:**
  - Tra cứu DB `tiktok_tracker.db` thấy bảng `snapshots` có 0 dòng cho `@bangtam2311` -> Vội kết luận "nick chết / không tồn tại nên bot search lỗi gây nhả follow hàng loạt".
- **Sự thật hiện trường:**
  1. Nick ngoài farm không nằm trong diện crawl nội bộ nên snapshot = 0 là HOÀN TOÀN BÌNH THƯỜNG.
  2. Trong `mode1_search_follow.py`, khi search không ra nick hoặc ID không khớp, kết quả là `outcome == "skipped"` (`res.failed_ids.append(uid)`), TUYỆT ĐỐI KHÔNG GỌI `set_follow_failed()`, KHÔNG PHẠT STREAK.
  3. Kiểm tra file state: Nếu `failed: {}` rỗng thì chứng minh tài khoản chưa từng fail bấm nút bất kỳ nick nào. Không được đổ lỗi cho target buff ngoài.

## 4. Đồng Bộ Hiển Thị Watchdog Cho Máy Ăn Nhả Đuôi (Ceiling Drop)
- Trong `feed_session_watchdog.py`:
  - Máy có `len(flist) > 0` dù kết thúc bằng `status == "FOLLOW_FAILED"` thì BẮT BUỘC phải được ghi nhận vào `fl_success` để ghi nhận các lượt follow thành công đã đạt được trước khi chạm trần.
  - Đồng thời vẫn ghi nhận vào `fl_released` kèm số lượt `(MN: X lượt)`.
  - Mẫu số ứng viên tính %: `total_fl_candidates = len(set(fl_success) | set(fl_released))`.
  - Chấm dứt hiện tượng báo cáo vô lý: *"Follow chéo 3 lượt - Thành công: 0 máy"*.
