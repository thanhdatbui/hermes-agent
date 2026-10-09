# TikTok 46.9.3 Selector Drift (id/fm9) & Fail-Closed Profile Action Classification

## 1. Hiện tượng & Triệu chứng (Live Incident 2026-09-20 - Máy 38)
1. **Mode 1 (Search Follow):**
   - Vào search profile nick mục tiêu (ví dụ `@hunh.m.linh571`, `@kimm.ngnn614`).
   - Màn hình hiện rõ nút đỏ "Follow" hoặc "Follow lại" kèm nút "Nhắn tin", nhưng bot mở profile xong lập tức back ra, không hề tap nút follow.
   - Script đánh dấu nick vào `skipped` với lý do "đã follow sẵn (skip)".
2. **Mode 2 (Anchor & Following List):**
   - Vào profile Anchor, nút "Follow" của Anchor vẫn đỏ lòm (chưa follow), nhưng bot vẫn ngang nhiên nhảy vào tab Following của Anchor để cào danh sách nick con bên trong.
   - Khi follow nick con trong list, dù server nhả follow (nút nhảy lại màu đỏ), bot vẫn tiếp tục cắm đầu follow tiếp các nick sau và ghi nhận thành công (false positive) vào file `follow_state`.

## 2. Nguyên nhân gốc rễ (Root Cause)
- **TikTok 46.9.3 đổi Action Button ID:** Cả nút "Follow"/"Follow lại" và nút "Nhắn tin" trên profile đều dùng resource-id `com.ss.android.ugc.trill:id/fm9`.
- **Lỗ hổng trong `verify_follow.py`:**
  - Whitelist `_ACTION_BUTTON_SUFFIXES` thiếu `":id/fm9"` và `"id/fm9"`.
  - Hàm `_is_profile_action_node(node)` từ chối node nút Follow (do không khớp ID), nhưng lại chấp nhận node "Nhắn tin" (do text match `message_markers`).
  - Hệ quả: `classify_button()` thấy có 1 nút "Nhắn tin" và 0 nút "Follow" được công nhận -> kết luận profile ở trạng thái **`followed`** dù nút Follow đỏ lòm vẫn nằm sờ sờ trên màn hình!
- **Lỗ hổng Fail-Closed trong `mode2_follow_followers.py`:**
  - Trong `_ensure_anchor_followed`: Nhánh `if classification != "not_followed": return profile_xml` biến mọi trạng thái phân loại không rõ ràng (`unknown`) thành hợp lệ, cho phép bot cào list của Anchor chưa follow.
  - Trong `_path_b_verify`: Khi profile nick con không đạt trạng thái `followed` sau khi mở, hàm trả về `"manual"` thay vì `"failed"`, khiến runner không gọi `state.set_follow_failed()`, dẫn đến follow bị nhả nhưng vẫn đếm tăng ngân sách.

## 3. Quy tắc khắc phục chuẩn (Mandatory Fix Pattern)
1. **Mở rộng Whitelist Selector:**
   - Luôn duy trì ID mới của TikTok 46.9.3:
     ```python
     _ACTION_BUTTON_SUFFIXES = (
         ":id/fds", ":id/ff8", ":id/fij", ":id/fi6", ":id/flo", ":id/flp", ":id/fm9", ":id/follow_button",
         "id/fds", "id/ff8", "id/fij", "id/fi6", "id/flo", "id/flp", "id/fm9", "id/follow_button",
     )
     ```
2. **Chế độ Fail-Closed Anchor tuyệt đối:**
   - Trong `_ensure_anchor_followed`: CHỈ ĐƯỢC PHÉP tiếp tục khi và chỉ khi `classification == "followed"`.
   - Nếu sau khi xem video và reload mà trạng thái vẫn không phải `followed` (kể cả `unknown`), BẮT BUỘC đặt `state.set_follow_failed()` và return `None` để ngắt phiên ngay lập tức.
3. **Chế độ Fail-Closed Path B tuyệt đối:**
   - Trong `_path_b_verify`: Mọi trường hợp mở profile thành công mà không thấy trạng thái `followed` rõ ràng (nút vẫn là Follow/Follow lại đỏ do TikTok nhả), BẮT BUỘC coi là `failed`, kích hoạt `state.set_follow_failed()` và dừng phiên ngay.
4. **Đối soát Ground Truth qua Dashboard Crawler:**
   - Bắt buộc lấy snapshot số lượng `following_count` của tài khoản trước và sau ca chạy.
   - Nếu runner báo `followed > 0` nhưng delta `following_count` trên server không tăng, hệ thống phải kích hoạt còi báo động lỗi báo cáo sai lệch và đưa acc vào diện rate-limit cooldown.
