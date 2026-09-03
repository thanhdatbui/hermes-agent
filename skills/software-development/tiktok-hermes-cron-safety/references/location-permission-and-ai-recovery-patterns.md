# AI Auto-Recovery & TikTok Location Permission Bypass

## 1. Màn hình popup quyền vị trí TikTok (Location Permission Dialog)
- **Tiêu đề:** "Xem nội dung phù hợp và địa điểm lân cận" (English: "See relevant content and nearby places").
- **Nội dung:** "Mở cài đặt thiết bị của bạn và truy cập Vị trí > Trong khi sử dụng ứng dụng. Bạn có thể tắt bất cứ lúc nào." (English: "Open device settings and set location > while using the app...").
- **Các nút điều khiển:**
  - `android:id/button3`: "Hủy" / "Cancel" (clickable, enabled)
  - `android:id/button1`: "Mở cài đặt" / "Open settings" (clickable, enabled)

## 2. Quy tắc bypass an toàn (Benign Popup Allowlist)
- **Hành động chuẩn:** Click nút `Hủy` (`android:id/button3`) để dismiss popup an toàn, KHÔNG bấm "Mở cài đặt" (tránh bị văng sang Settings thiết bị).
- **Ràng buộc Scope khi Detect:**
  - Bắt buộc kiểm tra cả 4 tín hiệu (Title, Message Body, Settings Button `button1`, Cancel Button `button3`).
  - Tất cả các control phải thuộc cùng một FrameLayout / Modal Dialog Container của TikTok package (`com.ss.android.ugc.trill`).
  - Nút `Hủy` và `Mở cài đặt` phải là sibling button trong button panel của dialog để tránh click nhầm `button3` của dialog khác.
  - Priority: Location permission dialog là blocking modal foreground nên được ưu tiên nhận diện trước khi xử lý các background CTA overlays (Shop CTA, Add-phone).

## 3. Quy trình AI Auto-Recovery tự động:
1. Khi máy bị dừng phiên, bot gửi alert ảnh banner đỏ lên Telegram.
2. Background AI Agent (`python_runner/ai_recovery/agent.py`) được spawn:
   - Vision AI phân tích ảnh hiện trường + UI XML.
   - Code-First: Tự động vá rule/detector mới vào `core/benign_popup.py` hoặc `flows/feed_swipe_smoke.py`.
   - Chạy Plan-Review Audit (9Router / Terra) + Pytest regression suite.
   - Khi vượt qua audit & test, thực thi lệnh ADB giải phóng màn hình máy kẹt và gửi báo cáo kết quả gỡ kẹt lên nhóm Telegram.

## 4. Pitfalls & Lessons từ AI Auto-Recovery:
- **Pitfall Trùng Lặp Handler (Dead Code Appending):**
  - Khi auto-recovery vá thêm handler thoát màn hình mới (ví dụ: màn hình camera/tạo video, popup đề xuất bạn bè...), handler **bắt buộc phải được đấu nối/đăng ký vào dispatcher trung tâm** (`dismiss_any_popup` trong `benign_popup.py` hoặc bộ `classifier.py`), không chỉ append hàm rời ở cuối file.
  - Nếu chỉ định nghĩa hàm ở cuối file mà không nối vào luồng dispatch, các phiên chạy sau của các máy khác sẽ vẫn bị coi là màn hình kẹt chưa có giải pháp ➔ AI Recovery lại tiếp tục sinh thêm hàm trùng lặp (`dismiss_tiktok_camera_screen`, `dismiss_camera_creation_screen`, v.v.).
- **Windows Exit Code 3221226091 (0xC000026B - STATUS_DLL_INIT_FAILED_LOGOFF):**
  - Khi Hermes Gateway tiến hành restart/reload trong lúc một cron job script (`tiktok_watcher.py`, `tiktok_runner.py`) đang chạy, tiến trình con bị ngắt ngang bởi hệ điều hành và trả về exit code 3221226091.
  - Đây là lỗi do restart Gateway cắt ngang execution, không phải bug logic trong script hay config sai. Kiểm tra lại script trực tiếp để xác nhận exit code 0.

