# Case UI-86: Chuẩn Hóa Mode 2 Lọc Nick Ngoài, Canary Nghiệm Thu Đa Lượt & Entropy Xem Video Profile

## 1. Bối cảnh sự cố & Root Cause (2026-10-01)
- **Sự cố:** Sáng 2026-10-01, toàn farm 80 máy chạy Mode 2 failover sạch sang Mode 1 do dính lỗi `MANUAL_REVIEW: follower row không có nút follow semantic`.
- **Nguyên nhân cốt lõi:**
  - Logic cũ quét `missing_button_rows` kiểm tra mọi row trên màn hình. Khi nick mồi (Anchor) có following tự nhiên (đề xuất, bạn bè ngoài farm), layout nick người ngoài không có nút semantic hoặc bị che khuất -> dập cầu dao `MANUAL_REVIEW`.
  - Selector TikTok 46.x cập nhật thêm resource-id nút follow `com.ss.android.ugc.trill:id/ubp` (`id/ubp`), thiếu trong whitelist selector.
- **Khắc phục:**
  1. Chỉ kiểm tra `missing_button_rows` với nick nội bộ farm: `_normalize_handle(r.get("handle", "")) in internal_uids`. Bỏ qua 100% nick ngoài farm (`not in internal_uids`).
  2. Thêm `com.ss.android.ugc.trill:id/ubp`, `:id/ubp`, `id/ubp` vào `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS`.

---

## 2. Quy Tắc Nghiệm Thu Canary Bắt Buộc (User Invariants)

### Invariant 1: Canary Nghiệm Thu Phải Chạy Đa Lượt (>1 Lượt, Khuyến Nghị 2–4 Lượt)
- **Lý do kỹ thuật:** Nếu chỉ chạy 1 lượt, lỡ lượt đầu tiên rơi đúng vào nick trong farm thì code lỗi cũ cũng có thể vượt qua ngẫu nhiên.
- **Yêu cầu:** Phải cấu hình `budget_per_session` từ 2–4 lượt để chứng minh runner đã cuộn qua các nick ngoài farm an toàn, bỏ qua không văng lỗi và follow thành công các nick farm phía sau.

### Invariant 2: Vị Trí Chụp Ảnh Nghiệm Thu Mode 2 Phải Ở Màn Hình Danh Sách Following
- **Cấm chụp:** Màn hình Profile tổng thể hay màn hình Home/Launcher.
- **Bắt buộc chụp:**
  1. Màn hình danh sách Following khi vừa vào Anchor (thấy các nick ngoài và nick farm).
  2. Màn hình danh sách Following khi đang lướt/sau khi follow (thấy trạng thái nút bấm đã đổi sang Đang follow / Bạn bè).

---

## 3. Quy Trình Xem Video Tự Nhiên & Verify Nhả Follow Trong Mode 2

### A. Với Nick Mồi (Anchor) — `_ensure_anchor_followed`
1. Nếu Anchor chưa follow -> Bắt buộc mở video đầu tiên của Anchor xem **8–15 giây**.
2. Thả tim ngẫu nhiên với tỷ lệ **50%–70%**.
3. Bấm nút Follow trực tiếp **trên video** (dấu `+` đỏ hoặc content-desc Follow).
4. Bấm Back về Profile Anchor, **bắt buộc vuốt reload (pull-to-refresh)** để phá cache nút "Nhắn tin".
5. Nếu sau khi vuốt reload mà nút nhảy lại thành "Follow" đỏ -> Bị nhả, dừng session ngay (`set_follow_failed`).

### B. Với Nick Nội Bộ Trong Danh Sách Following — `_path_b_verify` & `_maybe_watch_profile_video`
1. Bấm nút Follow ngay trên danh sách Following.
2. Bấm vào username để nhảy vào Profile (Path B verify).
3. **Bắt nhả:** Nếu thấy trạng thái vẫn là `not_followed` (nút Follow/Follow lại) -> **Thoát ngay lập tức**, dừng session, cấm xem video.
4. **Nếu server đã nhận thật (`followed`):**
   - Xác suất **~30–35%** chạy `_maybe_watch_profile_video`.
   - **Cuộn tìm video:** Nếu màn hình đầu chưa thấy cover video (do Bio dài hoặc Header lớn), **bắt buộc cuộn nhẹ 1–2 lần** (`swipe(540, 1400, 540, 800)`) để tìm lưới video. Không được lẳng lặng return khi chưa cuộn.
   - Bấm mở video xem **6–10 giây**, xác suất **30% thả tim**.
   - Bấm Back về lại Profile, rồi Back về danh sách Following.
   - **Ghi log & Telemetry:** Log rõ `[MODE2] Đã xem video tự nhiên trên profile @<uid> (dwell=...s, liked=...)` và nạp vào `res.details["mode2_watched_videos"]` để xuất trong báo cáo ca farm.

---

## 4. Tích Hợp Telemetry Vào Báo Cáo Watchdog (`feed_session_watchdog.py`) & Đọc Báo Cáo Vận Hành

### Cập Nhật Báo Cáo Telegram Mỗi Phiên
Watchdog đọc `mode2_watched_count` từ `follow_result.json` và tổng hợp trực tiếp lên dòng báo cáo Follow chéo:
```text
• Follow chéo (50 lượt follow) [Module 2 (Anchor): 46 | Module 1 (Bù): 4 | Xem video: 15 lượt]:
```

### 4 Chỉ Số Đánh Giá Script Vận Hành Ổn Định
1. **Tỷ trọng Module 2 vs Module 1:** Module 2 phải chiếm đa số (80–90%+). Nếu Module 2 tụt dốc về ~0 trong khi Module 1 tăng vọt -> Dấu hiệu lỗi semantic selector hoặc anchor drift.
2. **Số lượt xem video:** Hiển thị số lượt bot đã thực sự vào xem video profile đối phương.
3. **Lỗi script/xác minh:** Phải là `Không có`. Nếu xuất hiện lỗi, kiểm tra ngay máy bị dính để xử lý selector/ADB.
4. **Bị nhả follow:** Tách riêng danh sách máy bị TikTok từ chối follow để đưa vào cooldown bảo vệ nick mà không gián đoạn toàn farm.

