# Follow Friends Suggestion Popup: Profile Guard & Navigation Fallback Pattern (06/09/2026)

## 1. Ngữ cảnh & Triệu chứng Lỗi
- **Hiện tượng:** Khi chạy `feed-session-smoke` hoặc `multi-machine-feed-session`, automation bị kẹt hoặc báo fail:
  `reason = "follow_friends_popup_no_close_control"`, `dismissed = False`.
- **Nguyên nhân gốc rễ:**
  1. **False-Positive trên trang Profile:** Hàm `detect_follow_friends_suggestion_popup` và `_detect_follow_friends` (trong `benign_popup_registry.py`) có các text marker ("Tìm bạn bè", "Mời bạn bè", "Bạn bè với", "Theo dõi lại",...) xuất hiện dày đặc trên trang Profile cá nhân (nút "Tìm bạn bè", "Mời bạn bè", "Sửa hồ sơ", tab "Đang follow" / "Follower"). Nếu automation vô tình rơi vào Profile, nó ngỡ là popup gợi ý kết bạn.
  2. **Kẹt biến `current_root` khi fallback BACK:** Trong `dismiss_follow_friends_suggestion_popup`, khi không tìm thấy nút X (`_find_follow_friends_semantic_close_control is None`), hàm gửi phím Back hoặc tap nút quay lại, sau đó recapture hierarchy mới (`after_root`). Tuy nhiên, biến `current_root` không được cập nhật (`current_root = after_root`). Khi hàm kiểm tra lại `_find_follow_friends_semantic_close_control(current_root)` ở cuối khối, nó vẫn check trên hierarchy cũ (trước khi Back) và fail cứng với `follow_friends_popup_no_close_control`.

---

## 2. Giải pháp 2 Lớp (Profile Guard + Navigation Fallback)

### Lớp 1: Profile & Main Feed Guard (Chặn False-Positive)
Trong cả `benign_popup.py` và `benign_popup_registry.py`:
- Kiểm tra dấu hiệu Profile: `"sửa hồ sơ"`, `"edit profile"`, `"đang follow"`, `"follower"`, `"thêm tiểu sử"` (kèm diacritic-free ascii fallback).
- Nếu màn hình là Main Feed hoặc Profile: **BẮT BUỘC** phải có dialog modal thực sự (`android.app.Dialog` hoặc class chứa dialog) HOẶC có nút X semantic close control (`_find_follow_friends_semantic_close_control`).
- Nếu là Profile/Feed mà không có dialog/close control, trả về `False` ngay lập tức!

```python
is_profile = (
    "sửa hồ sơ" in combined or "sua ho so" in combined_ascii or
    "edit profile" in combined or
    "đang follow" in combined or "dang follow" in combined_ascii or
    "follower" in combined or
    "thêm tiểu sử" in combined or "them tieu su" in combined_ascii
)
if is_main_feed or is_profile:
    if not (has_dialog or has_close_control):
        return False
```

### Lớp 2: Navigation Fallback & State Tree Synchronization
Trong `dismiss_follow_friends_suggestion_popup`:
1. **Thử đóng nút X:** Nếu có, tap và sleep 1.0s, capture fresh root và cập nhật `current_root = after_root`.
2. **Fallback Header Back / Back Key:**
   - Tìm nút quay lại trên header: element có id kết thúc `:id/back`, `:id/bq7`, `/back`, `/btn_back` hoặc text/desc in `{"quay lại", "back", "trở về", "tro ve"}`.
   - Nếu tìm thấy và clickable: tap vào nút đó.
   - Nếu không tìm thấy hoặc tap không đóng được: gọi `send_device_back_key(ctx)`.
3. **Cập nhật State Tree:**
   - Sau khi Back/tap: `time.sleep(1.0)`, capture fresh root `after_root, verified = _capture_fresh_root(current_root)`.
   - **BẮT BUỘC gán:** `if verified and after_root is not None: current_root = after_root`.
4. **Xác minh thoát thành công:**
   - Nếu `not detect_follow_friends_suggestion_popup(after_root)` HOẶC màn hình đã hiển thị Main Feed / Profile (`_is_main_feed_or_profile_screen(after_root)`):
     -> Đánh dấu `closed = True`, `reason = f"followed_{followed_count}_friends_and_dismissed_via_back"`.
5. **Không fail cứng:**
   - Ở nhánh cuối cùng: nếu `_is_main_feed_or_profile_screen(current_root)` hoặc popup không còn detect, trả về `dismissed = True`. Không báo `follow_friends_popup_no_close_control` nếu đã thoát thành công về Feed/Profile.

---

## 3. Lệnh Kiểm Chứng Canary
```bash
env -u PYTHONPATH powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <ID> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
```
Luôn kiểm tra `multi-machine-feed-session completed` với `Status: success`.
