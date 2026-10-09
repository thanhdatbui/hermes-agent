# Case UI-57: Path B Profile Mutual Follow Button 'id/flp' & Semantic Fallback ('Bạn bè', 'Nhắn tin')

## 1. Triệu chứng
Farm Alert kích hoạt cảnh báo đỏ trên máy farm (ví dụ Máy 37 - Row 1, nick `ngc.trinh6472`):
```text
🚨 [FARM ALERT: MÁY 37] DỪNG PHIÊN
• Quy trình: Follow TikTok (tiktok-follow)
• Máy: 37 | Serial: ce0916091cf8142101 | Nick: ngc.trinh6472
• Triệu chứng: MANUAL_REVIEW: Path B fail (row nói followed nhưng profile manual)
• Hiện trường: GIỮ HIỆN TRƯỜNG FOLLOW
```

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Flow vận hành Mode 2 (`follow_one_follower` trong `mode2_follow_followers.py`):**
   - Sau khi tap nút Follow trên hàng danh sách follower của anchor, runner gọi `_verify_row_after_tap` và nhận diện trạng thái hàng chuyển sang `followed`.
   - Tiến trình kích hoạt kiểm tra đối soát chéo **Path B** (`_path_b_verify`): tap mở profile cá nhân của nick vừa follow để xác minh trực tiếp quan hệ.
   - Tại `_path_b_verify`, hàm `_classify_profile_action(profile_xml)` ủy nhiệm cho `classify_button(xml_text)` trong `verify_follow.py`.
2. **Resource ID Action Button Drift (`id/flp`):**
   - Trên TikTok 46.x, khi tài khoản tạo quan hệ 2 chiều (Mutual Follow / "Bạn bè" / "Friends") hoặc trên một số giao diện profile mới, nút hành động mang resource-id `com.ss.android.ugc.trill:id/flp`.
   - Trước đó, `_ACTION_BUTTON_SUFFIXES` chỉ chứa `('id/fds', 'id/ff8', 'id/fij', 'id/fi6', 'id/flo', 'id/follow_button')`, thiếu hoàn toàn `id/flp`.
   - `_is_profile_action_node` bỏ qua nút này vì không khớp whitelist resource-id, dẫn tới `action_nodes` rỗng hoặc thiếu nút chính.
3. **Cạm bẫy phân loại `classify_button` trả về `unknown`:**
   - Khi nút mang ID lạ hoặc kèm theo các nút icon phụ (dropdown ▼, icon bạn bè), `classify_button` trả về `unknown`.
   - `_classify_profile_action` trước đây không có lớp phòng vệ fallback theo semantic text/content-desc trên vùng profile header.
   - `_path_b_verify` nhận `classification == "unknown"` → trả về `pb = "manual"`.
   - `follow_one_follower` fail-closed: `return "manual", f"MANUAL_REVIEW: Path B fail (row nói followed nhưng profile {pb})"`.

## 3. Giải pháp chuẩn hóa (Fix Pattern)
1. **Bổ sung `id/flp` vào whitelist Action Button (`verify_follow.py`):**
   ```python
   _ACTION_BUTTON_SUFFIXES = (
       ":id/fds", ":id/ff8", ":id/fij", ":id/fi6", ":id/flo", ":id/flp", ":id/follow_button",
       "id/fds", "id/ff8", "id/fij", "id/fi6", "id/flo", "id/flp", "id/follow_button",
   )
   ```
2. **Gia cố semantic fallback cho `_classify_profile_action` (`mode2_follow_followers.py`):**
   Nếu `classify_button(xml_text)` trả về `"unknown"`, kiểm tra vùng profile header action band (`y < 1200`):
   - Quét các nhãn followed/mutual: `{"bạn bè", "friends", "nhắn tin", "message", "đã follow", "đang theo dõi", "following", "gửi tin nhắn", "send message"}`.
   - Quét các nhãn not_followed: `{"follow", "follow lại", "theo dõi"}`.
   - Nếu có nút followed/mutual và HOÀN TOÀN KHÔNG có nút Follow nào → trả về `"followed"`.
   - **Cạm bẫy fail-closed với nút không xác định (như "Đang chờ duyệt"):** Tuyệt đối CẤM fallback trả về `"not_followed"` chỉ vì thấy nút Follow khi mà `classify_button` đã từ chối. Nếu trên profile xuất hiện đồng thời nút thứ 2 không xác định ngữ nghĩa (ví dụ: `Đang chờ duyệt` / `Requested` đi kèm `Follow`), fallback BẮT BUỘC giữ nguyên `"unknown"` để `_path_b_verify` trả về `"manual"`, bảo toàn fail-closed cho `test_path_b_verify_duplicate_semantic_actions_are_manual`. Nếu bẻ lái thành `"not_followed"`, runner sẽ gọi nhầm `state.set_follow_failed()` và báo sai lỗi rate-limit.

   **Mẫu triển khai chuẩn:**
   ```python
   def _classify_profile_action(xml_text: str) -> str:
       from .verify_follow import classify_button

       res = classify_button(xml_text)
       if res == "unknown":
           try:
               nodes = _parse_mode2_nodes(xml_text)
               followed_kw = {
                   "nhắn tin", "send message", "đang theo dõi", "message",
                   "following", "đã follow", "gửi tin nhắn", "friends", "bạn bè"
               }
               not_followed_kw = {"follow lại", "follow", "theo dõi"}
               has_follow_btn = False
               has_followed_btn = False
               for n in nodes:
                   b = n.get("bounds")
                   if not b or b[1] >= 1200:
                       continue
                   vals = {
                       (n.get("text") or "").strip().lower(),
                       (n.get("content_desc") or "").strip().lower(),
                   }
                   vals.discard("")
                   if vals & not_followed_kw:
                       has_follow_btn = True
                   if vals & followed_kw:
                       has_followed_btn = True

               if has_followed_btn and not has_follow_btn:
                   return "followed"
           except Exception:
               pass

       return res
   ```

   **Lệnh kiểm chứng test Path B (bắt buộc 32/32 pass 100%):**
   ```bash
   PYTHONPATH="D:/Taadaa/tiktok-follow" /d/Taadaa/python-envs/automation/Scripts/python.exe -m pytest follow_runner/tests/test_mode2_follow_followers.py -k test_path_b -q -p no:cacheprovider
   ```

## 4. Kỷ luật điều phối Coordinator ↔ Worker (Claude Opus Playbook)
- Khi alert đã xác định triệu chứng cụ thể (`Path B fail (row nói followed nhưng profile manual)`), CẤM Coordinator giao goal điều tra mở khiến worker sa vào vòng lặp đọc lắt nhắt chạm trần 35 turns mà không ghi code.
- Coordinator BẮT BUỘC tra cứu mốc code O(1) qua `session_search`, soạn Patch Contract chuẩn xác (`old_string` → `new_string`) và giao Worker thực thi trong <= 6 tool calls.
