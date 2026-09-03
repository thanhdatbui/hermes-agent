# TikTok Location Permission Dialog Dismissal Pattern (2026-08-20)

## Context & Phenomenon
Khi TikTok hiển thị modal dialog yêu cầu cấp quyền vị trí:
- **Tiêu đề (VN)**: `Xem nội dung phù hợp và địa điểm lân cận`
- **Tiêu đề (EN)**: `See relevant content and nearby places`
- **Nội dung body**: `Mở cài đặt thiết bị của bạn và truy cập Vị trí > Trong khi sử dụng ứng dụng. Bạn có thể tắt bất cứ lúc nào.` (`android:id/message`)
- **Nút từ chối**: `Hủy` / `Cancel` (`android:id/button3`)
- **Nút mở cài đặt**: `Mở cài đặt` / `Open settings` (`android:id/button1`)

## Pitfalls & Core Rules
1. **Modal Scope Isolation (Tránh false-positive cross-dialog)**:
   - Dialog này dùng các resource-id chuẩn của Android framework (`android:id/button1`, `android:id/button3`, `android:id/message`).
   - Tuyệt đối KHÔNG quét toàn bộ tree hierarchy phẳng hoặc lấy first-match riêng rẽ cho từng nút/text, vì sẽ dễ ghép nhầm nút `Hủy` của một popup/draft khác đang chạy ngầm hoặc dialog sibling.
   - Phải duyệt theo từng candidate container subtree chứa đồng thời cả 4 thành phần (Title, Body message, Button 1, Button 3) và xác thực Button 1 & Button 3 là sibling trực tiếp trong action bar.

2. **Priority Ordering**:
   - Location dialog là blocking modal foreground.
   - Khi xuất hiện, nó phải được xử lý bấm `Hủy` (`android:id/button3`) trước khi các detector CTA ở background (như Shop CTA / Add Phone) nhận nhầm click.

3. **Multi-language Support**:
   - Hỗ trợ đầy đủ cả cặp từ khoá Tiếng Việt (`Xem nội dung phù hợp và địa điểm lân cận`, `Hủy`, `Mở cài đặt`) và Tiếng Anh (`See relevant content and nearby places`, `Cancel`, `Open settings`).
