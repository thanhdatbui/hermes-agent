# Triage: Profile Anchor Safe-Skip & Ngôn ngữ phản hồi

## 1. Ngôn ngữ & Phong cách phản hồi
- BẮT BUỘC 100% TIẾNG VIỆT, đi thẳng vào số liệu ca/máy/acc/row. Tuyệt đối không xổ tiếng Anh khi giải thích flow vận hành farm cho user.

## 2. Hiện tượng: Tìm kiếm acc, vào profile, lướt video rồi thoát không xem
- **Bản chất**: Cơ chế **Video Gate / Safe-Skip** trong `mode2_follow_followers.py` (`_ensure_anchor_followed`).
- **Nguyên nhân**:
  1. Quy tắc Anti-Release: CẤM tap follow trực tiếp trên profile anchor. Bắt buộc mở video đầu tiên -> xem 8-15s -> like 50-70% -> follow từ player.
  2. Khi vào profile, bot tìm video cover theo selector (`cover`, `tv_play_count`, `exx`, `aweme`).
  3. Nếu màn hình đầu chưa có, bot swipe nhẹ 1 lần (`adapter.swipe(540, 1400, 540, 800)`) để load lưới video.
  4. Nếu sau swipe vẫn không match được video cover nào (profile không có video hoặc UI XML selector bị lệch), bot kích hoạt chốt chặn:
     `reason: "anchor @<uid> không có video — back ra bỏ qua"`
  5. Sau đó bot back ra, kết thúc session và trigger teardown (force-stop TikTok về HOME).
- **Vị trí tra cứu O(1)**:
  - `D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/row-<N>-<time>/<timestamp>/machines/machine_<ID>/<timestamp>/follow_result.json`
  - Tra cứu row acc trên `taikhoan_run_safe.xlsx` để đối chiếu slot máy và target anchor.
