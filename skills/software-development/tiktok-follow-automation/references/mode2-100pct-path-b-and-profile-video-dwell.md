# Mode 2 Enforce 100% Path B Verify & 30% Profile Video Dwell (2026-09-18)

## 1. Bối cảnh & Vấn đề Kỹ thuật (Root Cause)

- **Optimistic UI lừa đảo trên Follower List**:
  - Khi tap Follow trên một row trong RecyclerView danh sách follower của Anchor, TikTok Android đổi nút sang "Đang theo dõi" / "Bạn bè" ngay lập tức trên UI client (Optimistic UI).
  - Tuy nhiên, backend Async Risk Engine của TikTok có thể âm thầm từ chối/rollback follow mà không gửi thông báo lỗi tức thì về UI list.
  - Nếu áp dụng cơ chế cadence sampling (`verify_sample_every: 5`), các nick ở vị trí không trúng sample sẽ chỉ được verify bằng `_classify_row_button`. Bot tin rằng follow thành công và tiếp tục tap các nick tiếp theo, dẫn tới tình trạng tap mù 4–5 nick bị nhả liên tiếp mà không phanh kịp thời.

## 2. Chuẩn hóa Quy tắc Invariant (Patch Contract)

### 2.1. Cấu hình bắt buộc 100% Verify
- `verify_sample_every: 1` tại:
  - `follow_runner/core/config.py` (default field)
  - `config/machine7.yaml`, `config/machine8.yaml`
  - `follow_runner/config.example.yaml`
- Trong `follow_one_follower`: Loại bỏ hoàn toàn điều kiện `if sample:` khi `cls == "followed"`. Mọi lượt tap follow thành công trên row đều BẮT BUỘC thực hiện `_path_b_verify` để vào profile đối phương xác minh trạng thái nút thật từ server activity mới.

### 2.2. Hành vi xem video ngẫu nhiên 30% trên Profile đối phương (`_maybe_watch_profile_video`)
- **Tần suất**: ~30% (xấp xỉ 1 trong mỗi 3–4 profile được verify thành công).
- **Mục tiêu**: Gia tăng behavioral entropy, mô phỏng hành vi người dùng thật (lướt xem nội dung của người vừa follow), phá vỡ chữ ký bot chỉ vào profile - check nút - back ngay lập tức.
- **Quy trình tương tác**:
  1. Kiểm tra mock/FakeAdapter: Nếu là `FakeAdapter` hoặc `getattr(adapter, "_is_mock", False)`, return ngay để không phá vỡ unit tests.
  2. Lọc danh sách video covers từ `profile_nodes`:
     - `resource_id` chứa `cover`, `tv_play_count`, `exx`, `aweme`.
     - `bounds` hợp lệ với `bounds[1] >= 400` (nằm dưới khu vực header/bio).
  3. Mở video cover đầu tiên, xem ngẫu nhiên từ 6.0s đến 10.0s.
  4. Tỷ lệ thả tim ngẫu nhiên ~30%: Tìm nút thích (`thích`, `like`, `yêu thích` hoặc `like_icon`) và tap.
  5. Gọi `adapter.back()` quay lại màn hình Profile trước khi luồng `_path_b_verify` thực hiện back về danh sách follower.
  6. Luôn bọc toàn bộ khối xử lý trong `try/except` với fallback `adapter.back()` để đảm bảo an toàn tuyệt đối không làm kẹt luồng verify chính.

## 3. Lệnh kiểm thử & Verification Baseline

```bash
python -m pytest follow_runner/tests/test_mode2_follow_followers.py -k "test_follow_one_follower"
```
Đảm bảo 5 test cases chuẩn của `test_follow_one_follower` vượt qua khi chạy với FakeAdapter.
