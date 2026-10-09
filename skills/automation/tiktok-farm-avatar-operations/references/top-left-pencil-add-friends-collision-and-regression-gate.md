# Top-Left Pencil vs Add Friends Collision & Regression Gate Discipline (07/10/2026)

## 1. Hiện Tượng & Nguyên Nhân Va Chạm Layout (Collision)
- **Hiện tượng:** Máy vào Profile root thành công nhưng kẹt ở bước `ENSURE_AVATAR`, log báo:
  `[PROFILE_LAYOUT] Overlapping layouts matched: ['top_left_pencil', 'right_pencil']; choosing top_left_pencil`
  Sau đó tap vào tọa độ `(78, 150)` và không mở được trang Sửa hồ sơ, văng lỗi `AVATAR_EDIT_OPEN_FAILED`.
- **Nguyên nhân cốt lõi:**
  1. Icon ở góc trên bên trái header `[24,96][132,204]` thực chất là icon **"Thêm bạn bè"** (Add Friends) của TikTok, không phải cây bút chì.
  2. Hàm loại trừ trong `TopLeftPencilLayout._find_pencil_candidates` chỉ lọc `"thêm người"`, `"find friends"` mà thiếu từ khóa tiếng Việt thực tế: `"thêm bạn"`, `"bạn bè"`, `"add friends"`.
  3. Thứ tự ưu tiên trong `REGISTRY`: `TopLeftPencilLayout` xếp trước `RightPencilLayout`, dẫn đến khi overlap sẽ chọn nhầm icon kết bạn thay vì icon bút chì thật bên phải tên người dùng.
  4. `ShareProfileLayout` vô tình nằm trong `REGISTRY` làm gãy fail-closed gate của unit test.

---

## 2. Bản Vá Chuẩn Hóa Kiến Trúc Layout Registry
- **Quy tắc thứ tự trong `profile_layouts/__init__.py`:**
  ```python
  REGISTRY: tuple[ProfileLayout, ...] = (
      ClassicTextLayout(),
      RightPencilLayout(),     # Ưu tiên bút chì bên phải trước
      TopLeftPencilLayout(),   # Chỉ fallback sang top-left khi không có right pencil
  )
  ```
  *(Loại bỏ `ShareProfileLayout` khỏi REGISTRY mặc định của Edit Profile)*.
- **Quy tắc mở rộng blacklist trong `top_left_pencil.py`:**
  ```python
  combined_desc = (n.desc + " " + n.text).casefold()
  if any(k in combined_desc for k in (
      "thêm người", "thêm bạn", "bạn bè",
      "find friends", "add friends",
      "quay lại", "back", "thông báo", "menu", "chia sẻ"
  )):
      return False
  ```

---

## 3. Kỷ Luật Bắt Buộc: Chạy Regression Gate Trước Khi Chạm Máy Thật
- Khi Operator hỏi *"Có chạy regression gate không"*, đây là câu hỏi chất vấn kỷ luật an toàn cực kỳ nghiêm ngặt.
- **BẮT BUỘC:** Chạy offline pytest kiểm chứng trước và sau mọi thay đổi layout:
  ```bash
  python -c "
  import subprocess, os
  env = os.environ.copy()
  env.pop('PYTHONPATH', None)
  cmd = [r'D:\CodexRuntime\tiktok-video\venv-core024\Scripts\pytest.exe', r'D:\Taadaa\Tiktok-video\tests\test_avatar_edit_and_milestone.py']
  res = subprocess.run(cmd, env=env)
  assert res.returncode == 0
  "
  ```
  Yêu cầu bắt buộc: **34/34 tests PASSED (0 failed)**.
- Chỉ khi regression gate đạt 100% xanh mới được phép kích hoạt runner trên thiết bị thật.
