# TikTok Account Switcher: Core Flow vs Consumer Delegation

## Context & Bài học thực tế (04/10/2026)
Trong phiên đổi avatar trên farm (TikTok v47), Agent đã mắc các sai lầm:
1. **Phát biểu sai kiến thức cơ bản**: Nhầm lẫn chuyển nick là "bấm vào avatar" thay vì tap vào Tên/Username trên header Profile.
2. **Tự ý chế cháo đè code**: Khi gặp lỗi `SWITCHER_NOT_CONFIRMED`, Agent tự can thiệp vào hook adapter cấp consumer (`scripts/tiktok_workflow/adapter.py`), tự chế swipe sticky và lọc toạ độ mò mẫm, trong khi **toàn bộ cơ chế mở Account Switcher đã được chuẩn hoá tập trung 100% trong `automation-core` (`automation_core.tiktok.account_switcher`)**.
3. **Phá vỡ tính đồng bộ**: Làm bẩn working tree của consumer repo, phá vỡ nguyên tắc canonical platform, bị User chỉnh trực tiếp.

## Nguyên tắc bất biến
1. **Account Switcher thuộc quyền sở hữu của `automation-core`**:
   - Mọi logic nhận diện anchor, sticky header, fuzzy match username, tìm node `@`, và tap xổ sheet Account Switcher nằm trong `automation_core/tiktok/account_switcher.py`.
   - Consumer repos (`Tiktok-video`, `Tiktok_Reg`, `tiktok-follow`, `tiktok-add-bao-mat-f2a`) BẮT BUỘC dùng trực tiếp `open_switcher` hoặc `open_account_switcher` của core.
   - **CẤM TUYỆT ĐỐI** consumer repo tự viết hook đè, tự hardcode swipe sticky, hoặc tự đoán toạ độ mở switcher ở tầng consumer nếu không có chỉ thị kiến trúc từ User.

2. **Quy trình chuẩn mở Account Switcher trên TikTok Profile**:
   - Khi ở trang Profile: Chuyển nick là thao tác mở bottom sheet từ Tên hiển thị / Username trên header.
   - Tuyệt đối KHÔNG PHẢI bấm vào ảnh đại diện (avatar). Tap avatar chỉ để xem ảnh hoặc đổi avatar.
   - Khi UI v47 đổi kiểu hiển thị: `automation-core` tự quản lý selector header; nếu phát sinh layout mới cần mở rộng core và có test suite của core bảo vệ, không patch chắp vá trong adapter consumer.

3. **Kỷ luật xử lý khi Switcher thất bại trên máy live**:
   - Không vội sửa code: Kiểm tra xem máy có bị văng về Feed, kẹt popup hay chưa login (`inspect_machine.py`).
   - Nếu layout thay đổi thực sự: Báo cáo bằng chứng ảnh (`account-switcher-profile.png`), hỏi ý kiến hoặc xin chỉ thị cập nhật core, tuyệt đối không hack workaround ở consumer.
