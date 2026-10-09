# Anchor Pull-to-Refresh & Web Reconciliation Reconcile Rule (2026-10-06)

## 1. Bản chất cơ chế Pull-to-Refresh Profile Anchor (`pull_to_refresh_profile`)
- **Vị trí và lực vuốt:**
  - `cx = 540`, `y1 = int(h * 0.35)` (~672px), `y2 = int(h * 0.78)` (~1497px), duration 500-750ms.
  - Vuốt kéo từ 35% màn hình xuống 78% màn hình trên trang Profile đối phương kích hoạt chuẩn `SwipeRefreshLayout` của TikTok.
  - Khi nick bị nhả follow ngầm (shadow limit action), nút bấm trên video/profile ban đầu có thể hiển thị "Đã follow" do local UI optimistic update.
  - **Nhưng ngay khi cú vuốt reload (Pull-to-refresh) hoàn tất:** App TikTok bắt buộc fetch fresh metadata từ backend. Nút lập tức văng ngược lại thành nút `Follow` màu đỏ.
  - Runner bắt sống trạng thái nhả tại chỗ qua `refreshed_classification == "not_followed"` và set cờ `FOLLOW_FAILED` dừng session ngay lập tức.

## 2. Quy tắc đối soát TikTok Web vs Runner (Nguyên nhân lệch âm ảo)
- **Hiện tượng:** Runner báo `followed_count = 1` hoặc `2` (tính cả follow tự nhiên khi lướt feed + anchor 1 thành công cục bộ), nhưng sau đó anchor 2 bị nhả sau vuốt (`FOLLOW_FAILED`). Khi đối soát snapshot TikTok Web cuối phiên, Following của nick trên Web tăng +0 $\rightarrow$ Watchdog báo lỗi `Lệch -2`.
- **Nguyên nhân gốc rễ:**
  - Khi TikTok server kích hoạt shadow limit cho nick, backend từ chối commit bất kỳ action follow nào vào database toàn cục (kể cả follow feed lẫn follow profile).
  - Client app có thể cache hiển thị tạm thời ở 1 vài màn hình trước đó, nhưng thực chất DB TikTok không ghi nhận.
- **Kỷ luật Watchdog:**
  - Nếu máy/nick kết thúc phiên với trạng thái `FOLLOW_FAILED` (bị nhả follow ở bất kỳ nhịp nào trong phiên):
    - Toàn bộ follow tự nhiên lúc lướt feed coi như không hợp lệ.
    - Tại bảng đối soát TikTok Web cuối phiên, KHÔNG tính nick này vào số lệch âm bắt buộc (negative delta defect). Phải gắn cờ `Web +0 (Bị nhả follow trong phiên, TikTok server drop action)` để tránh báo động giả / lệch ảo.

## 3. Targeted Canary Probe với `--canary-hook`
- Khi chạy canary hook isolated test (ví dụ `open_following_tab`, `verify_profile`):
  - Bắt buộc khởi tạo `FollowState(args.machine, cfg, account_row_index=args.account_row_index)` truyền vào `FollowEngine`, KHÔNG truyền `state=None`.
  - Giữ timeout an toàn và chụp screencap kiểm chứng nút trước khi phán đoán.
