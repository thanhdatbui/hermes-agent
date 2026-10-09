---
name: case-174-live-stream-overlay-closeout
description: Case 174 (16/09/2026) - Xử lý màn hình TikTok LIVE room che Navigation bar khi Verify Profile và bài học cô lập WIP khi chốt phiên qua closeout_gate.py.
---

# Case 174: TikTok LIVE Stream Room Che Navigation Bar & Cô Lập WIP Diff Khi Chốt Phiên (16/09/2026)

## 1. Triệu chứng & Nguyên nhân Sự cố Máy 77
- **Alert**: `feed-session-smoke blocked: profile verification navigation-failed: navigation target profile not found in XML` trên Máy 77.
- **Hiện trường**: Máy 77 swipe xong 21 video, video cuối trúng luồng TikTok LIVE stream (`com.ss.android.ugc.trill`).
- Toàn bộ Bottom Navigation Bar bị che khuất bởi giao diện phòng LIVE:
  - Header: `Thử thách LIVE lân cận`, `14–28/9 Nhận thưởng tiền mặt`.
  - Chat/Activity: `‎Mắt 2 mí giao diện 1 mí đã chia sẻ phiên LIVE`.
- **Root Cause**:
  Hàm `_detect_tiktok_live_room` trong `python_runner/flows/benign_popup_registry.py` chỉ có các marker cũ (`phòng live`, `chia sẻ live`, `nhập bình luận...`), chưa có các cụm từ mới:
  `"phiên live"`, `"thử thách live lân cận"`, `"thu thach live lan can"`.
  Do đó `find_matching_handler` không nhận diện được để dismiss phòng LIVE về feed, làm bước `tap_navigation_target("profile")` không tìm thấy tab Hồ sơ và fail-closed.

## 2. Giải pháp Sửa Lỗi & Unit Test
- Bổ sung 3 marker vào `_detect_tiktok_live_room` trong `python_runner/flows/benign_popup_registry.py`.
- Thêm test case `test_detect_tiktok_live_room_session_share_and_challenge` trong `python_runner/tests/test_benign_popup_registry.py`.
- Chạy focused test:
  `pytest python_runner/tests/test_benign_popup_registry.py -k "live_room"` -> 4/4 passed trong 5.58s.

## 3. Kỷ luật Chốt phiên với `closeout_gate.py` (Cô lập WIP Diff)
- **Cạm bẫy**: Khi repo có các thay đổi WIP khác trong working tree (ví dụ thử nghiệm `fast natural swipe` trong `feed_swipe_smoke.py`), `closeout_gate.py` trích xuất cả 2 file, dẫn đến Reviewer OmniRoute reject do lo ngại regression về thời gian vuốt màn hình.
- **Quy tắc cô lập**:
  1. `git stash push -m "unrelated-wip" <path/to/dirty_file>` để đưa candidate diff về đúng phạm vi sửa lỗi task hiện tại.
  2. Chạy lại `closeout_gate.py --repo "<repo>" --skip-test --base HEAD` -> Reviewer phê duyệt ngay lập tức (**`APPROVED`**).
  3. Commit, fetch, push lên remote an toàn.
  4. Working tree sạch sẽ sau khi hoàn tất.
