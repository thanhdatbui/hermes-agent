# Pitfalls & Patterns: Popup Dismiss, Safe XML Capture & BACK Key Trapping

## 1. Safe Hierarchy Capture trong Popup Dismissers (`_safe_capture_hierarchy`)
- **Triệu chứng:** Displayer / dismisser báo `dismissed=True` nhưng popup không đóng trên máy thực tế, do không tìm thấy node nút bấm.
- **Nguyên nhân:** Runtime `DeviceContext` (từ `python_runner`) và `AdbClient` (từ `automation_core`) không có method `ctx.dump_hierarchy()` hay `ctx.adb.dump_hierarchy()`. Nếu helper chỉ kiểm tra 2 thuộc tính này, chuỗi XML trả về luôn rỗng `""`.
- **Giải pháp chuẩn:**
  ```python
  def _safe_capture_hierarchy(ctx: Any) -> str:
      if hasattr(ctx, "dump_hierarchy") and callable(ctx.dump_hierarchy):
          try:
              res = ctx.dump_hierarchy()
              if res:
                  return res
          except Exception:
              pass
      if hasattr(ctx, "adb") and hasattr(ctx.adb, "dump_hierarchy") and callable(ctx.adb.dump_hierarchy):
          try:
              res = ctx.adb.dump_hierarchy()
              if res:
                  return res
          except Exception:
              pass
      if hasattr(ctx, "dump_xml") and callable(ctx.dump_xml):
          try:
              res = ctx.dump_xml()
              if res:
                  return res
          except Exception:
              pass
      try:
          from automation_core.ui import dump_current_ui
          adb = getattr(ctx, "adb", ctx)
          xml = dump_current_ui(adb)
          if xml:
              return xml
      except Exception:
          pass
      try:
          from automation_core.ui import dump_shell_ui
          adb = getattr(ctx, "adb", ctx)
          xml = dump_shell_ui(adb)
          if xml:
              return xml
      except Exception:
          pass
      return ""
  ```

## 2. Modal Dialogs chặn `KEYCODE_BACK`
- **Ví dụ điển hình:** Modal xin quyền danh bạ / Facebook ("Để kết nối với những người bạn biết trên TikTok, hãy cho phép truy cập vào danh bạ của bạn trong mục cài đặt thiết bị.").
- **Hành vi Android/TikTok:** Dialog dạng modal chặn toàn bộ `KEYCODE_BACK` (gửi phím back trả về exit code 0 nhưng popup không biến mất).
- **Yêu cầu xử lý:**
  1. Luôn ưu tiên tap trực tiếp vào node text mang ý nghĩa từ chối: `target_labels = {"không cho phép", "kh\u00f4ng cho ph\u00e9p", "don't allow", "dont allow", "deny", "từ chối", "tu choi", "hủy", "huy", "cancel", "để sau", "not now"}`.
  2. Bổ sung fallback tap theo tọa độ tỷ lệ màn hình `(w, h)` trước khi thử phím BACK:
     - Nút `"Không cho phép"` (góc dưới bên trái modal): `(int(w * 0.305), int(h * 0.639))`.
  3. Tuyệt đối không chỉ gửi `send_device_back_key(ctx)` rồi return `dismissed=True` nếu chưa xác nhận popup thực sự đóng.
