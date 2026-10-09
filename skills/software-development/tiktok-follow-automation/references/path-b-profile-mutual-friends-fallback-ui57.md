# Case UI-57: Mode 2 Path B Profile Mutual Follow ("Bạn bè") & Message Semantic Fallback

## Triệu chứng
Farm Alert trên thiết bị chạy follow (ví dụ Máy 37 `ngc.trinh6472` Row 1):
```text
status: "MANUAL_REVIEW"
reason: "MANUAL_REVIEW: Path B fail (row nói followed nhưng profile manual)"
```
Hiện trường: Trên màn hình danh sách Đã follow của anchor, hàng follower hiển thị "Bạn bè" hoặc sau khi tap follow, kiểm tra chéo profile đối phương (Path B) thì profile hiển thị cụm nút "Bạn bè" / "Friends" hoặc "Nhắn tin" / "Message", nhưng runner dừng lại với `profile manual`.

## Nguyên nhân gốc rễ (Root Cause)
1. **Luồng kiểm tra chéo Path B (`_path_b_verify`):**
   - Trong `mode2_follow_followers.py`, sau khi tap follow trên hàng follower list (`_verify_row_after_tap` trả về `"followed"`), runner tap mở Profile của nick vừa follow để đối soát quan hệ.
   - Tại `_path_b_verify`, runner gọi `_classify_profile_action(profile_xml)`.
   - `_classify_profile_action` ủy nhiệm sang `classify_button(xml_text)` trong `verify_follow.py`.
2. **Lệch Resource-ID & Thiếu Semantic Fallback:**
   - Trên TikTok 46.x, khi tài khoản được follow lại thành quan hệ 2 chiều (Mutual Follow / Bạn bè) hoặc nút hành động đổi sang cụm nút "Nhắn tin" với resource-id mới (`id/flp` hoặc các nút custom), `classify_button` không khớp danh sách whitelist cứng `_ACTION_BUTTON_SUFFIXES` nên trả về `"unknown"`.
   - `_classify_profile_action` trước đây không có lớp fallback ngữ nghĩa, trả nguyên `"unknown"` về `_path_b_verify`.
   - `_path_b_verify` nhận kết quả khác `"followed"` nên fail-closed thành `return "manual"`, dẫn đến `MANUAL_REVIEW: Path B fail (row nói followed nhưng profile manual)`.

## Cạm bẫy triển khai Fallback (Regression Pitfall)
- **Bẫy ép trạng thái `not_followed`:**
  Nếu trong fallback viết:
  ```python
  if has_followed_btn and not has_follow_btn:
      return "followed"
  if has_follow_btn and not has_followed_btn:
      return "not_followed"  # <-- NGUY HIỂM!
  ```
  Khi gặp màn hình ambiguous (ví dụ 2 nút trái ngược "Follow" đi kèm "Đang chờ duyệt" hoặc nút follow trong suggested accounts), `classify_button` ban đầu trả về `"unknown"` để fail-closed. Nhưng nhánh `has_follow_btn` ép trả về `"not_followed"`, khiến `_path_b_verify` tưởng là profile chưa follow (trigger `FOLLOW_FAILED: TikTok không nhận follow`) hoặc làm gãy unit test `test_path_b_verify_duplicate_semantic_actions_are_manual`.
- **Chuẩn an toàn:**
  CHỈ trả về `"followed"` khi phát hiện nhãn `followed_kw` và hoàn toàn KHÔNG có nút follow đối kháng:
  ```python
  if has_followed_btn and not has_follow_btn:
      return "followed"
  return res  # Giữ nguyên unknown / fail-closed ban đầu
  ```

## Giải pháp chuẩn hóa trong `mode2_follow_followers.py`
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

## Kiểm thử & Xác minh
1. **Unit test:** Thêm `test_classify_profile_action_fallback_friends_and_message` kiểm tra cả "Bạn bè", "Nhắn tin" và ambiguous buttons.
2. **Focused test:** `PYTHONPATH="D:/Taadaa/tiktok-follow" pytest -p no:cacheprovider follow_runner/tests/test_mode2_follow_followers.py -k "test_path_b"`.
3. **Preflight proxy readiness:** Nếu máy dính timeout proxy preflight do stale marker:
   `python -c "from automation_core.readiness import mark_proxy_state; mark_proxy_state('<serial>', 'proxy_ready')"`
