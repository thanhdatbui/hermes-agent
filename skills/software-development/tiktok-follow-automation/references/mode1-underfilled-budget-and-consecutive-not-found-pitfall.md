# Pitfall: Mode 1 Underfilled Budget, Double Randomization, and Consecutive Not Found

## 1. Triệu chứng & Hiện tượng
- Nick chạy thành công, không bị nhả follow (`follow_failed: false`), nhưng số lượt follow trong phiên chỉ đạt 3–8 lượt (kém xa mức budget thiết kế 10–20/phiên hay trần 40/ngày).
- Mode 2 kết thúc sớm do cạn anchor hoặc nick farm trong following list của anchor, nhưng khi chuyển sang Mode 1 chạy bù thì Mode 1 vẫn không lấp đầy quota phiên.

## 2. Nguyên nhân cốt lõi trong Codebase

### A. Dual Gate (video_count & account_age_days)
- Với nick chưa đủ 10 video (`video_count < 10`), hàm `FollowState.session_budget()` tự động ép trần budget xuống `randint(3, 5)` lượt/phiên (giai đoạn mồi nhẹ).
- Nếu nick chỉ có 8-9 video, việc chỉ follow 3-5 lượt là **đúng theo thiết kế Dual Gate**, không phải lỗi thiếu budget.

### B. Mode 1 dừng sớm do `consecutive_not_found >= 5`
- Trong `mode1_search_follow.py`, vòng lặp duyệt `uids` có điều kiện ngắt:
  ```python
  if consecutive_not_found >= max_consecutive_not_found: # default = 5
      logger.warning("run_mode1: reached %d consecutive not-found UIDs, completing session gracefully", consecutive_not_found)
      break
  ```
- Nếu trong danh sách UID có 5 UID liên tiếp bị xoá, đổi handle, hoặc search không ra profile, Mode 1 sẽ `break` toàn bộ vòng lặp ngay lập tức thay vì duyệt tiếp các UID hợp lệ còn lại trong pool, khiến phiên bị dừng non (underfilled).

### C. Quota phiên bị random lại 2 lần (Double Randomization)
- `run_mode2()` gọi `state.session_budget()` để xác định quota phiên cho Mode 2.
- Khi fallback sang Mode 1 (`run_mode1()`), code lại gọi tiếp:
  ```python
  budget = max(0, min(state.session_budget(...), state.budget_remaining()) - len(res.followed))
  ```
- `session_budget()` thực hiện `random.randint(10, 20)`. Việc gọi lại lần thứ 2 khiến target budget của phiên bị nhảy sang một con số ngẫu nhiên mới, làm lệch pha accounting giữa Mode 2 và Mode 1.

## 3. Kỷ luật điều phối & Phản hồi
- Tuyệt đối không lấp liếm bằng các nick bị nhả follow khi người dùng đang hỏi về nick chạy thực tế.
- Bóc tách rõ: Nick bị ép budget theo gate (do thiếu video/tuổi) vs. Nick bị dừng non do cơ chế ngắt 5 not-found / random quota.
