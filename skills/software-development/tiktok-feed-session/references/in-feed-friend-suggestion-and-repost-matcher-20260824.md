# In-Feed Friend Suggestion Card & Repost Sheet Matcher Fix (2026-08-24)

## Hiện tượng & Nguyên nhân
- **Hiện tượng**: Màn hình video feed TikTok hiển thị thẻ gợi ý bạn bè in-feed (có tag "Bạn bè với...", nút "Không quan tâm" và nút "Follow lại" `id/ct3`). Runner dừng phiên với lỗi `unexpected popup/dialog marker detected` và giữ hiện trường.
- **Nguyên nhân kép**:
  1. `repost_sheet_close` trong `GEMPHONEFARM_BLIND_POPUP_RULES` chứa xpath `... or @resource-id="com.ss.android.ugc.trill:id/title"`. Tên tác giả video trên Feed cũng dùng resource-id `:id/title`, khiến rule nhận diện nhầm video là bảng Repost Sheet, sau đó cố tìm nút đóng `:id/e55` không tồn tại $\rightarrow$ `action not found` $\rightarrow$ fail.
  2. `follow_back_suggestion` trước đây dùng `contains(@text, "Người mà bạn có thể biết")`. Engine `find_by_gem_xpath` (`_XPATH_CONDITION_RE`) chỉ bóc tách các cặp `@attr="value"` khớp chính xác, hoàn toàn bỏ qua hàm `contains()`. Do đó rule không match được thẻ "Bạn bè với...".
  3. Sau khi các blind rules thất bại, classifier phát hiện các marker "Follow lại", "Không quan tâm" chưa được xử lý và phân loại thành `manual-needed:popup` $\rightarrow$ dừng phiên oan.

## Cách xử lý chuẩn
1. **Chuẩn hóa `repost_sheet_close`**:
   - Match chính xác tiêu đề bảng đăng lại đa ngôn ngữ: `//node[@text="Bài đăng lại" or @text="Repost" or @text="Reposts" or @content-desc="Bài đăng lại" or @content-desc="Repost" or @content-desc="Reposts"]`.
   - Tuyệt đối không dùng bare resource-id `:id/title` nếu không đi kèm text (để tránh bắt nhầm author title trên feed video).
   - Nút đóng: `//node[@content-desc="Đóng" or @content-desc="Close" or @resource-id="com.ss.android.ugc.trill:id/e55"]`.
   - Đặt `loop=False` để chỉ tap đóng 1 lần, tránh tiếp tục quét và tap nhầm vào nút Close của UI bên dưới.

2. **Chuẩn hóa `follow_back_suggestion`**:
   - Match chính xác theo text / content-desc hành vi: `//node[@text="Follow lại" or @content-desc="Follow lại" or @text="Follow back" or @content-desc="Follow back" or @text="Theo dõi lại" or @content-desc="Theo dõi lại"]`.
   - **CẤM match bare resource-id `:id/ct3` đứng một mình** mà không có text/desc rõ ràng (tránh false-positive tap nhầm các button khác tái sử dụng ID `ct3` khi chưa render text).
   - Action: `tap`, `loop=False` (bấm 1 lần nút Follow lại để theo dõi và tiếp tục chu kỳ feed bình thường).

3. **Quy tắc XPath trong `GEMPHONEFARM_BLIND_POPUP_RULES`**:
   - Tuyệt đối không dùng `contains()` trong xpath cho `find_by_gem_xpath` vì parser regex chỉ đọc `@attr="value"`.
   - Luôn sử dụng exact attribute matching (`@text="exact_text"`, `@resource-id="exact_id"`).
