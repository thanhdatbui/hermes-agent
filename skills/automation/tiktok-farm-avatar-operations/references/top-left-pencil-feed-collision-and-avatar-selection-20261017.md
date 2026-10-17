# Top-Left Pencil Feed/Header Collision & Avatar Face Clarity (2026-10-17)

## 1. Hiện Tượng Lỗi: `AVATAR_UPLOAD_MENU_MISSING` Do Bắt Nhầm Layout
- **Triệu chứng**:
  Khi chạy `run_tiktok_upload_avatar.ps1`, runner văng lỗi:
  `[ERROR] [AVATAR_UPLOAD_MENU_MISSING] ENSURE_AVATAR: Không tìm thấy Tải ảnh lên`
  và kết thúc với `exit=1, verified=False`.
- **Nguyên nhân gốc rễ**:
  1. Trong `scripts/tiktok_workflow/profile_layouts/top_left_pencil.py`, `TopLeftPencilLayout` có điều kiện bounds bị nới lỏng quá mức (`0 <= n.l <= 45`, `w, h <= 170`).
  2. Đồng thời, `matches()` thiếu điều kiện loại trừ màn hình Feed video (`tree.has_text("đề xuất", "for you")`).
  3. Khi ở Feed hoặc trên header profile của các thiết bị Samsung, icon ở góc trên cùng bên trái `[24,96][126,204]` (tâm `75, 150`, là icon Thêm bạn / Live camera không có description) bị nhận diện nhầm là "bút chì sửa hồ sơ".
  4. Lệnh `adapter.tap(75, 150)` tap vào nút Thêm bạn thay vì mở màn hình Sửa hồ sơ. Khi vào sai màn hình, state machine không tìm thấy "Tải ảnh lên" và crash.

## 2. Giải Pháp Khắc Phục Chuẩn Hóa
- **Thắt chặt bounds & loại trừ Feed trong `top_left_pencil.py`**:
  ```python
  def matches(self, tree: UiTree) -> bool:
      if tree.has_text("sửa hồ sơ", "chỉnh sửa hồ sơ", "edit profile"):
          return False
      if tree.has_rid("long_press_layout") or tree.has_text("đề xuất", "for you"):
          logger.debug("[PROFILE_LAYOUT] [METRIC] event=top_left_pencil_excluded reason=feed_surface")
          return False
      cands = self._find_pencil_candidates(tree)
      return len(cands) > 0

  def _find_pencil_candidates(self, tree: UiTree) -> list[Node]:
      def is_top_left_pencil(n: Node) -> bool:
          if n.cls not in {"android.widget.ImageView", "android.widget.ImageButton", "android.view.View", ""}:
              return False
          combined_desc = (n.desc + " " + n.text).casefold()
          for k in ("thêm người", "thêm bạn", "bạn bè", "find friends", "add friends", "quay lại", "back", "thông báo", "menu", "chia sẻ"):
              if k in combined_desc:
                  return False
          # Thắt chặt bounds: l từ 10..45, w và h <= 130
          if 10 <= n.l <= 45 and 70 <= n.t <= 130:
              if 50 <= n.w <= 130 and 50 <= n.h <= 130:
                  return True
          return False
      return tree.find(is_top_left_pencil)
  ```
- **Kiểm thử hồi quy**:
  Chạy focused test `python -m pytest tests/test_avatar_edit_and_milestone.py -q` bảo đảm 100% test cases pass.

---

## 3. Kỷ Luật Trích Xuất Avatar: Tránh Kính Râm / Che Mặt & Cung Cấp Đa Dạng
- **Bài học từ phản hồi User ("Đổi ảnh khác")**:
  - Dù avatar phong cách hip-hop có trang phục cá tính nhưng việc **đeo kính râm đen che kín mắt** làm mất đi thần thái khuôn mặt, khiến người xem/chủ kênh cảm thấy xa lạ hoặc khó nhận diện.
  - Khi trích xuất avatar người thật cho kênh cá nhân:
    * **Ưu tiên số 1**: Khuôn mặt lộ rõ ngũ quan, mắt nhìn thẳng, nụ cười tươi tắn tự nhiên, không bị phụ kiện (kính râm to, khẩu trang, nón che sụp) che khuất mắt.
    * **Đa dạng hoá 3 góc**: (1) Cận cảnh chính diện tươi cười thân thiện; (2) Góc hoạt động chuyên môn / nghệ thuật (chơi đàn, vẽ tranh, làm việc); (3) Góc biểu diễn / sân khấu.
    * **Headroom chuẩn**: Đỉnh tóc cách mép trên 15–25px, cằm không chạm đáy viền tròn xanh $512 \times 512$.

---

## 4. Kỷ Luật Pin Top Video Trong Chuẩn Hóa 3 Món
- Trong `tools/pin_top_videos.py`, sau khi tap nút "Ghim" trên action sheet, TikTok thường tự động đóng action sheet và cập nhật cờ "Đã ghim".
- Nếu tự động gửi `KEYCODE_BACK` mù quáng sau khi tap mà không kiểm tra lại UI, lệnh BACK sẽ làm thoát khỏi màn hình Profile về Home/Feed, dẫn đến việc verify tile ghim thất bại (`PIN_NOT_VERIFIED`).
- **Quy tắc**: Chỉ gửi `KEYCODE_BACK` khi `parse_action_sheet(dump_profile_ui_atx(serial))` xác nhận action sheet vẫn còn hiển thị.
