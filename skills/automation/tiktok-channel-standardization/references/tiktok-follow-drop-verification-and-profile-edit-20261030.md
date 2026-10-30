# TikTok Follow Drop Verification & Profile Edit UI Mechanics (2026-10-30)

## 1. Cơ Chế Kiểm Tra "Nhả Follow" Trong Code Farm
Quy trình phát hiện nhả follow trong `mode2_follow_followers.py` hoạt động nghiêm ngặt và trung thực, chống Optimistic UI của TikTok:

- **Tại khâu Anchor (`_ensure_anchor_followed` dòng 610-675):**
  1. Bắt buộc mở video đầu tiên của Anchor.
  2. Dwell xem video 8 - 15 giây (`dwell = random.uniform(8.0, 15.0)`).
  3. Like ngẫu nhiên 50% - 70%.
  4. Bấm nút Follow ngay trên video (avatar + icon hoặc content-desc Follow).
  5. Chờ 2 - 4 giây để server ghi nhận, sau đó bấm Back về Profile Anchor.
  6. **BẮT BUỘC VUỐT RELOAD (Pull-to-refresh):** Gọi `pull_to_refresh_profile(adapter, sleep_after=3.5s)` để xóa cache UI của client, ép app tải quan hệ thực tế từ server.
  7. Nếu nút trên Profile Anchor sau khi reload nhảy ngược lại thành màu đỏ (`Follow` hoặc `Follow lại`): Đánh dấu `FOLLOW_FAILED: anchor @... bị nhả sau vuốt — dừng session`.

- **Tại khâu Followers List (Path B dòng 1704-1732):**
  1. Bấm follow trên danh sách ➔ Mở profile của đối phương lên để xác minh.
  2. **BẮT BUỘC VUỐT RELOAD:** Gọi `pull_to_refresh_profile(adapter, sleep_after=3.5s)`.
  3. Nếu nút hiển thị `Follow` thay vì `Đang follow`: Đánh dấu `FOLLOW_FAILED: TikTok không nhận follow (profile vẫn chưa follow)`.

## 2. Xác Suất Xem Video Mồi (Followers List)
- Hàm `_maybe_watch_profile_video`:
  - Quy định tỷ lệ trúng xem video: `chance_range = (0.30, 0.35)` (30% - 35%).
  - 65% - 70% các lượt follow trong danh sách followers sẽ bấm trực tiếp không xem video.
  - Khi trúng lượt xem: Dwell từ 12 - 20s, like 80%.

## 3. Bản Chất Kỹ Thuật Khi Nick Bị Nhả
- "Nhả" là kết quả **bị server TikTok từ chối (Drop) thật**, được xác minh qua cú vuốt reload (Pull-to-refresh) + sleep 3.5s.
- CẤM suy đoán cảm tính về việc nick "chưa đủ video", "lỗi mạng" hay "Anchor khó tính".
- **Invariant Nền Tảng TikTok**: TikTok CHỈ kiểm soát/giới hạn ở chiều CHO ĐI (Following của chính nick đang chạy bot), TUYỆT ĐỐI KHÔNG CÓ NỀN TẢNG NÀO CẤM CHIỀU NHẬN (Follower). Không bao giờ được suy diễn Anchor cấm nhận follow!
- Phải đọc trực tiếp file `follow_result.json` và mã nguồn để đối soát chính xác hành vi của từng máy.

## 4. Phạm Vi Rà Soát Độ Tuổi Nick (Fleet Audit Contract)
- Khi User yêu cầu rà soát theo "cùng độ tuổi" hoặc "cùng đợt reg": BẮT BUỘC lọc theo khoảng thời gian reg chuẩn xác `reg_date ± 15 ngày` (hoặc đúng ngày cụ thể).
- TUYỆT ĐỐI CẤM gom các nick lệch tháng/khác đợt (như nick tháng 6/tháng 7) vào báo cáo so sánh độ tuổi của nick cuối tháng 8.

## 4. Cơ Chế Đổi Username Trên Biến Thể Profile Mới
- Nút Sửa hồ sơ trên TikTok S7 là **ICON CÂY BÚT CHÌ**.
- Trên một số biến thể giao diện chưa có Bio, TikTok ẩn nút Sửa hồ sơ và chỉ hiện nút `+ Thêm tiểu sử`.
- Giải pháp: Tap vào dòng Bio (hoặc nhập tạm 1 Bio hợp lệ có dấu tiếng Việt) ➔ Giao diện Profile chuyển về dạng có dòng Bio ➔ Tap trực tiếp vào dòng Bio sẽ mở ra trang **Sửa hồ sơ** đầy đủ ➔ Tap vào dòng `Tên người dùng` (@handle) để đổi và bấm Xác nhận popup 30 ngày.
