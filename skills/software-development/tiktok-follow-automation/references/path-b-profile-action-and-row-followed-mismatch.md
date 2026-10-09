# Case UI-58: Path B Fail — Row Nói Followed Nhưng Profile Manual

## 1. Triệu chứng & Bối cảnh Hiện trường (Máy 37 — Row 1)
- **Farm Alert:** `MANUAL_REVIEW: Path B fail (row nói followed nhưng profile manual)`
- **Artifact:** `D:/Taadaa/runtime/kibe/live/<date>/row-<N>-<time>/<run_id>/machines/machine_<M>/<run_id>/follow_result.json`
- **Chỉ số:** `status: "MANUAL_REVIEW"`, `exit_code: 1`, `failed: 1`, `follow_failed: false`.
- **Trạng thái thực tế:** Runner đã follow thành công nhiều nick trước đó (ví dụ Máy 37 đã follow 6 nick: `ngoc.phan39`, `demarfpmafi`, `lilyanzj8n1`, `aliciwwt40z`, `leiamiyxrqg`, `evalykgbqpd`), không bị TikTok rate-limit (`follow_failed: false`, `fail_streak: 0`).

## 2. Root Cause & Vị trí Mã Nguồn
Lỗi phát sinh tại `follow_runner/flows/mode2_follow_followers.py` trong hàm `follow_one_follower`:
```python
cls = _verify_row_after_tap(engine, current_row["username_node"], uid)
if cls == "followed":
    # Path B: mở profile, kiểm tra identity + trạng thái hiện tại
    pb = _path_b_verify(engine, current_row["username_node"], uid)
    if pb == "failed":
        return "failed", "FOLLOW_FAILED: TikTok không nhận follow (profile vẫn chưa follow)"
    if pb != "followed":
        return "manual", f"MANUAL_REVIEW: Path B fail (row nói followed nhưng profile {pb})"
    return "followed", ""
```

### Cơ chế kiểm tra 2 bước:
1. **Bước 1 (Row verification):** `_verify_row_after_tap` kiểm tra lại button ngay trên hàng follower list sau khi tap. Nếu nút đổi sang "Đang follow" / "Bạn bè" / "Following", trả về `cls = "followed"`.
2. **Bước 2 (Path B profile verification):** `_path_b_verify` tap mở profile cá nhân của nick vừa follow để đối soát quan hệ độc lập.
   - `_path_b_verify` gọi `_classify_profile_action(profile_xml)` để phân loại nút action trên profile header (ủy nhiệm sang `classify_button` trong `verify_follow.py`).
   - `classify_button` lọc candidate qua `_is_profile_action_node(node)`:
     ```python
     if any(rid == ab or rid.endswith(ab) for ab in _ACTION_BUTTON_SUFFIXES):
         return True
     message_markers = {"nhắn tin", "message", "gửi tin nhắn", "send message"}
     values = _normalized_action_values(node)
     return bool(values & message_markers) or any(m in v for v in values for m in message_markers)
     ```
   - **Root Cause Selector Drift (`id/flp` & Bạn bè/Friends):**
     + Trên TikTok 46.x khi tạo quan hệ mutual follow (hoặc layout profile mới), nút "Bạn bè" / "Friends" mang resource-id `id/flp`.
     + `_ACTION_BUTTON_SUFFIXES` chỉ có `(':id/fds', ':id/ff8', ':id/fij', ':id/fi6', ':id/flo', ':id/follow_button')` — THIẾU `id/flp`.
     + `_is_profile_action_node` chỉ fallback text cho `message_markers`, KHÔNG có `friend_markers` `{"bạn bè", "friends"}`.
     + Kết quả probe thực tế:
       * `id/flp` + `text="Bạn bè"` $\rightarrow$ `_is_profile_action_node` trả về `False` $\rightarrow$ `action_nodes` rỗng $\rightarrow$ `classify_button` trả về `"unknown"`.
       * `id/flo` + `text="Bạn bè"` $\rightarrow$ trả về `"followed"`.
       * `id/flp` + `text="Friends"` $\rightarrow$ trả về `"unknown"`.
     + Khi `_classify_profile_action` trả về `"unknown"`, `_path_b_verify` lập tức đánh rớt thành `pb = "manual"` và emit Farm Alert: `MANUAL_REVIEW: Path B fail (row nói followed nhưng profile manual)`.
   - Đồng thời nếu sau khi `adapter.back()` từ profile về lại list mà RecyclerView render trễ hoặc bị kẹt overlay khiến `restored = False` (`not (dump_ok and back_ok and restored)`), `_path_b_verify` cũng fail-closed trả về `pb = "manual"`.

## 3. Quy chuẩn Khắc phục & Điều tra O(1)
1. **Mở rộng `verify_follow.py` và `mode2_follow_followers.py`:**
   - Thêm `id/flp` (`:id/flp`) vào `_ACTION_BUTTON_SUFFIXES` và `_ACTION_BUTTON_IDS`.
   - Bổ sung `friend_markers = {"bạn bè", "friends"}` vào `_is_profile_action_node` để các button mang nhãn Bạn bè/Friends không bị loại bỏ kể cả khi resource-id bị biến thể.
   - Bổ sung fallback kiểm tra văn bản trong `_classify_profile_action` nếu `classify_button` trả về `"unknown"` nhưng header band (`y < 1200`) có node thuộc TikTok package chứa text/content-desc Bạn bè / Nhắn tin / Friends / Message.
2. **Cấm Bẫy Grep Timeout 900s trong Runtime:**
   - Tuyệt đối không chạy `grep -rn` hoặc `find` trên thư mục ca chạy `/d/Taadaa/runtime/.../row-N-*/`.
   - Một thư mục ca chứa tới 40 máy chạy song song với hàng chục nghìn file XML dump và screencap. Lệnh grep đệ quy chắc chắn dính timeout 900s và đốt sạch lượt gọi của session.
   - Luôn truy cập O(1) theo đúng đường dẫn:
     `/d/Taadaa/runtime/kibe/live/<date>/<row_folder>/<run_id>/machines/machine_<N>/<run_id>/follow_result.json`
     hoặc chỉ grep trên đúng 1 file `log.jsonl` của máy đó.
