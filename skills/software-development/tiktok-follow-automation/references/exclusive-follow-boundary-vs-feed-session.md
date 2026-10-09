# Phân Định Ranh Giới: Follow Chéo vs Follow Tự Nhiên Lướt Feed (2026-10-07)

## 1. Ranh Giới Vận Hành Độc Quyền
- **Hành vi Follow ĐỘC QUYỀN của `tiktok-follow`:**
  - Mọi thao tác tap Follow trên toàn bộ Taadaa Phone Farm chỉ được phép diễn ra trong repo `tiktok-follow` (`Mode 1: Search Follow` và `Mode 2: Follow Followers`).
  - Mỗi lượt follow đều phải tuân thủ nghiêm ngặt:
    + Dual Gate: `account_age_days >= 30` VÀ `video_count >= 10`.
    + Budget hạn mức phiên từ `follow_state.json`.
    + Path B / Pull-to-refresh: Sau khi bấm follow video, quay về profile Anchor và vuốt kéo làm mới (`pull_to_refresh_profile`) để xác minh server TikTok không nhả nút đỏ.
- **Tuyệt đối cấm follow dạo trong phiên Nuôi Nick Lướt Feed (`tiktok-luot nuoi acc`):**
  - Trong các flow `feed_swipe_smoke.py` và `benign_popup.py`:
    + Thẻ đề xuất bạn bè (`follow_back_suggestion`): Bấm nút "Không quan tâm" (`id/cv6`) 100%.
    + Popup gợi ý bạn bè (`follow_friends_suggestion_popup`): Khóa `follow_limit = 0`, chỉ bấm Đóng / Back.
  - Lý do: Follow trên feed là bấm mù không qua verify pull-to-refresh, gây hao hụt burst velocity limit và làm sai lệch đối soát của watchdog.
