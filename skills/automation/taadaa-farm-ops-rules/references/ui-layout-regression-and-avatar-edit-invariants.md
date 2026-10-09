# TikTok Profile UI Variants & Anti-Regression Invariants (03/10/2026)

## 1. Sự cố Vòng lặp Hồi quy (Regression Loop) trong Selector UI
- **Hiện tượng**: Sửa selector cho máy A làm hỏng máy B. Ví dụ commit `2f1155f` (01/10/2026): khi sửa nhận diện cho máy có bút bên phải, agent tự coi `[24, 96][126, 204]` là "nút Back góc trên bên trái" và hardcode bypass `event=top_left_back_bypassed`. Đến 02/10/2026, Máy 18 rơi vào biến thể TikTok mới có cây bút nằm đúng ở `[24, 96][126, 204]` (tâm `(75, 150)` ngay trên tên hiển thị `huy0108`) khiến script bị mù hoàn toàn, loop lỗi `AVATAR_EDIT_OPEN_FAILED`.
- **Nguyên nhân cốt lõi**:
  1. Monolith `state_machine.py` chứa chuỗi `if/else` chắp vá thay vì Strategy Pattern / Registry.
  2. Agent sửa ad-hoc cục bộ cho 1 máy mà không kiểm thử hồi quy trên các layout khác.
  3. "Luật mềm" (nhắc đọc `docs/farm-automation-cases.md`) thất bại do LLM context amnesia.

## 2. Danh mục Biến thể Layout Profile TikTok (Golden Layout Corpus)
Mọi selector nhận diện Profile BẮT BUỘC phải hỗ trợ và kiểm thử trên cả 4 biến thể:
1. **Biến thể A (Classic)**: Có nút chữ to `[ Sửa hồ sơ ]`, `[ Chỉnh sửa hồ sơ ]` hoặc `[ Edit profile ]`.
2. **Biến thể B (Right Pencil)**: Nút icon cây bút nằm bên phải header: `[780..950, 480..650]`.
3. **Biến thể C (Top-Left Pencil & Right Avatar)**:
   - Avatar nằm bên phải `[756..999, 350..549]`, có bong bóng trạng thái ("Tám chuyện nào"), bị nút Story `+` (`[931, 499][1080, 636]`) đè ở góc dưới phải.
   - Nút mở màn "Sửa hồ sơ" là **icon cây bút góc trên bên trái**: `[24, 96][126, 204]` (tâm `(75, 150)`), nằm ngay phía trên tên tài khoản. CẤM coi đây là nút Back!
4. **Biến thể D (Share / More)**: Có icon 3 chấm hoặc nút Chia sẻ hồ sơ cạnh nút `+ Thêm tiểu sử`.

## 3. Quy tắc Nghiệm thu Đổi Avatar Bắt buộc (Canary & Verification)
- CẤM nghiệm thu qua Smoke test khi status trả về `SKIPPED_EXISTING_AVATAR` hoặc `PRESENT` của avatar cũ.
- Đổi avatar BẮT BUỘC:
  1. Chạy với cờ `--force-avatar-upload` và `--force-avatar-machines <N>`.
  2. Kiểm tra log `[ENSURE_AVATAR] Avatar upload thành công` và report `avatar_status: FORCED_REPLACED_VERIFIED`.
  3. Chụp ảnh màn hình Profile thực tế sau khi đổi và đối soát khớp với ảnh gốc trong thư mục nguồn (Folder Video).

## 4. Quy trình Cưỡng chế Kỹ thuật (Hard Enforcement Checklist)
1. **Trước khi sửa code UI selector**: BẮT BUỘC tra cứu `docs/farm-automation-cases.md` để nắm các case/anti-pattern liên quan.
2. **Khi sửa code**: Bổ sung Golden XML dump của biến thể mới vào `tests/fixtures/` hoặc test suite.
3. **Chạy Regression Test Matrix**: Chạy `pytest tests/test_avatar_edit_and_milestone.py` đảm bảo pass 100% tất cả các test case của TẤT CẢ các biến thể cũ lẫn mới.
4. **Sau khi sửa**: BẮT BUỘC ghi nhận Case mới (Case Fix, Anti-Pattern, Golden Bounds) vào `docs/farm-automation-cases.md`.
