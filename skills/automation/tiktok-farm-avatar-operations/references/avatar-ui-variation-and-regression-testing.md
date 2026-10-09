# Regression Gating & Multi-Layout UI Compatibility in TikTok Avatar Operations

## 1. Context & Problem
TikTok thường xuyên A/B test và cập nhật layout trên các tài khoản/phiên bản khác nhau trong farm:
- Một số tài khoản hiển thị nút text truyền thống: "Sửa hồ sơ" / "Chỉnh sửa hồ sơ" / "Edit profile".
- Một số tài khoản hiển thị icon cây bút chì ở góc trên bên trái header (như Machine 11 Tik 1 `@hatien15118`).
- Một số tài khoản hiển thị icon cây bút chì ở bên phải hoặc nằm cạnh nút "Chia sẻ hồ sơ".
- Giao diện Photo Picker có thể là DocumentsUI của Android hoặc Media Picker tùy biến của TikTok/Samsung.

Khi điều chỉnh logic workflow cho một máy cụ thể, Operator thường có tâm lý lo ngại: *"Có regression gate đầy đủ chứ, sợ giao diện tiktok khác nhau thôi"*. Do đó, việc duy trì bộ regression test gate và kiến trúc layout registry là bắt buộc.

---

## 2. Multi-Layout Registry Architecture (`profile_layouts`)
Để không bao giờ bị vỡ layout khi TikTok đổi giao diện, logic tìm nút sửa hồ sơ được phân rã thành các class độc lập trong thư mục `scripts/tiktok_workflow/profile_layouts/`:
1. `ClassicTextLayout`:
   - Nhận diện các nhãn text: `"sửa hồ sơ"`, `"chỉnh sửa hồ sơ"`, `"edit profile"`.
2. `TopLeftPencilLayout`:
   - Nhận diện icon cây bút chì ở góc trên bên trái header (bên trên username):
   - Toạ độ/Bounds tiêu chuẩn: `[left: 10..45, top: 70..130, right: 110..145, bottom: 190..230]` (ví dụ bounds thật trên M11: `[43, 117][108, 182]`, center `(76, 150)`).
   - Tự động loại trừ các icon điều hướng khác như Back, Menu, Thêm bạn bè.
3. `RightPencilLayout`:
   - Nhận diện nút bút chì hoặc nút edit ở khu vực header bên phải (`left >= 650`, `top 450..620`).
4. `ShareProfileLayout`:
   - Nhận diện vùng nút chia sẻ / edit nằm cạnh phần bio.

**Nguyên tắc Fail-Closed:** Nếu không match bất kỳ layout nào trong registry, workflow ném `AVATAR_EDIT_BUTTON_NOT_FOUND` và dump XML ra thư mục quarantine để mở rộng layout có chủ đích, tuyệt đối không click mò tọa độ ngẫu nhiên.

---

## 3. Regression Test Gates (Offline Verification)
Trước và sau bất kỳ thay đổi nào liên quan đến avatar workflow, BẮT BUỘC chạy kiểm chứng bằng 2 lệnh focused pytest offline:

1. **Bộ test Layout & Milestone Popups:**
   ```bash
   D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe -m pytest D:/Taadaa/Tiktok-video/tests/test_avatar_edit_and_milestone.py -v
   ```
   - Xác nhận 34/34 tests PASS.
   - Bao gồm: Đóng popup chúc mừng lượt thích/milestone ("OK", "Xong"), phát hiện màn hình Sửa hồ sơ, và phân giải các biến thể cây bút chì.

2. **Bộ test Photo Picker & Album Selection:**
   ```bash
   D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe -m pytest D:/Taadaa/Tiktok-video/tests/test_tiktok_workflow.py -k avatar_picker -v
   ```
   - Xác nhận toàn bộ test picker PASS.
   - Kiểm tra hành vi chọn thẳng candidate ảnh đầu tiên mới push, không mở dropdown menu gây bấm nhầm nút Camera.

---

## 4. Pitfall An Toàn Cho Mock / FakeAdapter Trong Unit Tests
- Trong unit tests (`tests/test_tiktok_workflow.py`), test runner thường khởi tạo các đối tượng giả lập như `FakeAdapter` hoặc `DummyAdapter`.
- Các class này chỉ implement một tập hợp tối thiểu các phương thức public (`dump_ui`, `tap`, `back`, `_tap_if_found`), thường **không** có các helper nội bộ như `_find_ui_element`.
- **Quy tắc code phòng thủ:** Bất kỳ đoạn code nào truy cập helper nội bộ của adapter (ví dụ kiểm tra node `o_9`):
  ```python
  # SAI - Gây AttributeError trên FakeAdapter trong unit test
  already_at_picker = bool(adapter._find_ui_element(current_xml, resource_id="o_9"))

  # ĐÚNG - Hoàn toàn tương thích cả adapter thật lẫn adapter mock trong test suite
  already_at_picker = bool(
      hasattr(adapter, "_find_ui_element")
      and adapter._find_ui_element(current_xml, resource_id="o_9")
  )
  ```
- Việc tuân thủ quy tắc phòng thủ này đảm bảo pipeline test hồi quy (CI / offline pytest) luôn chạy ổn định 100% mà không bị false alarm.
