# Case 79 — Follow lại x0 < 50 & Static Comment Bar False-Positive (Máy 74, 03/09/2026)

## Tóm tắt sự cố
Máy 74 dừng phiên với alert `startup ad/splash marker detected` khi đang ở màn
hình video chi tiết (`DetailActivity`) có nút *Follow lại* và thanh bình luận tĩnh.

---

## Pitfall 1 — Nút "Follow lại" bị bỏ qua do điều kiện biên trái quá chặt

**File:** `python_runner/flows/benign_popup.py` → `dismiss_follow_friends_suggestion_popup`

**Anti-pattern:**
```python
if parse_bounds(el.attrib.get("bounds", ""))[0] >= 50:
    ...  # tap Follow lại
```

**Vấn đề:** Trên màn hình video chi tiết, nút Follow lại có `bounds="[36,1625][840,1757]"`
($x_0 = 36 < 50$), nên bị loại trừ hoàn toàn.

**Fix chuẩn:**
- Hạ ngưỡng về `>= 0` (tautology cho tọa độ pixel) — tức là bỏ filter tọa độ trái.
- Sau khi bấm Follow lại (`followed_count > 0`) mà không tìm thấy nút `X` đóng thẻ:
  tự động tìm nút Back (`:id/bq7` / `Quay lại` / `Back`) hoặc gửi phím `BACK`
  để thoát `DetailActivity` về Feed chính.

---

## Pitfall 2 — `detect_comment_input_overlay` nhận nhầm thanh bình luận tĩnh

**File:** `python_runner/flows/benign_popup_registry.py` → `detect_comment_input_overlay`

**Anti-pattern:**
```python
# Branch B (cũ): chỉ cần EditText focused + comment evidence là đủ
if has_focused_input and has_comment_evidence:
    return True
```

**Vấn đề:** Android luôn set `focused="true"` trên EditText `:id/eg4` (`"Thêm bình luận..."`)
kể cả khi bàn phím chưa mở và không có comment drawer. Condition trên false-positive 100%
trên mọi video detail.

**Fix chuẩn:**
```python
# Branch B (mới): yêu cầu thêm bằng chứng bàn phím ảo hoặc comment drawer
if has_focused_input and has_comment_evidence and (keyboard_detected or has_comment_drawer):
    return True
```

**Quy tắc chung:** Bất kỳ detector nào dựa vào `focused="true"` của EditText
PHẢI kết hợp với bằng chứng keyboard/drawer. `focused="true"` đơn độc không phân biệt
được "đang nhập" vs "thanh tĩnh".

---

## Pitfall 3 — Swipe Recovery không thoát được DetailActivity

**File:** `python_runner/flows/feed_swipe_smoke.py` → `_swipe_recovery_on_stuck`

**Anti-pattern:** Hàm chỉ vuốt 2 cái lên/xuống mà không kiểm tra có đang ở
`DetailActivity` hay không.

**Fix chuẩn:** Trước khi vuốt, kiểm tra nút Quay lại (`:id/bq7`). Nếu có → tap Back
để thoát về Feed trước. Vuốt 2 cái chỉ là cơ chế thoát màn hình lạ không có nút Back
rõ ràng.

---

## Pitfall 4 — DELEGATE_TASK vi phạm farm safety khi context mô tả quét rộng

**Sự cố phiên này:** Em dispatch `delegate_task` với context mô tả lệnh `grep -rn` để
tìm log — subagent không bị ràng buộc bởi farm safety rule nếu coordinator truyền
context sai.

**Quy tắc:** Trước khi dispatch bất kỳ subagent nào để fix farm alert:
1. Đọc lại context sẽ truyền.
2. Đảm bảo context KHÔNG chứa `grep -r`, `find`, `os.walk`, `glob(recursive=True)`.
3. Thay bằng lệnh ADB trực tiếp theo serial hoặc `inspect_machine.py <N>`.

---

## Chẩn đoán nhanh khi gặp `startup-ad marker detected` sai

1. Chạy `python D:/Taadaa/tools/inspect_machine.py <N>` — lấy XML hiện trường.
2. Kiểm tra có `EditText` với `text="Thêm bình luận..."` và `focused="true"` không có
   keyboard/drawer không → đây là thanh tĩnh, không phải overlay.
3. Kiểm tra có nút với text chứa `Follow` hoặc `Theo dõi` + bounds $x_0 < 50$ không
   → đây là nút Follow lại bị bỏ qua.
4. Kiểm tra activity name — nếu là `DetailActivity` mà không có tab điều hướng đáy
   → swipe recovery cần tap Back trước.
