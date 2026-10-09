# Case UI-47: Follow-Timeout, 120s Soft Deadline Budgeting, and Transition Guards

## Triệu chứng & Bối cảnh

- **Triệu chứng:** Farm Alert `• Script: tiktok-follow • Triệu chứng: follow-timeout` kèm hiện trường TikTok dừng ở Feed Đề xuất (`SplashActivity`).
- **Bối cảnh:** Parent feed runner (`multi_machine_feed_session.py` -> `_run_follow_hook`) kích hoạt `follow_runner` qua subprocess với hard deadline 1200.0s (20 phút).
- Khi tiến trình con chạy quá 1200.0s mà chưa kết thúc, `subprocess.TimeoutExpired` được kích hoạt ở tiến trình cha, kill tiến trình con và phát cảnh báo đỏ `GIỮ HIỆN TRƯỜNG FOLLOW TIMEOUT`.

---

## Root Cause Phân tích

1. **Ngưỡng Dự trữ Thời gian Quá Hẹp (60s vs 120s):**
   - Trong `FollowEngine.has_time_for_next_action(reserve_seconds=60.0)`, mức dự trữ cũ là 60.0s.
   - Trên thiết bị thực tế, một chu kỳ thao tác (Search UID/Anchor + typing + wait results + Users tab fallback + profile load + Path B reload verify + inter-follow delay) có thể kéo dài 60–90s.
   - Khi phiên chỉ còn 61–89s, runner vẫn đánh giá `has_time_for_next_action() == True` và bắt đầu một action mới. Action này kéo dài vượt mốc 1200.0s, dẫn đến bị tiến trình cha kill bằng `TimeoutExpired`.

2. **Thiếu Chốt Chặn Chuyển Tiếp Giữa Mode 2 và Mode 1:**
   - Trong `FollowEngine.run_session()`, khi chạy hybrid mode (`both`), Mode 2 (follow followers của anchor) chạy trước.
   - Sau khi Mode 2 kết thúc và còn dư budget, `run_session()` chuyển sang Mode 1 (`run_mode1`) mà không kiểm tra `has_time_for_next_action()`.
   - Nếu Mode 2 đã tiêu tốn gần hết quỹ thời gian (ví dụ 1050s/1200s), Mode 1 bắt đầu duyệt search UID và bị timeout giữa chừng.

3. **Recovery Ladder Cascade Trong Mode 2:**
   - Khi `_open_following_tab` gặp lỗi, `mode2_follow_followers.py` thực hiện recovery ladder (`engine.recover_ui()`, `_back_to_feed()`, `_open_following_tab` lần 2).
   - Mỗi bước trong ladder có thể mất 30–60s. Nếu không có soft deadline guard trước các nhánh retry, runner sẽ kẹt trong chuỗi recovery cho đến khi bị parent kill cứng.

---

## Giải Pháp Chuẩn (Case UI-47)

1. **Nâng Ngưỡng Dự trữ Thời gian Lên 120s:**
   - `FollowEngine.has_time_for_next_action(reserve_seconds: float = 120.0)`: Đặt mặc định 120.0s (2 phút an toàn).
   - Mọi vòng lặp duyệt UID (Mode 1), duyệt anchor (Mode 2), và duyệt row follower (Mode 2) đều gọi `has_time_for_next_action(reserve_seconds=120.0)`. Khi còn < 120s, runner lập tức dừng vòng lặp, log info và trả về `status="OK"`, `failed=False` cùng toàn bộ danh sách UID đã follow thành công.

2. **Chốt Chặn Chuyển Tiếp Mode 2 ➔ Mode 1:**
   ```python
   if mode in ("1", "both") and res.status == STATE_OK:
       if callable(getattr(self, "has_time_for_next_action", None)) and not self.has_time_for_next_action(reserve_seconds=120.0):
           logger.info("Session deadline approaching, skipping mode1 after mode2 with %d followed accounts", len(res.followed))
       else:
           from .mode1_search_follow import run_mode1
           res = run_mode1(self, res)
   ```

3. **Soft Deadline Guards Trong Recovery Ladder:**
   - Trong `mode2_follow_followers.py`: Kiểm tra `has_time_for_next_action(reserve_seconds=120.0)` trước khi gọi `engine.recover_ui()` và trước khi retry `_open_following_tab(engine, uid)`.
   - Trong `mode1_search_follow.py`: Kiểm tra trước khi retry `_nav_search` và giới hạn `max_consecutive_not_found = 5`.

4. **Unit Test Phủ Kín:**
   - `test_run_session_skips_mode1_when_soft_deadline_approaching`
   - `test_run_mode1_breaks_gracefully_on_soft_deadline`
   - `test_run_mode2_breaks_gracefully_on_soft_deadline`
   - `test_run_mode1_breaks_on_max_consecutive_not_found`
