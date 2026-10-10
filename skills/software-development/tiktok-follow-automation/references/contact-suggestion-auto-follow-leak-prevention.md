# Phòng ngừa rò rỉ Follow lẻ từ Popup Danh bạ / Bạn bè (Contact Suggestion Auto-Follow Leak Prevention)

## Hiện tượng
Trên Web Dashboard (`tiktok_dashboard.py` / BXH Đã Follow):
- Tài khoản hiển thị: `ĐÃ FOLLOW: X (+1)` (hoặc +2)
- Nhưng: `🔗 Nội bộ: +0`
- Trong khi đó, ca chạy trong log ghi nhận: `status: skipped` (`organic-rest-day-pure-feed` hoặc `under-6-videos-follow-disabled`), và cấu hình feed lướt `follow_rate_percent: 0`.

## Nguyên nhân gốc rễ
1. **Rò rỉ từ Handler Popup trong `automation-core`:**
   - Trong quá trình lướt Feed (đặc biệt khi chuyển tab Bạn bè / Hộp thư / Dành cho bạn), TikTok thường bung popup hoặc in-feed card gợi ý kết bạn: *"Follow bạn bè của bạn"*, *"Bạn bè với [Tên]"*, *"Danh bạ"*, *"Follow bạn"*.
   - Trước đây, trong `src/automation_core/tiktok/benign_popup.py` (`detect_contact_follow_suggestion`) và `src/automation_core/tiktok_popup.py` (`_dismiss_follow_friends_popup`), handler được cấu hình hành vi tiện tay bấm nút "Follow lại" / "Follow" trước khi bấm nút X đóng (pre_action="tap_follow_button" hoặc lặp vòng bấm tối đa 2 người).
2. **Hậu quả vận hành:**
   - Hành vi này **vượt mặt (bypass) hoàn toàn chính sách an toàn của Farm**: Nick đang trong ngày nghỉ dưỡng sinh (`organic rest`), nick yếu chưa đủ 6 video, hoặc nick chưa được cấp phép đi follow chéo vẫn bị tự động bấm follow người lạ ngoài farm.
   - Dẫn đến nguy cơ TikTok phát hiện hành vi bất thường, gây nhả follow (drop follow), tụt trust nick yếu, và làm sai lệch số liệu thống kê follow nội bộ.

## Quy tắc Invariant bắt buộc
1. **CẤM TUYỆT ĐỐI auto-follow từ bất kỳ popup nào:**
   - Toàn bộ handler xử lý popup gợi ý bạn bè, danh bạ (`contact_follow_suggestion`, `follow_friends_suggest_*`) trong `automation-core` **BẮT BUỘC CHỈ ĐÓNG / BỎ QUA** (`dismiss_not_interested_button` hoặc icon Close X `dismiss_close_x`).
   - Tuyệt đối KHÔNG trả về `follow_target` hay `pre_action="tap_follow_button"`.
2. **Quyền hạn Follow duy nhất:**
   - Mọi lượt follow trên Farm **CHỈ ĐƯỢC PHÉP PHÁT SINH DUY NHẤT** từ ca chạy follow chéo nội bộ có kiểm soát do `follow_runner` chỉ định theo hạn mức quota ngày (Graduated Probation Ladder & Sweet Spot Quota).
