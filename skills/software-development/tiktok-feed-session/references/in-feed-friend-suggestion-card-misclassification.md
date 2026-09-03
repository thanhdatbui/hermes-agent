# In-Feed Friend / Contact Suggestion Card Misclassification

## Hiện tượng
Máy dừng phiên với cảnh báo:
`🚨 [MÁY XX] DỪNG PHIÊN`
`• Script: multi-machine-feed-session`
`• Lý do: unexpected popup/dialog marker detected`
`• Trạng thái: 🟡 GIỮ HIỆN TRƯỜNG ĐỂ HERMES AGENT XỬ LÝ`

Ảnh hiện trường hiển thị video feed bình thường trên tab `Đề xuất` (hoặc `Bạn bè`), bên dưới có thẻ đề xuất gắn trực tiếp trên video:
- Tag/prefix: `Bạn bè với ...`
- Tên tài khoản tác giả / nút: `com.ss.android.ugc.trill:id/title`
- Hai nút hành động: `Không quan tâm` (`:id/cv6`) và `Follow lại` (`:id/ct3`)
- Không có modal dialog overlay hay nút đóng X dạng modal (`:id/e63` hoặc header X).

## Nguyên nhân gốc (Root Cause)
1. **Classifier gom cụm marker thành modal popup:**
   `detect_contact_follow_suggestion` (trong `automation-core` và `python_runner/flows/benign_popup.py`) phát hiện đồng thời:
   - `contact_marker`: "Bạn bè", "Người mà bạn có thể biết"
   - `follow_marker`: "Follow lại"
   - `dismiss_button_present`: "Không quan tâm"
   -> Phân loại thành `manual-needed:popup` (`contact_follow_suggestion`).

2. **Blind popup rule bắt nhầm node:**
   Rule `repost_sheet_close` trong `GemPhoneFarmBlindPopupRule` dùng XPath `//node[@text="Bài đăng lại" or @resource-id="com.ss.android.ugc.trill:id/title" and @text="Bài đăng lại"]`.
   Do thứ tự ưu tiên toán tử logic trong XPath, mệnh đề `@resource-id="...:id/title"` khớp với tên tác giả video ("Bích Ngọc Ngọc"), kích hoạt tìm nút đóng `e55` và báo action failure.

3. **Thiếu modal close X dẫn đến dừng phiên sai:**
   Do đây là video feed item (nằm trong ViewPager/Feed container), không có nút đóng modal X. Cơ chế dismiss popup không đóng được, khiến luồng đánh giá là popup kẹt và kích hoạt `manual-needed:popup` dừng phiên giữ hiện trường.

## Quy tắc xử lý chuẩn (Standard Rule)
1. **Phân biệt In-Feed Card với Modal Dialog:**
   - **In-Feed Card:** Nằm trực tiếp trên ViewPager feed (`com.ss.android.ugc.trill:id/viewpager`), các tab trên (`Đề xuất`, `Bạn bè`) và navigation bar dưới vẫn hiển thị đầy đủ, không có scrim / modal barrier.
   - Thẻ này là nội dung feed hợp lệ: **không dừng phiên**, cho phép vuốt tiếp (`swipe`) qua video sau hoặc thực hiện tương tác hành động ("Follow lại" / "Không quan tâm" nếu có policy).
2. **Khắc phục XPath Selector:**
   - Đóng ngoặc chuẩn xác khi kết hợp `or` và `and` trong XPath `repost_sheet_close`: `//node[(@text="Bài đăng lại" or @resource-id="com.ss.android.ugc.trill:id/title") and @text="Bài đăng lại"]` hoặc chỉ khớp strictly `@text="Bài đăng lại"`.
3. **Guard cho `detect_contact_follow_suggestion`:**
   - Khi `selected_feed_screen` xác định rõ feed hợp lệ (`for-you`, `friends`, `following`) và ViewPager đang hiển thị feed controls bình thường, thẻ in-feed recommendation không được biến cả màn hình thành `manual-needed:popup` chặn swipe.
