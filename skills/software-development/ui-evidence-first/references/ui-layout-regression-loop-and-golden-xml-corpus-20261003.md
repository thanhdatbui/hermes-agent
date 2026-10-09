# UI Layout Regression Loop & Golden XML Corpus Invariant (03/10/2026)

## 1. Sự cố Thực tế: Vòng lặp Hồi quy "Sửa chỗ này Đập chỗ khác"
- **Bối cảnh**: TikTok liên tục A/B testing giao diện Profile (layout Classic nút chữ, layout Right-Pencil, layout Top-Left Pencil trên tên hiển thị `huy0108`, layout Story nút `+` đè góc avatar...).
- **Diễn biến sự cố 01/10 ➔ 03/10**:
  1. Ngày 01/10/2026, commit `2f1155f`: Khi sửa nhận diện nút cây bút cho một máy khác, agent tự quan sát thấy toạ độ `[24, 96][126, 204]` ở góc trên bên trái liền vội vàng kết luận đây là "nút Back góc trên bên trái" và hardcode bypass:
     `if left >= 24 and top >= 96 and right <= 126 and bottom <= 204: event=top_left_back_bypassed; break`
     Thậm chí còn sửa luôn unit test để ép `_find_profile_edit_button` trả về `None` cho bounds này.
  2. Ngày 02/10 – 03/10/2026: Máy 18 rơi vào biến thể TikTok mới (cây bút nằm đúng ở `[24, 96][126, 204]`, tâm `(75, 150)` ngay trên tên hiển thị `huy0108`). Do bị đoạn code bypass chặn lại, script bị mù hoàn toàn, rơi vào loop lỗi `AVATAR_EDIT_OPEN_FAILED`, không thể mở màn Sửa hồ sơ.
  3. User bức xúc: *"Vkl bắt đầu vòng lặp sửa chỗ này thành lỗi chỗ kia, trc đây t ép phải đọc trong file uiautomator case.md trc khi sửa tránh tình trạng đó, rồi sau đéo hiểu sao sửa cũng k đọc, sửa xong cx k ghi vào case, đéo tuân thủ tao nữa"*.

## 2. Nguyên nhân Thất bại của "Luật Mềm" (Soft Rules Failure)
- Ép agent bằng câu chữ trong prompt ("nhớ đọc file case trước khi sửa") luôn thất bại theo thời gian vì:
  + LLM context amnesia giữa các session / subagent mới.
  + Áp lực sửa nhanh lỗi hiện trường cục bộ dẫn đến các giả định ad-hoc (`if/else` chắp vá trong monolith >7000 dòng).
  + Không có test hồi quy tự động kiểm tra trên toàn bộ các biến thể layout cũ.

## 3. Giải pháp Cưỡng chế Hệ thống (Hard Enforcement Architecture)

### A. Golden XML Corpus & Matrix Regression Suite
1. **Lưu trữ Golden XML**: Mọi biến thể layout đã gặp trên farm phải được trích xuất XML dump thực tế và lưu vào `tests/fixtures/golden_layouts/`:
   - `profile_variant_a_classic.xml`: Nút chữ to "Sửa hồ sơ".
   - `profile_variant_b_right_pencil.xml`: Icon bút bên phải `[780..950, 480..650]`.
   - `profile_variant_c_top_left_pencil.xml`: Icon bút góc trên bên trái `[24, 96][126, 204]`.
   - `profile_variant_d_share_more.xml`: Nút chia sẻ cạnh bio.
2. **Pytest Regression Matrix Bắt buộc**:
   ```python
   @pytest.mark.parametrize("layout_fixture, expected_bounds", [
       ("profile_variant_a_classic.xml", (540, 800)),
       ("profile_variant_b_right_pencil.xml", (854, 558)),
       ("profile_variant_c_top_left_pencil.xml", (75, 150)),
   ])
   def test_all_profile_variants_return_valid_edit_button(layout_fixture, expected_bounds):
       btn = StateMachine._find_profile_edit_button(adapter, load_xml(layout_fixture))
       assert btn is not None
       assert btn["center"] == expected_bounds
   ```
   **Bất kỳ commit nào làm fail 1 layout cũ sẽ bị pytest chặn đứng vật lý ngay lập tức.**

### B. Pre-commit / Closeout Gate Hook
- Tích hợp vào `closeout_gate.py`:
  + Kiểm tra diff: Nếu có thay đổi trong vùng UI selector (`_find_profile_edit_button`, `_is_avatar_crop_screen`, `_profile_avatar_bounds`...) mà `git diff --name-only` KHÔNG CÓ file docs case (`docs/farm-automation-cases.md`) hoặc không có test mới trong `tests/` ➔ **REJECTED ngay lập tức, CẤM CHỐT PHIÊN.**

### C. Quy tắc Đổi Avatar Thật (Canary Invariant)
- **CẤM** lấy kết quả exit 0 của `--avatar-smoke` (`SKIPPED_EXISTING_AVATAR`) để báo hoàn thành khi user yêu cầu đổi avatar.
- Bắt buộc chạy `--force-avatar-upload`, kiểm tra `avatar_status: FORCED_REPLACED_VERIFIED`, và chụp ảnh Profile thực tế đối soát với ảnh trong thư mục nguồn (Folder Video).
