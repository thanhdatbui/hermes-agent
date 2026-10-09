# Unconditional Dismiss Feed Follow Suggestions & Popup Invariant (07/10/2026)

## 1. Bối Cảnh & Sự Cố Phát Hiện
- Trên Farm Admin (máy 201–280, ví dụ máy 231 lúc 18:28), phát hiện máy tự bấm "Follow lại" một tài khoản trên Feed (`Thuỳ Vietlove Travel`) và hiển thị popup gợi ý bạn bè.
- Mặc dù luồng Follow chéo (`tiktok-follow`) có Gate chặn cứng 100% đối với các nick chưa đủ điều kiện (`under-6-videos-follow-disabled` / `under-21-days-follow-disabled` / Dual Gate `age>=30d, vid>=10`), nhưng tài khoản vẫn bị bấm follow trong phiên lướt feed.

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
1. **Lỗ hổng phân nhánh trong Popup Handler (`benign_popup.py` & `feed_swipe_smoke.py`):**
   - Trong `benign_popup.py` (`dismiss_follow_friends_suggestion_popup`), biến `follow_limit` trước đây được gán: `follow_limit = 0 if in_cooldown else 2`. Nick không dính cooldown bị bấm follow 1–2 người trước khi đóng popup.
   - Trong `feed_swipe_smoke.py` (`_gem_blind_action`, rule `follow_back_suggestion` - Case 165), chỉ kiểm tra `is_account_in_follow_cooldown`. Nick sạch bị tap vào nút "Follow lại" / "Theo dõi lại" (`resource-id: ct3`).
2. **Hậu quả của việc Follow Mù trên Feed / Popup:**
   - **Không kiểm soát & không verify:** Khác với `tiktok-follow` có quy trình ngâm video, pull-to-refresh profile để kiểm tra nhả nút và ghi nhận `follow_state.json`, bấm trên popup/thẻ feed là bấm mù 100%.
   - **Cháy hạn mức hành vi (Burst Velocity Limit):** Bấm follow vãng lai làm TikTok gắn cờ tài khoản spam, đến khi chuyển sang chạy Follow chéo nội bộ thì nick bị TikTok Silent Action Block (nhả nút đỏ diện rộng).
   - **Lệch đối soát Watchdog:** Gây lệch âm giữa số follow script ghi nhận và số liệu cào TikTok Web.

## 3. Quy Tắc Bất Biến: Unconditional Dismiss (Cấm Tuyệt Đối Follow Trên Feed / Popup)
User đã chốt quy tắc xử lý dứt điểm: **Luôn luôn bấm "Không quan tâm" / Đóng X cho TẤT CẢ các tài khoản, tuyệt đối cấm bấm Follow lại trên Feed / Popup**.

### A. Thẻ Đề Xuất Trên Feed (`follow_back_suggestion` trong `feed_swipe_smoke.py`):
- Luôn luôn tìm và tap nút **"Không quan tâm"** (`resource-id="com.ss.android.ugc.trill:id/cv6"` hoặc text/desc `"Không quan tâm"`).
- Tuyệt đối không phân nhánh bấm detector node ("Follow lại").

### B. Popup Gợi Ý Bạn Bè (`dismiss_follow_friends_suggestion_popup` trong `benign_popup.py`):
- Đặt cứng `follow_limit = 0`.
- Luôn luôn tìm nút đóng ngữ nghĩa (icon X, id `:id/close`, `:id/c3t`), hoặc Back để thoát popup sạch sẽ.

### C. Phân Vai Rạch Ròi 100%:
- **Lướt Feed (`tiktok-luot nuoi acc`):** Chỉ thực hiện hành vi người dùng thuần túy (xem video, thả tim, xem comment, dọn dẹp popup an toàn).
- **Follow:** ĐỘC QUYỀN do repo `tiktok-follow` quản lý (có budget, ngâm video, post-verify pull-to-refresh và lưu state đầy đủ).
