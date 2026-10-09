# Case 178: Fast Swipe Đa Tab (Following & Friends), Hiệu Chỉnh Tỉ Lệ Like Bù Trừ & Gỡ Dead-man Hook Cho Subagent

## 1. Bối cảnh & Hiện trạng cũ (Anti-Pattern)
- **Kẹt Deep Inspect 100% ở Following & Friends:** Cũ chỉ cho phép `Fast Swipe` trên tab `for-you` (`current_feed_type == FEED_TYPE_FOR_YOU`). Khi runner chuyển sang tab Following hoặc Friends, 100% video đều bị ép Deep Inspect (dump XML + screencap liên tục).
  - Hậu quả phần cứng: Farm 70–100 máy bị nghẽn UIAutomator, nóng CPU, tăng 300–800ms độ trễ thao tác trên các máy yếu.
  - Hậu quả thuật toán: Tab Friends bị gán cứng tỉ lệ Like 80% (10 video tim 8) và Following 50%. Pattern quá máy móc, thiếu nhiễu (noise), dễ bị TikTok gắn cờ bot cày tương tác.
- **Vấn đề Dead-man Hook (`guard_progress_supervisor.py`):**
  - Hook kiểm soát nhịp độ Coordinator chặn các session chạy quá 15 phút mà không có "Real State Change".
  - Tuy nhiên `REAL_STATE_CHANGES` chỉ liệt kê `patch`, `write_file`, lệnh build mà quên tính `delegate_task`. Khi Coordinator điều phối worker sửa code thì bị Dead-man hook chặn oan.

## 2. Thẩm định từ Sol 5.6 (`:20129`)
- **Khuyến nghị từ Sol:**
  - Mở Fast Swipe cho toàn bộ các tab:
    - For You: ~70-80% Fast Swipe / 20-30% Deep Inspect.
    - Following: ~50-60% Fast Swipe / 40-50% Deep Inspect.
    - Friends: ~30-40% Fast Swipe / 60-70% Deep Inspect.
  - Tỉ lệ Like thực tế trên tổng video sau bù trừ:
    - For You: 8–12%.
    - Following: 25–35% (thay vì 50%).
    - Friends: 40–45% (thay vì 80%).

## 3. Chi tiết thực thi Code Surgery
File: `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py`
1. **Gỡ bỏ ràng buộc ép cứng For You tại `is_fast_swipe_candidate`:**
   ```python
   # Cho phép Fast Swipe xen kẽ cho cả tab Đề xuất (For You), Following và Friends
   # để giảm tải CPU và tạo pattern tự nhiên.
   is_fast_swipe_candidate = (
       fast_swipe["enabled"]
       and not is_first_video
       and not is_last_video
       and not (is_feed_session and videos_until_tab_decision <= 0)
       and videos_until_deep_inspect > 0
   )
   ```
2. **Cân chỉnh lại `DEFAULT_FEED_LIKE_RATES` & Phân phối mềm liên tục:**
   ```python
   DEFAULT_FEED_LIKE_RATES = {
       FEED_TYPE_FOR_YOU: 8,
       FEED_TYPE_FOLLOWING: 35,
       FEED_TYPE_FRIENDS: 45,
   }
   
   # Trong _feed_like_rates():
   if raw is None:
       return {
           FEED_TYPE_FOR_YOU: random.randint(5, 12),
           FEED_TYPE_FOLLOWING: random.randint(25, 40),
           FEED_TYPE_FRIENDS: random.randint(35, 50),
       }
   ```
3. **Cập nhật Hook Dead-man Switch (`guard_progress_supervisor.py`):**
   - Bổ sung `"delegate_task"` vào `REAL_STATE_CHANGES` để không chặn lệnh điều phối worker subagent.

## 4. Kiểm chứng (Verification)
- Focused Pytest: `pytest -k "fast_swipe" python_runner/tests/test_feed_swipe_smoke.py -v` -> 4/4 passed (100%).
- Git commit: `b78a131` (`fix(feed): enable fast swipe for Following and Friends tabs with calibrated like rates`).
