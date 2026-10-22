# Rename Profile Geometry, Portable Flags & Bio Edit Safety Invariants (2026-10-22)

## 1. Samsung S7 (1080x1920) Profile Button Geometry
- **Layout Stacking Order (top to bottom):**
  1. Header / story prompt: `y ≈ 100 - 250`
  2. Avatar circle: `y ≈ 250 - 520`
  3. Nickname (Tên hiển thị): `y ≈ 539 - 587`
  4. Username (`@username`): `y ≈ 606 - 644`
  5. Follower stats (`Đã follow | Follower | Thích`): `y ≈ 689 - 774`
  6. Button row:
     - Account đã có bio (2 nút ngang): `Sửa hồ sơ` bên trái (`x ≈ 100 - 530`, tâm `(315, 865)`), `Chia sẻ hồ sơ` bên phải (`x ≈ 550 - 980`, tâm `(765, 865)`).
     - Account chưa có bio (1 nút chip ở giữa): `+ Thêm tiểu sử` (`x ≈ 350 - 730`, tâm `(540, 865)`).
  7. Video tab bar (Grid, Private, Liked): `y ≈ 950 - 1050`
- **Tapping Pitfall & The 540 Gap Trap:**
  - **BẪY KHE GIỮA x=540:** Trên nick đã có bio, tọa độ `x = 540` rơi đúng vào khe hở 25-pixel giữa nút `Sửa hồ sơ` và `Chia sẻ hồ sơ`. Khi OCR mờ không bắt được text nút và fallback về `(540, 865)`, máy sẽ tap vào khoảng trống không có phản hồi UI, dẫn đến `ABORT: ket o trang thai PROFILE 5 lan lien tiep`.
  - Tọa độ fallback cho `Sửa hồ sơ` **BẮT BUỘC là `(315, 865)`**, tuyệt đối không được dùng `(540, 865)` làm default chung. Tọa độ `540` chỉ được dùng khi đã xác nhận `btn_add_bio` khớp `+ Thêm tiểu sử`.
  - Tapping `y ≈ 660` lands in the blank space between username and followers -> no UI response.
  - Tapping `(72, 148)` (top left toolbar) hits the "Find Friends" icon on center-avatar layouts -> opens `FindFriendsPageActivity` loop.

## 2. BIO_EDIT Scope Safety Invariant
- **Strict Adherence to `BIO_REQUESTED`:**
  - When running a Rename-only job (`BIO_REQUESTED == False`), the runner MUST NOT write or overwrite a bio with dummy text (e.g. "Xin chao") just to force the "Sửa hồ sơ" button to appear.
  - Doing so creates unrequested profile mutation side-effects and false-success reports.
  - If `BIO_EDIT` is entered while `BIO_REQUESTED == False`, the runner must immediately escape back to Profile via `keyevent(4, 2)` without injecting text or tapping save.

## 3. Profile Username OCR Validation vs Internal Whitespace Noise
- TikTok usernames contain strictly alphanumeric characters, underscores, and dots with NO SPACES.
- **BẪY KHOẢNG TRẮNG OCR:** WinRT OCR (gói tiếng Anh) thường chèn khoảng trắng ngẫu nhiên vào giữa các ký tự username (ví dụ: `@ngotran g7771`). Nếu runner kiểm tra cứng `" " not in text`, dòng username thật sẽ bị loại bỏ hoàn toàn, dẫn đến `name, user = (None, None)` và quăng lỗi `da Luu nhung Ho so dang la @None, khong phai @ngotrang7771` dù thực tế thiết bị đã đổi tên thành công (False Positive FAIL).
- **Quy tắc đối soát chuẩn:**
  - Cho phép chuỗi có khoảng trắng nếu và chỉ nếu sau khi rút gọn qua `compact(text)` (bỏ khoảng trắng và ký tự đặc biệt) vẫn khớp chính xác `is_target_user(compact(text))`.
  - Giữ nguyên việc chặn khoảng trắng đối với các chuỗi khác để tránh bắt nhầm mention/bio suggestion.
  - Luôn ghi log telemetry `[OCR-SPACE]` khi phát hiện khoảng trắng để phục vụ truy vết.
  ```python
  text = t.strip()
  normalized = norm(text)
  is_user_line = (
      text.startswith("@")
      and b[1] < 750
      and not any(k in normalized for k in ("tai khoan", "nhac den", "noi ve", "chia se", "follower", "thich"))
      and (" " not in text or is_target_user(compact(text)))
  )
  if is_user_line and " " in text:
      print(f"   [OCR-SPACE] username OCR co khoang trang: raw={text!r} -> compact={compact(text)!r}")
  ```

## 4. Platform-Portable Subprocess Creationflags
- On Windows, `subprocess.CREATE_NO_WINDOW` (value `0x08000000`) prevents disruptive console window flash during automated tasks.
- However, hardcoding `creationflags=subprocess.CREATE_NO_WINDOW` crashes on non-Windows platforms with `AttributeError`.
- Portable pattern:
  ```python
  creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
  subprocess.run(cmd, creationflags=creationflags, ...)
  ```
