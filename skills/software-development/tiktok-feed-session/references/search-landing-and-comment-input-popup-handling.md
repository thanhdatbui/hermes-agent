# Search Landing Page & Comment Input Overlay Handling in TikTok Feed Session

## 1. Màn hình Tìm kiếm / Gợi ý Tìm kiếm (Search Landing Page)

### Hiện tượng & Cơ chế gây lỗi:
Khi chạy feed session hoặc chuyển hướng, TikTok vô tình bị chạm vào thanh tìm kiếm hoặc gợi ý tìm kiếm:
- **Nguyên nhân chạm nhầm từ Feed:** Tọa độ bắt đầu vuốt `BASE_SWIPE_START = (450, 1540)` rơi trúng dải `y = 1400 - 1650` nơi TikTok hiển thị **Search Pill (Gợi ý tìm kiếm)** đè trên mô tả video (ví dụ: `🔍 Cute Dog Videos`, `🔍 hài hước`...) hoặc chạm nhầm icon kính lúp ở góc trên bên phải.
- Giao diện có thanh tìm kiếm ("Tìm kiếm", `EditText`), banner thưởng tích điểm, danh sách "Tìm kiếm gần đây", "Bạn có thể thích", "Nội dung tìm kiếm thịnh hành".
- Góc trên bên trái có nút Back `←` (`[0, 50][150, 200]`).
- Do thiếu handler phân loại, `classifier.py` trả về `unknown` $\rightarrow$ `safety.py` báo `unknown TikTok state` và dừng phiên dạng fail-closed giữ nguyên hiện trường.
- **Lý do `_swipe_recovery_on_stuck` thất bại:** Cứu kẹt bằng vuốt dọc (`input swipe 540 1450 540 400`) chỉ làm cuộn danh sách từ khóa tìm kiếm trên Search Landing chứ không thoát được trang.

### Giải pháp chuẩn:
1. **Tránh chạm nhầm khi Swipe Feed:** Dời điểm bắt đầu vuốt `BASE_SWIPE_START` lên dải an toàn `y = 1380` (kết thúc tại `y = 480` trên chuẩn màn hình 1080x1920 portrait). Điểm chạm ngón `y = 1380` (jitter `1350 .. 1410`) nằm hoàn toàn ở vùng video trống phía trên dải tương tác khi bàn phím đang đóng (`y >= 1485`), triệt tiêu việc vô tình chạm vào Search Pill hay thanh tin nhắn/bình luận ở đáy.
2. **Negative Exclusions:** Bắt buộc loại trừ nếu màn hình chứa các trường của Profile (`Đã follow`, `Follower`, `Sửa hồ sơ`...), Camera/Video Creation, Thêm số điện thoại (`+84`), Xác minh OTP/CAPTCHA, Đăng nhập/Mật khẩu.
3. **Positive Markers:**
   - Section keywords: `"bạn có thể thích"`, `"you may like"`, `"tìm kiếm gần đây"`, `"nội dung tìm kiếm thịnh hành"`, `"gợi ý tìm kiếm"`, `"trending searches"`, `"hỏi ai"`.
   - Kết hợp `has_search_button` ("Tìm kiếm", "Search") hoặc `has_search_input` (`EditText` / resource-id chứa `search_input`).
4. **Dismisser Action:**
   - Ưu tiên tap nút Back `←` ở góc trên bên trái `[0, 50][150, 200]`.
   - Fallback: gửi keyevent `BACK` và sleep 1.0s để TikTok trượt về lại FYP Home Feed.
5. **Cứu kẹt trong `_swipe_recovery_on_stuck`:** Khi phát hiện màn hình là Search Landing hoặc overlay trong registry, bắt buộc gọi handler registry (`_dismiss_search_landing` để tap nút Back hoặc gửi keyevent `BACK`) trước khi thực hiện swipe.
6. **Chống lỗi Recapture Unavailable trong `dismiss_any_popup`:** Khi dispatch qua `BENIGN_POPUP_REGISTRY`, nếu dismisser trả về `PopupDismissResult` không chứa `after_attempt`, hàm gọi (`dismiss_any_popup` / `dismiss_allowed_generic_popup`) bắt buộc thực hiện `capture_calibration_attempt` để bổ sung `after_attempt`, ngăn chặn lỗi fail-closed `"popup dismiss reported success but recapture was unavailable"`.
7. **Registry Priority:** Đăng ký vào `BENIGN_POPUP_REGISTRY` với priority 84 (`search_landing_overlay`).

---

## 2. Thanh nhập Bình luận / Tin nhắn Feed kèm Bàn phím ảo (Comment/Feed Input Overlay / Quick Reply Dialog)

### Hiện tượng & Cơ chế gây lỗi:
- Khi lướt feed, vô tình chạm vào vùng nhập bình luận / nhắn tin nhanh làm bàn phím ảo nổi lên che nửa dưới màn hình (`y >= 1050`).
- **Nhận diện kỹ thuật (Fragment & Window):** TikTok kích hoạt fragment `IMUnifiedQuickInputDialogFragment` (tag `IMUnifiedQuickInputDialogFragment`) và gắn `PopupWindow` lên `SplashActivity`, làm tối nửa trên màn hình (`FrameLayout id/tco` hoặc scrim) và kích hoạt bàn phím Samsung (`com.sec.android.inputmethod`).
- **Cấu trúc UI XML đặc trưng:**
  - Nút máy ảnh: `resource-id="com.ss.android.ugc.trill:id/de6"` (`desc="Mở máy ảnh"`).
  - Ô nhập liệu: `class="android.widget.EditText"` nằm trong `FrameLayout id/l87` (hoặc `l86`).
  - Nút Emoji/GIF: `resource-id="com.ss.android.ugc.trill:id/koe"` (`desc="Mở nhãn dán, GIF và biểu tượng cảm xúc"`).
  - Nút gửi: `resource-id="com.ss.android.ugc.trill:id/l8c"` (`desc="Gửi"`).
- **Hiện tượng gõ chuỗi ký tự lạ (như "55554", "454"):** Khi touch-down ban đầu của lệnh vuốt (`start_y = 1540 - 1550`) chạm trúng thanh input ở đáy feed, `IMUnifiedQuickInputDialogFragment` bật lên tức thì. Đoạn kéo dài ngón tay tiếp theo trong cử chỉ vuốt (`x ≈ 424..450, y ≈ 1250`) kéo thẳng qua hàng phím số `5` và `4` trên bàn phím Samsung/Gboard, kích hoạt gõ liên tiếp các ký tự số (ví dụ `"55554"`, `"454"`) vào ô `EditText`.
- Bàn phím che toàn bộ thanh điều hướng đáy làm classifier không thấy tab Home/Profile $\rightarrow$ báo `unknown TikTok state` $\rightarrow$ cơ chế an toàn dừng phiên dạng `preserve_blocker_screen` để giữ nguyên hiện trường.

### Cơ chế gây lỗi False-Positive trên FYP Feed (Sự cố Máy 56 ngày 29/08/2026):
- Quét từ khóa lỏng lẻo (`"bình luận"`, `"comment"`, `"viết bình luận"`) khớp trúng nút bấm mở bình luận trên action bar phải của video FYP (`desc="Đọc hoặc viết bình luận. Bóc tem bình luận"`), kết hợp với `has_comment_controls` khớp `"gửi"` (nút gửi/nhắn tin trên thanh tác vụ), dẫn tới `has_comment_input and has_comment_controls` trả về `True` dù KHÔNG có bàn phím ảo (`keyboard_detected == False`) và KHÔNG có ô nhập liệu focus (`has_focused_input == False`).
- Thiếu Negative Exclusions loại trừ màn hình Bảng tin / FYP chuẩn (`Trang chủ` + `Hồ sơ` / `Hộp thư`).
- **Hệ quả:** Sau khi vuốt video (Swipe 1), classifier phân loại nhầm màn hình Feed FYP thành `manual-needed:popup` với reason `['comment input / story reply overlay marker present']`, dừng toàn bộ phiên và kích hoạt `status: blocked`.

### Giải pháp chuẩn:
1. **Thứ tự ưu tiên trong Registry (Priority Resolution):** Đăng ký `search_landing_overlay` với Priority 84 cao hơn `comment_input_overlay` (Priority 77) để xử lý dứt điểm màn hình tìm kiếm qua nút Back ngữ nghĩa trước khi xét đến comment input.
2. **Negative Exclusions bắt buộc cho FYP / Feed & Profile Navigation (Scoping strictly to `tiktok_nodes`):**
   - **Sự cố Máy 68 (30/08/2026):** Vòng lặp kiểm tra `login_exclusions` (`"đăng nhập"`), `otp_exclusions` (`"mã xác minh"`), `security_exclusions` và `search_terms`/`profile_terms` BẮT BUỘC chỉ quét trên `tiktok_nodes` (`com.ss.android.ugc.trill` / `com.zhiliaoapp.musically`), TUYỆT ĐỐI KHÔNG duyệt qua `com.android.systemui` hay toàn bộ `nodes`. Nếu duyệt toàn bộ, notification của Google Play trên thanh trạng thái (*"Thông báo của Dịch vụ Google Play: Yêu cầu đăng nhập"*) sẽ làm detector trả về `False` ngay lập tức, vô hiệu hóa toàn bộ cơ chế cứu kẹt comment overlay.
   - Nếu màn hình có thanh điều hướng đáy (`Trang chủ` + `Hồ sơ`/`Hộp thư`/`Cửa hàng`) hoặc tab đầu trang (`Đề xuất`/`Bạn bè`/`Đã follow`) VÀ không có bàn phím ảo (`keyboard_detected == False`) VÀ không có `EditText` focus (`has_focused_input == False`) $\rightarrow$ Bắt buộc trả về `False`. Loại trừ thêm form Login, OTP, CAPTCHA, Edit name.
3. **Khử False-Positive trong `_detect_camera_creation` (Priority 90):**
   - Sử dụng detector canonical `detect_keyboard_from_xml` để kiểm tra trạng thái hiển thị bàn phím ảo (`kb_state.visible`).
   - Nếu có bàn phím ảo, chỉ coi là Camera creation overlay khi có các marker tạo nội dung/quay chụp rõ ràng (Text creation mode với `shortvideo`, `record_layout`, hoặc kết hợp shoot modes `15s`/`60s`/`templates`).
   - Scoping package: Trích xuất danh sách node qua `_get_tiktok_app_nodes(root)` với strict allowlisting `_TIKTOK_PACKAGES` (`com.ss.android.ugc.trill`, `com.zhiliaoapp.musically`, `com.ss.android.ugc.aweme`), loại trừ triệt để `_NON_TIKTOK_SYSTEM_PACKAGES` (GMS, IME, Launcher, Settings, PermissionController, Vending). Khi XML thuộc app khác ngoài TikTok thì lập tức trả về `False`, không ghép OCR text.
   - Multi-window guard: Khi có dialog foreground từ app khác (GMS, PermissionController, Settings, Vending) đang focused hoặc clickable, tuyệt đối không match Camera creation overlay, ngăn chặn rò rỉ OCR text từ dialog hệ thống vào detector camera của TikTok background.
4. **Loại trừ Search & Profile Editors:** Bắt buộc loại trừ các ID tìm kiếm (`search_src_text`, `et_search`, `search_box`) và chỉnh sửa bio/profile (`edit_bio`, `sửa hồ sơ`, `edit_profile`) khỏi nhận diện comment overlay trừ khi có bằng chứng comment cụ thể (`has_comment_evidence == True`).
5. **Loại trừ Container & Button tĩnh:** Bỏ qua các resource-id nút bấm (`_button`, `_btn`, `btn`) và các container tĩnh chung chung (`comment_container`, `comment_list`, `comment_panel`) khỏi positive marker của ô nhập comment.
6. **Bắt buộc điều kiện Input / Keyboard:** Chỉ coi là Comment Input Overlay khi có bằng chứng comment cụ thể (`has_comment_evidence == True`) kết hợp với:
   - `EditText` trong TikTok đang `focused == True` HOẶC bàn phím ảo hiển thị (`keyboard_detected == True`).
   - HOẶC layout nhập bình luận cụ thể (`comment_input_layout`, `comment_reply_et`, `comment_input`) kết hợp với `EditText` / controls gửi / emoji.
7. **Thu hẹp danh sách từ khóa:** Loại bỏ các từ đơn chung chung (`"bình luận"`, `"comment"`, `"trả lời"`, `"reply"`), chỉ giữ các placeholder/hint nhập liệu rõ ràng (`"thêm bình luận"`, `"nhập bình luận"`, `"add a comment"`, `"để lại bình luận"`, `"say something"`), và bỏ qua các node là Button (`class="android.widget.Button"`) mở danh sách bình luận (`"đọc hoặc viết bình luận"`).
8. **Dismisser Action 2 nhịp & Hậu kiểm:**
   - Bước 1: Gửi 1 phím `BACK` để hạ bàn phím và unfocus input.
   - Bước 2: Chờ 0.8s kiểm tra lại hierarchy nếu còn overlay (`detect_comment_input_overlay == True`) thì gửi tiếp phím `BACK` thứ 2 để thoát dứt điểm về lại FYP Home Feed.

---

## 3. Quy tắc Thiết kế An toàn trong Vòng lặp Phục hồi (`_swipe_recovery_on_stuck`)

### A. Chống Đè Phím Back (Double-Dismiss Race Condition):
- Nếu handler dismisser từ registry (ví dụ `_dismiss_comment_input` hoặc `_dismiss_search_landing`) đã gửi lệnh Back / tap Back thành công (`handler_dismissed == True`), **KHÔNG ĐƯỢC** gửi thêm phím Back thứ hai trong nhánh dọn dẹp bàn phím trước khi chụp lại màn hình.
- Việc gửi 2 phím Back liên tiếp trong cùng 1 nhịp sẽ đẩy ứng dụng TikTok ra màn hình chính (Launcher) và làm hỏng toàn bộ phiên lướt.

### B. Kiểm Tra Màn Hình Nhạy Cảm Toàn Diện (Fail-Closed Sensitive Protection):
- **3 Giai đoạn kiểm tra:** (1) Trước khi vào vòng lặp recovery (trên `row` và initial XML/OCR), (2) Trước mỗi nhịp vuốt (pre-swipe inspection), và (3) Sau khi dismiss/vuốt (post-swipe / post-dismiss recapture).
- **Phạm vi token nhạy cảm:** Bao gồm cả classification tag (`manual-needed:login`, `manual-needed:verification`, `manual-needed:captcha`, `manual-needed:security`, `manual-needed:manual_challenge`, `manual-needed:otp`) và các chuỗi text/resource-id trong XML và OCR (`login_password`, `et_password`, `password_input`, `captcha`, `puzzle`, `xác minh bảo mật`, `security check`, `sec_check`, `verify_bar`, `mã xác minh`, `verification_code`, `enter code`, `nhập mã`, `đăng nhập`, `log in`, `sign up`, `đăng ký`, `quen_mat_khau`, `forgot password`).
- **Hành động khi phát hiện:** Lập tức ghi log `sensitive_screen_abort` và trả về `None` (fail-closed), **TUYỆT ĐỐI KHÔNG** thực hiện swipe hay gửi phím Back.

### C. Cô Lập XML và Attempt Giữa Các Lần Thử (Iteration Isolation):
- Luôn khởi tạo lại `xml_path_val = None` và `xml_text = None` ở đầu mỗi vòng lặp `for i in (1, 2)`.
- Ở lần thử $i=1$, nếu không có XML tươi từ dismisser thì mới đọc từ `row.get("xml_path")`.
- Ở lần thử $i > 1$, bắt buộc chỉ đọc XML từ `current_attempt` vừa chụp sau nhịp vuốt trước đó, tuyệt đối không dùng lại `row.get("xml_path")` cũ để tránh vòng lặp xử lý stale XML.
