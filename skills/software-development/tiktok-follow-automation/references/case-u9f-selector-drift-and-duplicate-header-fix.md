# Case: Fix Selector Drift id/u9f, Duplicate Selected Header Trap & Followed Re-ordering Trong Mode 2

## 1. Bối cảnh & Hiện tượng (2026-09-27)
- **Hiện tượng 1:** Toàn farm chạy follow chỉ đạt 1-3 lượt/máy/phiên thay vì 10-20 lượt như thiết kế. Log ghi nhận `_open_following_tab` fail sau ladder lần 2 trên các nick Anchor, dẫn đến Mode 2 bị ép về 1 lượt Anchor và làm cạn soft-budget thời gian (180s) của Mode 1.
- **Hiện tượng 2:** Báo cáo đối soát TikTok Web in lệch âm vô lý trên các máy dính nhả follow (ví dụ M58 script bắt được nhả follow nhưng đối soát vẫn báo `script báo 2 | web tăng +0 (Lệch -2)`).
- **Hiện tượng 3:** Sau khi follow thành công 1 nick trong danh sách Following của Anchor, khi quay lại màn hình hoặc chụp ảnh kiểm chứng thì không thấy nick đó ở đầu danh sách nữa.

---

## 2. Phân tích Nguyên nhân Kỹ thuật

### A. Bẫy Nhân Đôi Selected Header Trong `_classify_follower_surface`
- **Cơ chế lỗi:** Trên Android UI dump của TikTok bản mới, cả node container cha (`android.widget.LinearLayout`) và node con (`android:id/text1` - `android.widget.TextView`) đều mang thuộc tính `selected="true"` và cùng chứa text `Đã follow 138`.
- Khi `_classify_follower_surface` duyệt danh sách node tìm selected header:
  `selected_headers = [n for n in nodes if n.get("selected") and match_re]`
  -> Kết quả trả về `len(selected_headers) == 2`.
- Do code chặn cứng `if len(selected_headers) != 1: return "invalid"`, toàn bộ màn hình danh sách Following thực tế bị coi là `invalid`, khiến runner poll timeout 25s và kích hoạt ladder retry thất bại!
- **Giải pháp:**
  ```python
  has_text1_selected = any(c.get("resource_id") == "android:id/text1" and c.get("selected") for c in nodes)
  selected_headers = []
  for node in nodes:
      if not node.get("selected"):
          continue
      if has_text1_selected and node.get("resource_id") != "android:id/text1":
          continue
      match = _FOLLOWER_HEADER_RE.fullmatch(_semantic_text(node))
      if match is not None and match.group(1).casefold() in _FOLLOWER_EMPTY_LABELS:
          selected_headers.append((node, match))
  ```

### B. Selector Drift Nút Follow `id/u9f`
- TikTok bản mới cập nhật ID nút Follow trong danh sách Following thành `com.ss.android.ugc.trill:id/u9f` (trước đây là `u68`, `u2f`, `tum`, `tvn`...).
- Do thiếu `id/u9f` trong `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS` (`selectors.py`), `_cluster_follower_rows` không gán được nút bấm (`follow_button: None`), khiến các row hợp lệ bị bỏ qua.
- **Giải pháp:** Bổ sung `com.ss.android.ugc.trill:id/u9f`, `:id/u9f`, `id/u9f` vào `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS`.

### C. Cơ chế Sắp Xếp Danh Sách Của TikTok Sau Khi Bấm Follow
- Khi nick A bấm Follow nick B trong danh sách Following của Anchor:
  - TikTok chuyển trạng thái của B sang "Bạn bè" (nếu follow chéo) hoặc "Đang follow".
  - Thuật toán của TikTok lập tức re-order lại danh sách hoặc đẩy các nick đã follow xuống dưới / phân trang lại.
  - Khi mở lại danh sách hoặc re-dump, nick vừa follow sẽ không còn nằm ở vị trí cũ (top list), thay vào đó là các nick chưa follow khác được đẩy lên. Đây là hành vi bình thường của TikTok, không phải lỗi.

### D. Lỗ Hổng Đối Soát Watchdog Đối Với Máy Nhả Follow
- Trong `feed_session_watchdog.py`, khi tổng hợp `m_to_reported`, hàm tính gộp `cross_cnt + nat_cnt` mà không kiểm tra cờ `follow_failed`.
- Nếu nick dính `FOLLOW_FAILED` trong phiên (TikTok nhả follow), `reported_count` vẫn giữ nguyên số lượt tự nhiên trước đó ➔ Tạo ra chênh lệch âm giả mạo trong báo cáo đối soát.
- **Giải pháp:** Nếu máy có `follow_failed == True`, gán `m_to_reported[str(m)] = 0` để đối soát phản ánh đúng thực tế.
