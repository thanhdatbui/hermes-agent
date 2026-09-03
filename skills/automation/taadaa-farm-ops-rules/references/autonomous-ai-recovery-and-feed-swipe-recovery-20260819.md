# Quy Chuẩn Autonomous AI Recovery, Vuốt Retry Cứu Hộ & Vận Hành Farm (19/08)

## 1. Kiến Trúc Autonomous AI Recovery (Producer - Agent - Vision/Audit)
1. **Producer (Script Farm - 0 Token LLM)**:
   - Khi phát hiện máy lỗi/kẹt: Chụp ảnh hiện trường, vẽ **Banner Đỏ `[MAY XX] - HH:MM DD/MM`** ở đỉnh ảnh.
   - Gửi Tin nhắn 1 vào nhóm Telegram **Farm Alerts** (`-5373649734`).
   - **Bắt buộc giữ nguyên hiện trường**: Không tắt app, không bấm Home.
   - Spawn tiến trình nền độc lập: `python -m ai_recovery.agent --machine XX --serial ...`
2. **Autonomous Agent (`ai_recovery.agent`) - Quy Trình 5 Bước Bắt Buộc**:
   - **Bước 1 (Pre-check Live)**: Kiểm tra thiết bị còn online qua ADB. **CẤM so sánh pHash giữa 2 frame video động** (video feed, livestream, ads luôn đổi frame nên pHash chắc chắn lệch; so sánh pHash sẽ làm agent ngây thơ tưởng màn hình đã đổi và bỏ qua recovery).
   - **Bước 2 (AI Suy luận & Viết Code TRƯỚC)**: Nạp ảnh + XML vào Model Vision (`ag/claude-opus-4-6-thinking` qua 9Router port 20128). AI phân tích bản chất kẹt và viết code handler/rule mới cho `feed_swipe_smoke.py` / `benign_popup.py`.
   - **Bước 3 (Thẩm định Plan-Review độc lập)**: Gọi Model Plan-Review (`gpt-5.6-terra` / Claude CLI `--effort max`) audit `git diff` và chấm `VERDICT: APPROVED`.
   - **Bước 4 (Chạy trực tiếp hàm vừa code lên máy đang kẹt tại hiện trường)**: Kích hoạt chính logic vừa sửa trên máy lỗi tại hiện trường. Chụp ảnh xác minh sau khi chạy xem máy đã vượt qua màn hình kẹt hay chưa (CẤM chạy lại từ đầu).
   - **Bước 5 (Commit & Báo cáo Tin nhắn 2)**: Chạy test suite `pytest` xác nhận không có lỗi hồi quy -> `git commit & push origin master` -> Bắn Tin nhắn 2 (*Hướng sửa & Kết quả*) vào Farm Alerts.

## 2. Cơ Chế Vuốt Retry Cứu Hộ (Tối Đa 2 Lần Swipe) Trong Vòng Lặp Feed Chính
- **Vấn đề**: Trước đây khi gặp popup/quảng cáo/CTA lạ trong vòng lặp lướt video, script lập tức dán nhãn `manual-needed` và gọi `finalize_feed_session_cleanup()` dừng phiên ngay.
- **Quy tắc chuẩn**:
  - Tại bất kỳ bước nào trong vòng lặp feed, nếu gặp màn hình lạ/popup không nhận diện được:
  - **Miễn là KHÔNG PHẢI màn hình nhạy cảm (`manual-needed:login`, `login-overlay`, `verification`, `captcha`, `security`, `manual_challenge`)**:
  - Tự động kích hoạt cơ chế `_swipe_recovery_on_stuck` vuốt lên (swipe) tối đa 2 lần để lướt qua video tiếp theo.
  - Nếu sau khi vuốt mà phát hiện đã sang feed bình thường -> Khôi phục `SUCCESS`, reset `_swipe_recovery_used = False`, trừ biến đếm quota video và tiếp tục nuôi acc.

## 3. Khóa Xoay Màn Hình Kép (Dual-layer Lock) Chống Samsung OneUI Tự Xoay
- **Hiện tượng**: Samsung OneUI / TouchWiz ngầm tự kích hoạt `accelerometer_rotation = 1` khi phát hiện video ngang hoặc khi máy bị rung lắc.
- **Xử lý bắt buộc**: Mọi hàm `lock_portrait_rotation` và `ensure_portrait_rotation` phải chạy cả lệnh `settings put` lẫn ghi đè trực tiếp vào Content Provider:
  ```bash
  settings put system accelerometer_rotation 0
  settings put system user_rotation 0
  content insert --uri content://settings/system --bind name:s:accelerometer_rotation --bind value:i:0
  content insert --uri content://settings/system --bind name:s:user_rotation --bind value:i:0
  ```

## 4. Xử Lý Khi Nick Bị Nhả Follow (`FOLLOW_FAILED`)
- Khi phát hiện nick bị TikTok nhả follow sau khi vuốt pull-to-refresh xác nhận:
  1. Ghi nhận `follow_failed = True` và `follow_failed_date = YYYY-MM-DD` cho riêng nick đó (`follow_state_<m>_row_<r>.json`).
  2. Dừng toàn bộ các lượt follow tiếp theo của nick đó trong ngày.
  3. **Tự động đóng hoàn toàn ứng dụng TikTok, xóa danh sách app gần đây (Clear Recent Apps) và đưa máy về màn hình chính (Home) sạch sẽ.**

## 5. Xử Lý Kẹt Bàn Phím / Overlay Khi Mở Account Switcher (Máy 21)
- Khi tap vào header profile để đổi nick nhưng switcher không mở (do kẹt bàn phím ảo / overlay bình luận):
- Tự động gửi phím `BACK` (keyevent 4) để hạ bàn phím/overlay -> Thử tap lại vào switch_anchor -> Chụp lại XML để tiếp tục luồng chuyển nick.

## 6. Xử Lý Màn Hình Startup Recents Rỗng (Máy 35)
- Khi dọn app đầu phiên mà màn hình Recent Apps không có nút "Đóng tất cả" (do máy đã sạch sẵn) -> Tự động gửi phím Home và coi như thành công, tuyệt đối không được ném lỗi ngắt phiên.

## 7. Cấu Hình 9Router API Key
- `NINEROUTER_API_KEY` được lấy từ cơ sở dữ liệu `C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite` (bảng `apiKeys`).
- Bắt buộc ghi đúng key vào `C:\Users\Kibe\AppData\Local\hermes\.env` để các module `vision_client.py` và `plan_reviewer.py` kết nối trực tiếp vào port 20128 mà không bị rơi vào fallback.
