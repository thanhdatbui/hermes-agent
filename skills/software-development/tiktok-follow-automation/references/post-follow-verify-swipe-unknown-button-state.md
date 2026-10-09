# Post-Follow Verify Swipe: Trạng thái nút không xác định sau vuốt xác nhận (Case UI-53)

## Triệu chứng
Farm Alert kích hoạt cảnh báo đỏ trên máy farm (ví dụ Máy 51 - row 2):
```
status: "MANUAL_REVIEW"
reason: "MANUAL_REVIEW: trạng thái nút không xác định sau vuốt xác nhận"
```

## Root Cause
Trong `follow_runner/flows/verify_follow.py`:
1. Sau khi tap nút Follow thành công (`cls == "followed"`), flow gọi `_confirm_not_released()` để kéo `pull_to_refresh_profile` nhằm xác thực follow không bị TikTok âm thầm nhả (shadow release / rate limit).
2. Sau khi refresh, `_confirm_not_released()` gọi `cls = classifier(_dump())` để phân loại lại nút hành động.
3. Trên giao diện TikTok mới (TikTok 46.x):
   - Thay vì hiển thị nhãn chữ truyền thống ("Đã follow", "Đang theo dõi", "Following", "Friends"), TikTok chuyển sang layout cụm nút:
     + Nút text chính: **"Nhắn tin"** / **"Message"** (`id/flo`, `id/ff8`, `id/fds` hoặc text/content-desc "Nhắn tin").
     + Nút icon phụ: **icon người kèm dấu tích** (biểu thị quan hệ đang follow / bạn bè).
     + Nút icon phụ: **mũi tên xổ xuống ▼** (tài khoản đề xuất liên quan).
4. `classifier(_dump())` (và `_normalized_action_values` / `FOLLOWED_MARKERS` trong `verify_follow.py` và `selectors.py`) chỉ so khớp các nhãn trong `FOLLOWED_TEXT`.
5. **Cạm bẫy cấu trúc vòng lặp `classify_button`:**
   - Trong `verify_follow.py`, các nút action trong header (`_is_profile_action_node`) mang cùng resource-id (ví dụ `id/flo` hoặc `id/ff8` / `id/fds`).
   - Cụm nút của TikTok 46.x gồm nút chính "Nhắn tin" và các nút icon phụ (icon người có tick, icon mũi tên xổ xuống ▼ gợi ý tài khoản).
   - Nút icon xổ xuống ▼ hoặc icon không có text/content-desc nhận diện được sẽ khiến `has_followed = False` và `has_not_followed = False`.
   - Dòng kiểm tra nghiêm ngặt `if not (has_followed or has_not_followed): return "unknown"` trong vòng lặp duyệt `action_nodes` sẽ lập tức bẻ lái về `"unknown"` ngay khi gặp một nút icon phụ trong cụm, bất kể nút "Nhắn tin" đã được nhận diện trước đó!
   - Ngoài ra, điều kiện `1 <= len(recognized_followed) <= 2` sẽ bị vi phạm nếu số lượng node trong cụm action vượt quá 2 khi gom cả các nút phụ.
   - Nếu nút "Nhắn tin" mang resource-id mới chưa có trong `_ACTION_BUTTON_SUFFIXES`, `_is_profile_action_node` sẽ bỏ sót nếu chỉ kiểm tra resource-id mà không kiểm tra semantic text trong header.
6. Kết quả: `cls` trả về `"unknown"`. Sau 1 lần reload cứu vãn (`_reload()`), `cls` vẫn là `"unknown"` → fail-closed rơi vào:
   `return VerifyResult("manual", "MANUAL_REVIEW: trạng thái nút không xác định sau vuốt xác nhận")`.

## Giải pháp (Fix Pattern)
1. **Mở rộng `FOLLOWED_MARKERS` / `_normalized_action_values` & nhận diện cụm nút:**
   - Thêm nhãn "nhắn tin", "message" vào tập nhận diện trạng thái đã follow (`FOLLOWED_MARKERS`), vì trên profile đối phương, nút "Nhắn tin" chỉ xuất hiện sau khi tài khoản đã được follow (hoặc hai bên là bạn bè/đang theo dõi).
   - Kiểm tra thêm `content-desc` của các nút icon trong vùng profile action (`y < 1200`), nhận diện các icon người có dấu tích / "đang follow" / "bạn bè".
   - Phân biệt nút hành động chính với nút icon phụ trợ: Các nút phụ trợ như icon mũi tên xổ xuống ▼ (gợi ý bạn bè/tài khoản tương tự) không được làm hỏng kết quả phân loại khi nút chính "Nhắn tin" đã hiện diện.
2. **Loại trừ false positive & xử lý cạm bẫy nút phụ:**
   - Chỉ chấp nhận "Nhắn tin" khi nằm trong vùng header profile action (`bounds[1] < 1200`), đảm bảo thuộc package TikTok hợp lệ (`is_tiktok_package`).
   - Đảm bảo nút "Follow" / "Follow lại" không còn hiện diện trong vùng action button (`len(recognized_not_followed) == 0`).
   - Nếu trong cụm `action_nodes` có nút "Nhắn tin" / "Message" / "Đã follow" và không có bất kỳ nút Follow nào, các nút icon dropdown ▼ hoặc nút phụ không nhãn không được gây ra `return "unknown"`.
3. **Focused Test:**
   - Viết test fixture XML với cụm nút ["Nhắn tin", icon người có tick, icon xổ xuống ▼] kiểm tra `classifier` và `_confirm_not_released` trả về `VerifyResult("success")`.
   - Kiểm tra các biến thể package TikTok (`com.ss.android.ugc.trill`, `com.zhiliaoapp.musically`).

## Chi tiết Implementation trong `verify_follow.py` (Case UI-53)
1. **`_is_profile_action_node(node)`**:
   - Thêm fallback cho các nhãn `message_markers`: `{"nhắn tin", "message", "gửi tin nhắn", "send message"}`.
   - Nếu resource-id không nằm trong `_ACTION_BUTTON_SUFFIXES` nhưng node nằm ở header band (`bounds[1] < 1200`), thuộc package TikTok hợp lệ, không phải stat counter và có text/desc trùng `message_markers`, node được chấp thuận là action node.
2. **`classify_button(xml_text)`**:
   - Bỏ qua các node không có text/desc: `if not values: continue`.
   - Khi phát hiện `has_message`, gán `has_followed = True`.
   - Bổ sung short-circuit an toàn:
     ```python
     if recognized_messages and not recognized_not_followed:
         return "followed"
     ```
     Điều này đảm bảo khi nút "Nhắn tin" xuất hiện mà hoàn toàn không có nút Follow/Follow lại/Theo dõi, classifier phân loại ngay là `"followed"` mà không bị chặn bởi các icon rỗng đi kèm.
