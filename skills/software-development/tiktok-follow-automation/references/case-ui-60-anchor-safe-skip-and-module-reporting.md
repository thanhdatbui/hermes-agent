# Case UI-60: Anchor Video Selector Safe-Skip & Per-Module Follow Reporting

## Hiện trường sự cố (Sự cố Máy 31 `@orlanffhm61` - Anchor `@phannhung1710`)
- **Triệu chứng**: Bot tìm kiếm anchor `@phannhung1710`, vào profile, cuộn lưới video nhưng không mở video nào mà thoát app ra HOME; log ghi `status: "MANUAL_REVIEW"`, `reason: "anchor @phannhung1710 không có video — back ra bỏ qua"`.
- **Nguyên nhân gốc**:
  1. Selector `_open_anchor_first_video` chỉ kiểm tra các resource-id cũ (`cover`, `tv_play_count`, `exx`, `aweme`). Trên TikTok 46.8.3, resource-id bị obfuscate / đổi định dạng khiến danh sách thumbnail rỗng dù trang có video.
  2. Khi không nhận diện được video, Mode 2 gán `res.status = "MANUAL_REVIEW"`, `failed = True` và thoát app làm đứng máy thay vì cho Mode 1 chạy bù.
  3. Báo cáo ca chạy (`FOLLOW_RESULT` payload) và báo cáo tổng kết watchdog Telegram (`feed_session_watchdog.py`) chỉ tính tổng follow chung, không phân tách Module 1 (feed/search) và Module 2 (anchor followers). Người vận hành không nhận diện được phiên fail hay thiếu follow là do bước vào video anchor hay do lỗi khác.

## Quy tắc xử lý chuẩn (Case UI-60 Invariant)
1. **Safe-Skip khi Anchor không có video**:
   - Khi `_last_anchor_follow_outcome == "no_video"`, ghi nhận `res.details["mode2_skip_reason"] = f"anchor @{uid} không có video"`.
   - CẤM TUYỆT ĐỐI gán `MANUAL_REVIEW` làm đứng phiên. Giữ `status = "OK"` để fall-through cho Module 1 (search follow) chạy tiếp bù đủ chỉ tiêu.
   - Anchor UIDs lọc `>= 5` video từ workbook `taikhoan_run_safe.xlsx` để hạn chế tối đa việc chọn nhầm anchor rác/ít video.
2. **Tách bạch số lượng follow từng Module (Runner + Watchdog Telegram)**:
   - `SessionResult`: Thêm `mode1_followed: list[str]` và `mode2_followed: list[str]`.
   - `FOLLOW_RESULT` JSON payload: `details["mode1_followed_count"]` và `details["mode2_followed_count"]`.
   - `feed_session_watchdog.py`: Bóc tách `mode1_followed_count` / `mode2_followed_count` trong `follow_result.json`, merge qua `merge_follow_result` và định dạng dòng Telegram summary:
     `• Follow chéo ({total} lượt follow) [Module 2 (Anchor): {m2} | Module 1 (Bù): {m1}]:`
   - Giúp người vận hành nhìn báo cáo biết ngay Mode 2 follow được bao nhiêu, nếu bằng 0 thì nhận diện ngay là do search/video anchor hay do nguyên nhân khác.
3. **Fail-Safe Cleanup & Dirty Flag Preservation (UI-59 Alignment)**:
   - Trong `run_follow.py` (`cleanup_after_result`): Chỉ normalize `failed = False` khi `is_strict_clean == True`.
   - Nếu là dirty failure (`failed = True` hoặc `missing/None`), BẮT BUỘC bảo toàn `failed = True` kèm `follow_failed = True` và luôn gọi `adapter.close_all_recent_apps()` để đưa máy về HOME an toàn.
4. **Quy tắc đồng bộ đa repo khi sửa data contract**:
   - Khi sửa payload của hook con (`tiktok-follow`), BẮT BUỘC kiểm tra và cập nhật consumer script / watchdog ở repo cha (`tiktok-luot nuoi acc`).
   - Phải chốt phiên và push đồng bộ cả 2 repo để báo cáo cron Telegram phản ánh đúng dữ liệu mới.

## Recipe triển khai watchdog (verified 2026-09-13)
1. `merge_follow_result(prev, new)` trong `scripts/feed_session_watchdog.py`: merge `followed` dedup + giữ `max(mode1_followed_count)`, `max(mode2_followed_count)` trên mọi nhánh return (OK / SKIPPED / FOLLOW_FAILED). Dùng `int(x or 0)` để tránh `None` crash.
2. `parse_run_all()`: đọc `details` từ `follow_result.json` với `isinstance(d.get("details"), dict)` guard, `int()` trong try/except → default 0, rồi đưa vào `f_item` trước khi gọi `merge_follow_result`.
3. `main()`: cộng dồn `total_m1_count += int(fd.get("mode1_followed_count", 0) or 0)` và `total_m2_count` tương tự; đổi title Telegram thành `• Follow chéo ({total} lượt follow) [Module 2 (Anchor): {m2} | Module 1 (Bù): {m1}]:`.
4. Test nghiệm thu `python_runner/tests/test_feed_session_watchdog.py::test_merge_follow_result_module_counts`: import `merge_follow_result`, assert dedup `["u1","u2","u3"]` + max counts (m1=2, m2=1), và nhánh FOLLOW_FAILED giữ max (m1=2, m2=3). Chạy `pytest .../test_feed_session_watchdog.py -q` phải `5 passed`.
