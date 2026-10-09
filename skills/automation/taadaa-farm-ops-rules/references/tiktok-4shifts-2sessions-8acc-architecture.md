# Kiến trúc Nuôi TikTok 4 Ca x 2 Phiên (8 Account / Máy) & Tối Ưu Quota Follow

Chốt kiến trúc hệ thống (09/09/2026):

## 1. Phân bổ Ca & Lịch chạy (Lane Parity)
- **Tần suất & Tải:** Chuyển đổi từ mô hình 3 Ca x 3 Phiên (6 acc/máy) sang **4 Ca x 2 Phiên** (hỗ trợ tối đa 8 acc/máy: Row 1 đến 8).
- **Lập lịch chẵn lẻ:**
  - Ngày Lẻ (Lane B): Chạy Row 1, Row 3, Row 5, Row 7.
  - Ngày Chẵn (Lane A): Chạy Row 2, Row 4, Row 6, Row 8.
- **Khung giờ Block Anchors (4 Ca rải đều 6 tiếng):**
  - **Ca 1:** `06:00` (Phiên 1: 06:00 - 07:30, Phiên 2: 07:30 - 10:00).
  - **Ca 2:** `12:00` (Phiên 1: 12:00 - 13:30, Phiên 2: 13:30 - 16:00).
  - **Ca 3:** `18:00` (Phiên 1: 18:00 - 19:30, Phiên 2: 19:30 - 22:00).
  - **Ca 4:** `00:00` (Phiên 1: 00:00 - 01:15, Phiên 2: 01:15 - 03:00).
- **Khoảng nghỉ đêm & Bảo trì:**
  - Từ `03:00 - 06:00` máy nghỉ sâu hoàn toàn, nhường tài nguyên cho job Dọn cache TikTok (`04:00`).

## 2. Quy tắc Phiên (2 Phiên / Ca)
- **Cấu trúc 1 Ca:** Mỗi acc chỉ chạy 2 phiên (mỗi phiên lướt feed 30-35 phút).
- **Khoảng nghỉ giữa phiên (`pair_gap`):** 35 đến 60 phút giữa Phiên 1 và Phiên 2 để máy hạ nhiệt.
- **Hook Đăng Video (Upload Hook):**
  - BẮT BUỘC dời lên **Phiên 2** (phiên cuối của ca), thay vì phiên 3 như trước.
  - Gating `multi_machine_feed_session.py`: Kiểm tra `session_index == 2` để kích hoạt đăng video.

## 3. Tối ưu Quota Follow (tiktok-follow)
- Khi rút từ 3 phiên xuống 2 phiên/ngày, để bảo toàn trần follow an toàn (~35 follow/ngày):
  - `budget_per_day`: 35
  - `budget_per_session`: Nâng từ 12 lên **18**
  - `budget_per_session_min`: **15**
  - `budget_per_session_max`: **18**
- **Nhịp độ an toàn:** 15-18 follow rải đều trong 30-35 phút lướt feed (~2 phút/follow) giúp tránh spam detection của TikTok và chống nhả follow ngầm.
