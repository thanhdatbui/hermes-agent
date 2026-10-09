# Anchor Video Grid Scroll Retry & Gate 1 Review Discipline (Case UI-60 Extension)

## Bối cảnh sự cố (13/09/2026)
- Khi chạy Mode 2 Follow Followers trên TikTok 46.x, nhiều máy báo lỗi `MANUAL_REVIEW: anchor @... không có video — back ra bỏ qua` trong khi người vận hành xác nhận **Anchor luôn có video thực tế**.
- Nguyên nhân gốc rễ: Khi vào trang profile của anchor từ màn hình tìm kiếm, màn hình đầu tiên (above the fold) chỉ hiển thị avatar, bio, số follower/following và tab bar. Lưới video nằm ở phía dưới và cần thời gian render hoặc cần cuộn nhẹ xuống mới xuất hiện trong UI hierarchy dump.
- Logic cũ chỉ cuộn nhẹ 1 lần (`adapter.swipe(540, 1400, 540, 800, 400)`) với `time.sleep(1.0)`. Trên các máy S7/Android farm cấu hình thấp hoặc mạng chậm, UI XML dump ngay sau 1s vẫn chưa kịp load các node video thumbnail (`cover`, `tv_play_count`, `exx`, `aweme`), dẫn đến kết luận vội là `no_video`.

## Pitfall & Bài học Review Gate 1: CẤM Fallback Bypass bừa bãi
- **Anti-Pattern (Bị Gate 1 Reject)**:
  - Worker cố gắng sửa nhanh bằng cách mở gate fallback tap Follow: `if is_mock_adapter:` -> `if True:` với lý do "anchor luôn có video, cứ tap follow luôn".
  - **Lý do Reviewer Reject**: Làm như vậy sẽ biến live device thành luôn tap follow anchor ngay cả khi không thấy video, phá vỡ hoàn toàn quy định farm an toàn (chỉ follow anchor đủ điều kiện video) và vô hiệu hóa cơ chế safe-skip.
- **Giải pháp chuẩn (Được Reviewer Approved)**:
  - Không mở fallback tap profile bừa bãi.
  - Tăng cường khả năng dò tìm lưới video bằng vòng lặp cuộn bounded (tối đa 2 lần):
    ```python
    if not video_covers and not is_mock_adapter:
        for _ in range(2):
            try:
                adapter.swipe(540, 1400, 540, 800, 400)
                time.sleep(1.2)
                fresh_profile_xml = adapter.dump_ui()
                if fresh_profile_xml:
                    profile_xml = fresh_profile_xml
                    profile_nodes = _parse_mode2_nodes(fresh_profile_xml)
                    video_covers = [
                        n for n in profile_nodes
                        if any(k in str(n.get("resource_id", "")).lower() for k in ("cover", "tv_play_count", "exx", "aweme"))
                        and n.get("bounds")
                        and isinstance(n["bounds"], (list, tuple))
                        and len(n["bounds"]) == 4
                        and n["bounds"][1] >= 400
                    ]
                    if video_covers:
                        break
            except Exception:
                pass
    ```
  - Delay tăng từ 1.0s lên 1.2s cho thiết bị kịp render, có `break` ngay khi tìm thấy video cover để không tốn thao tác thừa.

## Tách bạch Báo cáo Module 1 / Module 2 trong Watchdog
- `run_follow.py` emit `mode1_followed_count` và `mode2_followed_count` trong `details` của `FOLLOW_RESULT`.
- `feed_session_watchdog.py` parse passthrough 2 trường này từ `details` (fallback về 0 nếu dữ liệu cũ).
- Trong báo cáo tổng kết, hiển thị rõ ràng:
  `+ Module 2 (following-list nội bộ): X lượt | Module 1 (search bù): Y lượt`
  để người vận hành nắm chính xác tỷ lệ follow từ danh sách nội bộ và lượng search bù.
