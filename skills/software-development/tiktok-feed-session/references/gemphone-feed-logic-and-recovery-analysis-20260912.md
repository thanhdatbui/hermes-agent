# Phân tích toàn diện Flow GemPhoneFarm (Anh Khoa) & Kỹ thuật phục hồi tài khoản

Nguồn đối chiếu: Script `TIKTOK-Nuôi-Tài-Khoản-Gốc_decrypted.json` (205 nodes, 481 edges) tại `D:/Taadaa/TIKTOK-Nuoi-Tai-Khoan-Goc_decrypted.json_decrypted.json`.

---

## 1. Bản chất Action Block & Hiện tượng nhả follow (Silent Follow Drop)
- **Thực tế kiểm chứng trên Máy 24:** Bấm Follow trên UI local cập nhật thành công (nút chuyển "Nhắn tin"), nhưng khi thoát app / vào lại profile hoặc vuốt reload, server TikTok revert về nút đỏ `Follow`.
- **Nguyên nhân vỡ trận toàn farm (04/09 - 12/09):**
  - Từ 18/08/2026, TikTok cập nhật UI gộp nút Like thành `content-desc="Thích video. X lượt thích"`, khiến code cũ (`== "Thích"`) bị mù.
  - Cả farm lướt feed suốt 26 ngày không hề có 1 like nào (zombie feed).
  - Thuật toán Anti-Abuse (Isolation Forest & GNN) dựa trên tỷ lệ `In-feed engagement / Outbound follow`. Khi tỷ lệ like về 0 trong khi follow vẫn xuất ra, tài khoản rơi vào đuôi phân phối bất thường.
  - Cửa sổ trượt (Sliding Window 14-21 ngày) và hàm phân rã (Decay Factor) tích lũy đủ bằng chứng và áp dụng đồng loạt Dynamic Quarantine (Silent Drop) sau 2-3 tuần.
- **Phục hồi tài khoản:**
  - Không có chuyện "ngâm ngày offline" là tự khỏi. Backend TikTok chỉ ghi nhận qua telemetry hoạt động thực tế.
  - Asymmetric EWMA Recovery: Điểm trust mất nhanh, lấy lại chậm (cần 5-7 ngày lướt feed có like + đăng video đều 48h trên IP proxy mới sạch).

---

## 2. Điểm học tập từ Script GemPhoneFarm (Anh Khoa)
1. **Ad Fast-Skip (Bỏ qua video quảng cáo):**
   - Quét tìm `"Được tài trợ"` / `"Sponsored"`.
   - Nếu gặp: Bỏ qua lập tức trong 0.5s, không like, không dừng xem (tiết kiệm thời gian và tạo tín hiệu người thật).
2. **Pre-like Watch Time:**
   - Khi chọn like: Dừng xem video 4.5s - 16s rồi mới tap like.
   - Sau khi like: Delay 1.5s - 3.8s rồi mới vuốt tiếp.
3. **Phân bổ 3 Tab:**
   - 60% Đề xuất (For You), 20% Đang follow (Following), 20% Bạn bè (Friends).
   - Video mỗi phiên: 14 - 25 video.

---

## 3. Các cải tiến đã áp dụng vào Farm Kibe
1. **Repo `tiktok-luot nuoi acc`:**
   - Fix Like: Prefix match `desc.lower().startswith("thích video")` + `attrib.get("clickable") == "true"`.
   - Nâng thể tích: 16 - 22 video/phiên (Max 28 swipes), nhịp Fast Swipe (2-4s) xen kẽ Deep Inspect (8-15s).
   - Nâng timeout: `DEFAULT_DEVICE_TIMEOUT_SECONDS = 3000.0` (50 phút) để phù hợp thời gian chạy thực tế 28-35 phút/máy.
   - Ad Fast-Skip: Nâng cấp `_is_sponsored_xml` duyệt qua `iter_elements` phát hiện "Được tài trợ" / "Sponsored" để skip ngay.
2. **Repo `tiktok-follow`:**
   - Lớp Warmup sau Cooldown: `is_post_cooldown_warmup` tự động hạ budget xuống 3 - 5 nick/phiên khi nick vừa hết hạn cooldown (`fail_streak > 0` và `follow_failed == False`).
   - Follow thành công xóa sạch streak về 0 (`reset_follow_failed`).
3. **Watchdog Telegram (`feed_session_watchdog.py`):**
   - Tự động cộng dồn số lượt thả tim từ summary của từng máy và xuất báo cáo: `• Lướt Feed (N lượt thả tim)`.

---

## 4. Bài học về tranh luận kỹ thuật & Sự thật khách quan
- CẤM suy diễn hoặc thay đổi lập trường theo cảm tính:
  - Trick "chuyển nick trước ngâm qua đêm" không hề có cơ sở kỹ thuật (idle offline = không có telemetry = không có trust, ngược lại tăng rủi ro stale token và lệch network context khi IP xoay trong đêm).
  - Quy trình chuẩn: Đến giờ ca nào -> Mở app -> Switch đúng nick ca đó -> Lướt feed 15-20 phút (có like) -> Mới thực hiện Follow / Upload.
