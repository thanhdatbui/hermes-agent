# Comment/Feed Input Overlay & Virtual Keyboard Handling

## Bối cảnh & Hiện tượng
- Khi thiết bị đang lướt Feed TikTok, vô tình chạm trúng thanh bình luận hoặc nút trả lời tin nhắn khiến thanh nhập liệu (`EditText`) được focus và bàn phím ảo (Samsung Keyboard / AOSP IME) nổi lên che toàn bộ nửa dưới màn hình (`y >= 1050`).
- Mặc dù trước đó đã có các bộ nhận diện popup hay story reply, phiên chạy vẫn bị dừng và báo lỗi `unknown TikTok state` hoặc `swipe recovery (2 swipes) still stuck`.

## Nguyên nhân gốc rễ
1. **Khoảng trống nhận diện (Detection Gap):**
   - Bộ nhận diện `detect_story_quick_reaction_overlay` có điều kiện Negative Exclusion loại trừ các từ khóa bình luận (`comment_list`, `thêm bình luận`, `add a comment`) nhằm tránh match nhầm màn hình bình luận chuyên biệt.
   - Do đó, khi thanh nhập bình luận/tin nhắn feed kèm bàn phím ảo xuất hiện, nó không được khớp với Story reply handler.
2. **Bàn phím che khuất thanh điều hướng đáy làm Classifier rớt về `unknown`:**
   - Bàn phím ảo chiếm từ `y ≈ 1050` đến `y = 1920`, che khuất hoàn toàn các tab điều hướng (*Trang chủ*, *Hồ sơ*).
   - `core/classifier.py` không tìm thấy marker feed hợp lệ và phân loại màn hình là `unknown` $\rightarrow$ `safety.py` kích hoạt `unknown TikTok state`.
3. **Cơ chế Swipe Recovery bị vô hiệu hóa:**
   - Khi bị stuck/unknown, `_swipe_recovery_on_stuck` thực hiện swipe với tọa độ bắt đầu `y = 1600` (nằm ngay giữa bàn phím). Thao tác vuốt trên bàn phím không làm cuộn feed và cũng không làm tắt bàn phím $\rightarrow$ sau 2 lần swipe màn hình giữ nguyên trạng thái và runner dừng phiên.

## Quy chuẩn Xử lý (Standard Solution)
1. **Đăng ký `comment_input_overlay` vào `BENIGN_POPUP_REGISTRY` (Priority ~77):**
   - File: `python_runner/flows/benign_popup_registry.py`.
   - **Positive Markers:**
     - `EditText` đang có `focused="true"` trong package TikTok (`com.ss.android.ugc.trill` / `com.zhiliaoapp.musically`).
     - Bàn phím ảo đang hiển thị (`honeyboard`, `inputmethod`, `latin`, `swiftkey`) HOẶC có controls comment (icon emoji, nút gửi, resource-id `comment_input`, `et_comment`, `msg_edit_text`...).
   - **Negative Exclusions (BẮT BUỘC):**
     - Loại trừ màn hình Login: `login_email`, `login_password`, `btn_login`, `đăng nhập`, `log in`.
     - Loại trừ OTP: `otp_input`, `verification_code`, `mã xác minh`, `enter code`.
     - Loại trừ CAPTCHA / Security: `captcha`, `puzzle`, `xác minh bảo mật`, `security check`.
     - Loại trừ Edit Name: `thêm tên bạn mong muốn`, `bạn chỉ có thể đổi tên một lần mỗi 7 ngày`.
   - **Dismisser:**
     - Gửi 1 phím `BACK` qua `send_device_back_key(ctx)` để hạ bàn phím và thoát focus input.
     - Kiểm tra lại hierarchy, nếu vẫn còn overlay thì gửi tiếp phím `BACK` lần 2.
2. **Liên kết Classifier với Registry:**
   - File: `python_runner/core/classifier.py`.
   - Bổ sung `detect_comment_input_overlay(root)` trả về `manual-needed:popup` để dispatcher popup gọi handler xử lý tự động thay vì rớt về `unknown`.
3. **Bảo vệ `_swipe_recovery_on_stuck`:**
   - File: `python_runner/flows/feed_swipe_smoke.py`.
   - Trước khi thực hiện swipe cứu kẹt, kiểm tra nếu `detect_keyboard_state(ctx).visible` thì chủ động gửi `input keyevent BACK` để hạ bàn phím trước.
   - Điều chỉnh tọa độ bắt đầu swipe từ `y=1600` lên `y=1450` để tránh vùng dock/navigation bar.
