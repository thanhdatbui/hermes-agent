# Case UI-10: False-Positive Comment Input Overlay trên FYP Feed / Profile & Độc Lập Lỗi Lặp Swipe Recovery

## 1. Ngữ cảnh & Triệu chứng Sự cố
- **Triệu chứng:** Trong ca chạy lướt feed trên `machine_56` (hoặc các máy Samsung S7), sau khi vuốt video (Swipe 1), bot dừng phiên khẩn cấp và kích hoạt cờ `manual-needed:popup` với lý do `['comment input / story reply overlay marker present']`, đẩy máy vào trạng thái `status: blocked` giữ hiện trường.
- **Nguyên nhân gốc (Root Cause):**
  1. **Khớp từ khóa lỏng lẻo:** Trong `detect_comment_input_overlay`, quét chuỗi `"bình luận"` / `"comment"` / `"viết bình luận"` khớp trúng nút bấm mở bình luận trên video action bar của FYP (`content-desc="Đọc hoặc viết bình luận. Bóc tem bình luận"`), đồng thời cụm điều khiển gửi khớp trúng icon `"Gửi"` / chia sẻ trên thanh tác vụ.
  2. **Thiếu Negative Exclusions:** Không có cơ chế loại trừ khi giao diện đang hiển thị thanh điều hướng đáy FYP chuẩn (`Trang chủ` + `Hồ sơ`/`Hộp thư`/`Cửa hàng`) hoặc tab đầu trang (`Đề xuất`/`Bạn bè`/`Đã follow`) và màn hình Profile chuẩn (`Sửa hồ sơ`, `Follower`, `Đang follow`...).
  3. **Tái sử dụng Stale XML trong Swipe Recovery:** Trong hàm `_swipe_recovery_on_stuck`, vòng lặp thử 2 lần swipe cứu kẹt (`for i in (1, 2)`) nếu tái sử dụng biến `xml_path` của `row` cũ ban đầu ở nhịp thứ 2 sẽ nhận diện nhầm lại overlay đã được đóng từ nhịp 1, gửi tiếp phím `BACK` không cần thiết làm văng khỏi TikTok.

---

## 2. Quy tắc Sửa đổi Chuẩn (Standard Fix Patterns)

### A. Negative Exclusions cho Màn hình Bảng tin (FYP) & Hồ sơ chuẩn
Trong `detect_comment_input_overlay` (`benign_popup_registry.py`):
```python
combined_all = " ".join((el.attrib.get("text", "") + " " + el.attrib.get("content-desc", "") + " " + el.attrib.get("resource-id", "")).lower() for el in tiktok_nodes)
has_home_nav = ("trang chủ" in combined_all or "home" in combined_all) and ("hồ sơ" in combined_all or "profile" in combined_all or "hộp thư" in combined_all or "inbox" in combined_all or "cửa hàng" in combined_all or "shop" in combined_all)
has_feed_tabs = "đề xuất" in combined_all or "for you" in combined_all or "bạn bè" in combined_all or "đã follow" in combined_all or "following" in combined_all
has_profile_elements = ("sửa hồ sơ" in combined_all or "edit profile" in combined_all or "thêm tiểu sử" in combined_all or "add bio" in combined_all) and ("follower" in combined_all or "đang follow" in combined_all or "likes" in combined_all)

# Nếu là FYP feed chuẩn hoặc Profile chuẩn và KHÔNG có bàn phím ảo cũng như KHÔNG có EditText focus
if (has_home_nav or has_feed_tabs or has_profile_elements) and not keyboard_detected and not has_focused_input:
    return False
```

### B. Siết chặt Positive Markers (Yêu cầu bằng chứng Input / IME rõ ràng)
Chỉ khẳng định là overlay nhập bình luận/chat khi:
1. Có `EditText` trong TikTok đang `focused == True` kết hợp với bàn phím ảo hiển thị HOẶC resource-id container nhập bình luận (`comment_input_layout`, `comment_reply_et`, `comment_panel`...).
2. HOẶC có bàn phím ảo (`keyboard_detected == True`) kết hợp với `EditText` trong TikTok.

### C. Độc lập Artifact XML trong Swipe Recovery (`_swipe_recovery_on_stuck`)
Không bao giờ dùng lại `row.get("xml_path")` ở nhịp `i = 2`. Bắt buộc dùng `current_attempt.get("xml_path")` thu được sau lần swipe / dismiss trước đó:
```python
current_attempt = None
for i in (1, 2):
    if i == 1:
        xml_path_val = row.get("xml_path")
        ...
    else:
        xml_path_val = current_attempt.get("xml_path") if isinstance(current_attempt, dict) else None
    ...
    current_attempt = attempt
```

---

## 3. Checklist Kiểm thử & Gate 0.5 Khi Sửa Popup Classifier
- [ ] Bổ sung bài test hồi quy với file XML dump sự cố thực tế (committed fixture trong `fixtures/`).
- [ ] Thêm test case xác nhận màn hình FYP có nút Comment và nút Gửi được phân loại đúng là `"for-you"` (manual_needed: False).
- [ ] Thêm test case xác nhận màn hình Profile chuẩn không bị nhận diện nhầm thành popup.
- [ ] Cập nhật đồng bộ `docs/farm-automation-cases.md` và `docs/uiautomator.md` trước khi gọi Model Review Gate.
