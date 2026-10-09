# Phục hồi lỗi POST_NEXT_SELECTOR_EXHAUSTED & Bề mặt Xem trước (Preview/Editor) có nút Đăng `sp3`

## 1. Triệu chứng & Bối cảnh
- **Lỗi:** `[FAILED] [POST_NEXT_SELECTOR_EXHAUSTED] POST: final composer/editor Next surface was not confirmed`.
- **Hiện trường:** Thiết bị dừng ở màn hình Preview/Editor của TikTok:
  - Header: Tiêu đề `"Xem trước"` (resource-id `com.ss.android.ugc.trill:id/rzu`).
  - Footer: Nút bấm màu đỏ hồng hình viên thuốc ở góc dưới bên phải có icon tải lên và nhãn `"Đăng"` (resource-id `com.ss.android.ugc.trill:id/sp3`, class `android.widget.Button`, bounds `[564,1770][1032,1902]`).
  - Caption và hashtag đã được điền đầy đủ.

## 2. Nguyên nhân cốt lõi (Anti-Pattern)
1. **Bề mặt Preview không có nút "Tiếp" (Next):** TikTok một số build UI chuyển thẳng video sau khi pick vào màn hình Preview/Editor mà trên màn hình này KHÔNG CÓ nút "Tiếp" / "Next", chỉ có nút "Đăng". State machine khi cố tìm nút "Tiếp" để mở full composer bị trôi qua mọi selector và raise ngoại lệ fail-closed `POST_NEXT_SELECTOR_EXHAUSTED`.
2. **Thiếu resource-id `sp3`:** Danh sách selector của nút Đăng trong `state_machine.py` chỉ chứa `("sh8", "shd", "sox", "soz", "sp7", "rbp", "t66")` và các ID cũ — thiếu mã hash ID `sp3` của build TikTok mới.
3. **Stale Post Intent Receipt Block:** Tại `_record_post_intent()`, phương thức `path.open("x")` raise `FileExistsError` nếu file receipt `machine_X_account_Y_video_Z.json` từ một lần chạy trước đó (ví dụ từ nhiều ngày trước) vẫn còn lưu trên đĩa, khiến phiên mới từ chối bấm Đăng vô cớ.

## 3. Giải pháp chuẩn trong Codebase (`state_machine.py`)
1. **Thêm `sp3` vào danh sách Resource ID của nút Đăng:**
   - Trong `_handle_post()` tại các tuple selector: bổ sung `"sp3"` vào `("sh8", "shd", "sox", "soz", "sp7", "sp3", "rbp", "t66", ...)`.
   - Bổ sung kiểm tra cả `text="Đăng"`, `content-desc="Đăng"`, `text="Post"`, `content-desc="Post"`.
2. **Chuyển đổi Fail-Closed sang Fail-Forward tại `if not next_tapped:`:**
   - Trước khi raise `POST_NEXT_SELECTOR_EXHAUSTED`, kiểm tra xem màn hình hiện tại có chứa các marker của bề mặt Preview/Editor không:
     ```python
     if any(marker in xml_text for marker in ("Xem trước", "rzu", "sp3", "Đăng", "Post")):
         # Thử tìm và tap trực tiếp nút Đăng (sp3, text="Đăng", content-desc="Đăng")
         for res_id in ("sp3", "sh8", "shd", "sox", "soz", "sp7", "rbp", "t66"):
             if self._tap_post_with_intent(adapter, xml_text, resource_id=res_id):
                 preview_post_tapped = True
                 break
         if not preview_post_tapped:
             preview_post_tapped = self._tap_post_with_intent(adapter, xml_text, text="Đăng") or \
                                   self._tap_post_with_intent(adapter, xml_text, content_desc="Đăng")
         if preview_post_tapped:
             self._mark_post_surface_recovery_retrying()
             return self._finish_single_post_tap(adapter)
     ```
3. **Atomic Overwrite Stale Post Intent Receipt:**
   - Trong `_record_post_intent()`, bắt `FileExistsError` và đọc payload của file receipt hiện tại:
     ```python
     except FileExistsError:
         try:
             old_payload = json.loads(path.read_text(encoding="utf-8"))
             old_run_id = str(old_payload.get("run_id") or "")
             current_run_id = str(getattr(self.context.reporter, "run_id", "") or "")
             if current_run_id and old_run_id != current_run_id:
                 self._write_post_attempt_receipt(payload)
             else:
                 return False
         except Exception:
             return False
     ```
