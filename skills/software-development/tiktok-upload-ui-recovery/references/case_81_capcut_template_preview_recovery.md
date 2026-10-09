# Case 81: CapCut Template Preview / Template Hub Dismissal & Recovery

## Triệu chứng
- Workflow văng lỗi `upload_subprocess_nonzero` hoặc dừng phiên ở bước `VIDEO_PICK` / `OPEN_TIKTOK`.
- Máy 61 (hoặc máy bất kỳ trong farm) bị kẹt ở màn hình xem trước Mẫu / Template CapCut (giao diện hiển thị nút màu đỏ "Thử mẫu này" / "Use template", tên bài hát/beat, lyric, icon back `<` góc trên bên trái) thay vì hiển thị camera / album picker.

## Nguyên nhân gốc (Root Cause)
- Khi bấm nút Create/Plus trên thanh điều hướng hoặc sau khi mở app, nếu tài khoản vừa xem video dạng Mẫu CapCut hoặc TikTok push template recommendation, giao diện chuyển hướng vào `TemplatePreviewActivity` / `CapCutHubSurface`.
- Selector tìm kiếm nút "Tải lên" / "Album" không tồn tại trên màn hình này, dẫn đến timeout và subprocess crash non-zero.

## Giải pháp & Codebase Recovery
1. **Nhận diện màn hình mẫu:**
   - Detect các chuỗi UI đặc trưng: "Thử mẫu này", "Use template", "Mẫu CapCut", "CapCut · Dùng mẫu".
   - Detect nút quay lại (`back_btn`, `iv_back`, `btn_close`, icon `<` góc trái trên: bounds x <= 150, y <= 200).
2. **Auto-dismiss:**
   - Tự động tap nút Back / Close trên UI của màn hình template preview.
   - Nếu UI không phản hồi, gửi fallback keyevent BACK (`device.keyevent('BACK')` / `input keyevent 4`) 1-2 lần để thoát về Feed / Profile an toàn.
3. **Re-enter Upload Flow:**
   - Re-verify lại root UI (`Trang chủ` / `Hồ sơ`), sau đó thực hiện lại bước tap nút Create (+) để vào đúng Album / Video Picker chuẩn.
