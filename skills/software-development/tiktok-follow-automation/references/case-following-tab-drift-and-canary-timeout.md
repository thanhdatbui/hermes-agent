# Case UI: Drift Header Tab "Đang follow" / "Đang theo dõi" & Canary Bounded Timeout

## 1. Triệu chứng & Bối cảnh
- **Bối cảnh:** Phiên nuôi Row 2 ngày 2026-09-14, 13 máy chạy Follow Mode 2 đều thất bại với lỗi:
  `MANUAL_REVIEW: mở tab Đã follow fail cho {uid} sau ladder (lần 2)`
- **Các máy dính lỗi:** `M10, M26, M27, M32, M33, M35, M41, M46, M55, M58, M60, M64, M72`.
- **Nguyên nhân gốc rễ (Root Cause):**
  - Màn hình hồ sơ TikTok phiên bản tiếng Việt hiển thị tab số lượng theo dõi bằng các nhãn: `"Đang follow [N]"` hoặc `"Đang theo dõi [N]"`.
  - Trong `follow_runner/flows/mode2_follow_followers.py`, bộ nhận diện `_FOLLOWER_HEADER_RE` và `_FOLLOWER_EMPTY_LABELS` chỉ định nghĩa cứng:
    `"follower", "followers", "người theo dõi", "đã follow", "following"`.
  - Do thiếu `"đang follow"` và `"đang theo dõi"`, hàm `_classify_follower_surface` phân loại bề mặt là `"invalid"`, khiến `_on_follower_list` trả về `False`. Kết quả: hàm `_open_following_tab` lặp poll 25s không thấy list render, kích hoạt fallback ladder rồi văng `MANUAL_REVIEW`.

## 2. Giải pháp kỹ thuật (Contract Fix)
Tại `follow_runner/flows/mode2_follow_followers.py`:
- Cập nhật regex:
  ```python
  _FOLLOWER_HEADER_RE = re.compile(
      r"^(follower|followers|người theo dõi|đã follow|đang follow|đang theo dõi|following)(?:\s+(\d+))?$",
      re.IGNORECASE,
  )
  ```
- Cập nhật nhãn rỗng:
  ```python
  _FOLLOWER_EMPTY_LABELS = {
      "follower", "followers", "người theo dõi", "đã follow",
      "đang follow", "đang theo dõi", "following",
  }
  ```
- Viết bổ sung unit test trong `follow_runner/tests/test_mode2_follow_followers.py` kiểm tra cụ thể `Đang follow 3` và `Đang theo dõi 5`.

## 3. Bài học Canary & Nghiệm thu Bằng chứng (Live Canary Discipline)
- **Cạm bẫy:** Khi test canary máy thật, nếu gọi lệnh nuôi đầy đủ (`run_follow` với budget 15-18 follow, xem video đầy đủ), tiến trình sẽ kéo dài >10 phút và dễ bị tool runner timeout (ví dụ subagent timeout 360s). Điều này dẫn đến việc tiến trình bị ngắt giữa chừng, chụp ảnh non (chỉ dừng ở màn hình tìm kiếm Search landing) và báo cáo sai lệch kết quả.
- **Quy tắc nghiệm thu Canary đúng chuẩn:**
  1. Khi kiểm chứng UI Hook/Selector, bắt buộc thu hẹp scope (Targeted Canary): chạy test với đúng 1 UID / 1 follow budget hoặc kiểm tra riêng hàm điều hướng.
  2. Bắt buộc kiểm tra nội dung ảnh screencap: Ảnh nghiệm thu phải phản ánh đúng màn hình đích (danh sách Following đã mở ra), tuyệt đối không chấp nhận ảnh đang kẹt ở bàn phím hoặc thanh tìm kiếm.
  3. Luôn thực hiện Teardown an toàn: `am force-stop`, gửi `keyevent 3` (HOME) và `keyevent 26` (tắt màn hình).
