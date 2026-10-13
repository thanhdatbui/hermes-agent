# Anchor Mining Density and Following List Invariants (Mode 2)

## 1. Ranh giới State Giữa Anchor Mẹ vs Nick Con Nội Bộ (Non-Negotiable)
- **Quy tắc bất biến:** `state.is_followed` và bộ nhớ tài khoản đã follow **CHỈ ÁP DỤNG cho các nick con nằm TRONG danh sách Following/Follower**.
- **CẤM TUYỆT ĐỐI skip Anchor vì đã follow Anchor:**
  - Một Anchor nòng cốt (Tik1/Tik2) có thể có 200–380 Following. Một nick farm mới chỉ follow 10–15 nick trong đó.
  - Sau mỗi phiên, danh sách Following của Anchor đó vẫn còn hàng trăm nick farm hợp lệ chưa được khai thác.
  - Skip Anchor chỉ vì nick đã từng bấm follow Anchor là sai lầm nghiêm trọng: làm cạn kiệt mỏ Anchor xịn sớm và ép bot phải nhảy sang các Anchor mỏng hoặc fallback sang Mode 1.
  - Kể cả Anchor đã là bạn bè/đã follow sẵn, bot vẫn được phép và khuyến khích quay lại mở tab Following của Anchor đó để đào tiếp các nick con chưa follow.

## 2. Bẫy Rút Thăm Cào Bằng (Uniform Shuffle Trap) vs Xếp Hạng Độ Dày Của Mỏ (Anchor Density)
- **Hạn chế của cơ chế cũ:**
  - `anchor_uids()` áp dụng Min-following Gate (`following >= 30` từ snapshot mới nhất trong `tiktok_tracker.db`) để loại bỏ mỏ rỗng.
  - Tuy nhiên, khi vào `run_mode2`, lệnh `random.shuffle(uids); uids = uids[:3]` phân phối xác suất cào bằng (1/N) giữa mỏ 30 following và "siêu mỏ" 380 following (như `@hongggg.yn`, `@th.thy081`, `@thanh.h.dng00`).
- **Quy chuẩn điều phối ưu tiên mật độ (Density-Ranked Selection):**
  - **Tier S (Siêu mỏ $\ge 150$ following):** Ưu tiên bốc ngẫu nhiên trong nhóm này trước. Mỏ dày đảm bảo 1 phiên chạy Mode 2 luôn vét đủ quota 10–15 follow mà không lo cạn list.
  - **Tier A (Mỏ tiêu chuẩn $50 - 149$ following):** Chỉ bốc khi nhóm Tier S không còn anchor nào khả dụng hoặc không thể mở được.
  - **Tier B ($30 - 49$ following):** Dự phòng cuối cùng.
  - **Dưới 30 following:** Khóa cứng cổng loại trừ (`excluded_low_following`).

## 3. Phân Biệt Báo Cáo Phiên (Session Watchdog) vs Tích Lũy Ngày (Tracker DB)
- **Cơ chế ghi nhận:**
  - SQLite `tiktok_tracker.db` (`daily_account_actions`): Tích lũy tổng lượt follow thành công theo ngày dương lịch (`target_date`).
  - `feed_session_watchdog.py`: Báo cáo độc lập theo từng **Phiên chạy (Session)** trong Ca (ví dụ Phiên 1: 06:00–07:30, Phiên 2: 07:30–09:30).
- **Hiện tượng lệch số biểu kiến:**
  - Khi Phiên 1 thành công 1 lượt (`thanhbich0121` +1 follow) $\rightarrow$ DB ghi nhận `internal_follows = 1`.
  - Đến Phiên 2, nick chạy gặp anchor bị nhả nút và kích hoạt Fail-Closed an toàn $\rightarrow$ Phiên 2 không có lượt nào mới. Báo cáo Phiên 2 báo `Follow chéo (0 lượt follow)`.
  - Đây là hành vi đúng chuẩn của hệ thống giám sát theo phiên, không phải lỗi đồng bộ dữ liệu.

## 4. Tách Bạch Báo Cáo Lỗi Phần Cứng (Hardware USB/ADB Drop) vs Lỗi Logic Script
- Khi điện thoại bị mất kết nối ADB/USB do nghẽn thanh ghi bus USB 2.0 EHCI sau nhiều giờ hoạt động, script follow kích hoạt `status: BLOCKED (preflight device-lock/VPN fail-closed)`.
- Watchdog gom các ca `BLOCKED` này vào bộ đếm lỗi follow, và nếu $\ge 8$ máy sẽ phát cảnh báo `🚨 [FARM ALERT] PHÁT HIỆN LỖI SCRIPT FOLLOW HÀNG LOẠT`.
- **Kỷ luật chẩn đoán của Coordinator:**
  - Bắt buộc kiểm tra hiện trường O(1) bằng `inspect_machine.py <N>`.
  - Nếu lý do là `device not found / adb offline`, nguyên nhân là phần cứng/bus USB cần chu kỳ Reboot BIOS System Bus Reset (11:35 hàng ngày), TUYỆT ĐỐI KHÔNG vội vàng kết luận script logic hay runner Python bị hỏng code!
