# Targeted Canary Discipline & Following Tab Selector Drift (TikTok v46.9.3)

## 1. Hiện trường sự cố (Sự cố 13 máy Row 2 fail mở tab Following - 14/09/2026)
- **Triệu chứng**: 13 máy chạy Follow Mode 2 (`M10, M26, M27, M32, M33, M35, M41, M46, M55, M58, M60, M64, M72`) đều văng lỗi:
  `MANUAL_REVIEW: mở tab Đã follow fail cho {uid} sau ladder (lần 2)`.
- **Sai lầm quy trình Canary**:
  - Agent kiểm chứng bản vá bằng lệnh full session:
    `python -m follow_runner.run_follow --machine 10 --config ... --account-row-index 2 --mode 2`.
  - Chế độ này có budget mặc định 15–18 follows, xem video đệm và delay mô phỏng người dùng kéo dài >10 phút.
  - Subagent chạm trần timeout 360s của tool, tiến trình bị cắt ngang và chụp ảnh non (ảnh chụp lúc máy mới ở trang tìm kiếm nick, chưa vào profile anchor).
  - User chấn chỉnh: *"Hình m gửi là trang tìm kiếm nick mà... Đm lần sau chạy canary thì chạy nhắm đúng cái hàm vừa sửa thôi. Lưu rule này lại..."*

## 2. Nguyên nhân kỹ thuật gốc (Root Causes)

### Root Cause 1: Thiếu nhãn tiếng Việt trong regex Relation Tab
- TikTok phiên bản tiếng Việt hiển thị tiêu đề tab quan hệ là `"Đang follow [N]"` hoặc `"Đang theo dõi [N]"`.
- Trong `mode2_follow_followers.py`, regex `_FOLLOWER_HEADER_RE` và set `_FOLLOWER_EMPTY_LABELS` chỉ có:
  `"follower"`, `"followers"`, `"người theo dõi"`, `"đã follow"`, `"following"`.
- Thiếu 2 cụm từ trên khiến tab bị phân loại là `invalid`, `_on_follower_list` trả về `False`.
- **Khắc phục**:
  ```python
  _FOLLOWER_HEADER_RE = re.compile(
      r"^(follower|followers|người theo dõi|đã follow|đang follow|đang theo dõi|following)(?:\s+(\d+))?$",
      re.IGNORECASE,
  )
  _FOLLOWER_EMPTY_LABELS = {
      "follower", "followers", "người theo dõi", "đã follow", "đang follow", "đang theo dõi", "following",
  }
  ```

### Root Cause 2: Obfuscation RecyclerView ID trên TikTok v46.9.3
- Khi bot đã tap trúng tab và danh sách Following của anchor bung ra, bot vẫn timeout 25s vì không tìm thấy `RecyclerView`.
- TikTok v46.9.3 đổi ID `RecyclerView` hiển thị danh sách Following thành `com.ss.android.ugc.trill:id/uzs`.
- Khai báo cũ trong `follow_runner/core/selectors.py` (`FOLLOWER_LIST_RECYCLER_IDS`) chỉ gồm: `id/u5r`, `id/u_q`, `id/uoc`, `id/uo1`, `id/uvz`.
- **Khắc phục**:
  Bổ sung `com.ss.android.ugc.trill:id/uzs`, `:id/uzs`, `id/uzs` vào tuple `FOLLOWER_LIST_RECYCLER_IDS`.

## 3. Quy tắc Targeted Canary Invariant (ANTI-UNBOUNDED CANARY)

### Điều cấm
- **CẤM TUYỆT ĐỐI chạy full session (`run_session`) khi canary**: Không bao giờ kích hoạt pipeline nuôi acc với budget 15-18 follow để test sửa một selector hay một hook. Điều này gây lãng phí thời gian, timeout tool và chụp ảnh non sai lệch hiện trường.

### Tiêu chuẩn thực thi (< 60 giây)
- BẮT BUỘC dùng entrypoint targeted canary với cờ `--canary-hook`:
  ```bash
  python -m follow_runner.run_follow \
    --machine <N> \
    --config follow_runner/config.example.yaml \
    --account-row-index <row> \
    --skip-identity-verify \
    --canary-hook open_following_tab \
    --canary-target <anchor_uid> \
    --canary-screencap <path_to_png>
  ```
- **Các hooks được hỗ trợ**:
  1. `open_following_tab`: Test mở tab Following của anchor và xác nhận list render.
  2. `nav_search`: Test luồng tìm kiếm và mở profile mục tiêu.
  3. `verify_profile`: Test verify profile identity.
  4. `single_follow`: Test follow 1 video/profile cụ thể.
- **Nghiệm thu ảnh tại đúng đích**:
  - Script tự động chụp screencap qua `adapter.screencap()` ngay khi hook hoàn thành.
  - Bằng chứng ảnh BẮT BUỘC thể hiện đúng trạng thái đích (ví dụ: danh sách Following đã bung ra và hiển thị các hàng tài khoản). Cấm chụp khi app còn ở trang tìm kiếm hoặc đang chuyển cảnh.

## 4. Farm Alert Gate (> 10 máy lỗi)
- **Quy định**: Tại bất kỳ ca chạy nào, nếu phát hiện **> 10 máy** gặp sự cố ở bất kỳ khâu nào:
  + Lướt Feed Fail > 10 máy
  + Follow Hook Lỗi UI/Script > 10 máy
  + Upload Hook Lỗi > 10 máy
- **Hành động**: Watchdog `feed_session_watchdog.py` BẮT BUỘC gọi `send_farm_alert` gửi thông báo đỏ `🚨 [FARM ALERT] PHÁT HIỆN LỖI DIỆN RỘNG (>10 MÁY)` về nhóm Telegram `chat_id = -5373649734` kèm danh sách máy và mã lỗi chi tiết.
