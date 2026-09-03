# Story Quick Reply Overlay & Soft Keyboard Feed Stuck Pattern

## Triệu chứng
- Alert từ `multi-machine-feed-session` hoặc `feed-session-smoke`:
  - `Lý do: unknown TikTok state; swipe recovery (2 swipes) still stuck`
  - `Trạng thái: 🟡 GIỮ HIỆN TRƯỜNG ĐỂ HERMES AGENT XỬ LÝ`
- Ảnh hiện trường trên máy (ví dụ Samsung S7):
  - Hiển thị video Story (Tin) TikTok.
  - Phía dưới là panel 8 biểu cảm nhanh (Quick Reactions emoji: 😎, 🤣, 😳, 🥰, ❤️, 👏, 🔥, 🎆).
  - Thanh nhập tin nhắn: `Nhắn tin cho [username]...` / `Send a message...` / `Reply to...`.
  - Bàn phím ảo Samsung Keyboard (`com.sec.android.inputmethod` hoặc `com.samsung.android.honeyboard`) tự động bung lên chiếm nửa dưới màn hình (Y: ~1000 - 1920).

## Nguyên nhân gốc (Root Cause)
1. **Focus tự động / Touch trúng thanh input:** Khi feed chuyển qua video định dạng Story hoặc touch rơi vào vùng đáy video, TikTok kích hoạt chế độ trả lời nhanh Story và tự động focus vào EditText.
2. **Bàn phím ảo chặn Touch Event:** Khi soft keyboard hiển thị, mọi thao tác vuốt feed cơ bản (`input swipe 540 1600 540 400 300` hoặc `450 1540 450 620`) có điểm bắt đầu (Y: 1540 - 1600) nằm trọn trong vùng bàn phím ảo. Bàn phím hấp thụ toàn bộ touch event, ngăn cản feed cuộn lên.
3. **Classifier Miss & Recovery Stuck:**
   - Giao diện bị bàn phím và panel emoji che khuất khiến UI tree không khớp `for-you` / `feed` marker -> rơi vào `unknown TikTok state`.
   - Cơ chế `swipe_recovery_on_stuck` cố gắng swipe 2 lần bằng toạ độ chuẩn nhưng vẫn chạm vào bàn phím -> thất bại và kích hoạt safety stop giữ nguyên hiện trường.

## Quy trình xử lý & Phục hồi (Recovery Protocol)
1. **Phát hiện (Detection):**
   - Kiểm tra text/content-desc chứa các marker story reply: `nhắn tin cho`, `send a message`, `reply to`, `gửi tin nhắn`.
   - Kiểm tra trạng thái bàn phím ảo qua `dumpsys input_method` (`mInputShown=true`) hoặc presence của IME package (`com.sec.android.inputmethod` / `com.samsung.android.honeyboard`).
2. **Thoát overlay an toàn (Dismissal Ladder):**
   - **Bước 1 (Đóng bàn phím):** Bấm phím cứng `KEYCODE_BACK` (keyevent 4) một lần để thu gọn bàn phím ảo.
   - **Bước 2 (Thoát Quick Reaction overlay):** Bấm tiếp `KEYCODE_BACK` lần thứ 2 hoặc chạm vào vùng màn hình phía trên (Y < 800) để đóng overlay phản hồi nhanh.
   - **Bước 3 (Verify feed):** Capture lại UI XML và screenshot, xác nhận đã quay về feed chuẩn (`for-you` / `feed` video player) trước khi tiếp tục chu kỳ vuốt.
