# Video Count Gate Policy (Updated)

- **Video Gate Requirement**:
  - Tài khoản phải có **tối thiểu 10 video đã đăng** (`video_count >= 10`) mới được cấp budget follow trong phiên (`session_budget`).
  - Khi `video_count < 10` hoặc `video_count is None` / chưa có cột thống kê -> return budget = 0 (tuyệt đối không chạy follow).
  - Áp dụng đồng bộ tại `FollowState.session_budget()` và filter anchor/list tại `FollowEngine` (`row_video_counts.get(...) >= 10`).
  - Đã cập nhật toàn bộ test suite trong `follow_runner/tests/test_follow_state.py` (28/28 tests passed).
