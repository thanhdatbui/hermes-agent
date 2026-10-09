# Phân Tích Lịch Sử Tê Liệt Nút Like (18/08 - 12/09/2026), Làn Sóng Shadowban Follow & Tối Ưu Feed

## 1. Mốc Thời Gian & Nguyên Nhân Tử Huyệt Mất Like Suốt 26 Ngày

### 1.1. Mốc biến cố 18/08/2026
- **Trước ngày 18/08/2026:**
  - App TikTok bản cũ thiết kế nút Like gồm 2 node lồng nhau:
    - Node cha ngoài hiển thị số like: `<node resource-id="...:id/g0j" content-desc="Thích video. 355,6K lượt thích" />`
    - Node con bên trong là icon trái tim: `<node resource-id="...:id/g00" class="android.widget.ImageView" content-desc="Thích" />`
  - Code bot so sánh bằng tuyệt đối `content_desc == "Thích"` -> Khớp trúng node con -> Bấm Like đều đặn (máy 21, 33, 34 ngày 17/08 đều có lượt like ghi nhận).
- **Từ đêm 17/08 rạng sáng 18/08/2026:**
  - TikTok cập nhật layout UI: Xóa bỏ node con `ImageView`, gộp thành 1 node duy nhất:
    `<node resource-id="...:id/g2w" class="android.widget.Button" content-desc="Thích video. 41,3K lượt thích" clickable="true" />`
  - Chuỗi `content-desc` luôn đi kèm số lượt like động (VD: `"Thích video. 41,3K lượt thích"`, `"Thích video. 2.462 lượt thích"`, `"Like video. 1.2M likes"`).
  - Code so sánh bằng tuyệt đối `== "Thích"` bị **mù hoàn toàn**: Trả về `None` trên 100% video!

### 1.2. Hậu quả đối với hệ thống (Làn sóng Shadowban Follow từ 05/09 - 12/09)
- Suốt 26 ngày (18/08 đến 12/09): Cả dàn 80 máy lướt hàng nghìn video mỗi ngày nhưng **0 lượt Like nào phát sinh**.
- TikTok nhận diện hành vi: Tài khoản chỉ swipe cơ học theo nhịp cố định không hề có tương tác cảm xúc người thật (zombie behavior).
- **Quy luật ngấm đòn theo thời gian:**
  - **27/08 - 03/09:** Tài khoản còn điểm Trust cũ, chạy đỉnh cao 900 - 1.934 follow/ngày, 0 máy dính nhả.
  - **04/09 - 06/09:** Trust score cạn kiệt, bắt đầu xuất hiện máy dính nhả (ngày 05/09: 10 máy).
  - **07/09 - 12/09:** Vỡ trận hàng loạt: ngày 07/09 (23 máy), ngày 08/09 (20 máy), ngày 09/09 (27 máy), ngày 12/09 đỉnh điểm 40 máy dính cờ nhả follow (hơn 90% dàn Tik1 & Tik2 dính streak >= 2).
- **Chứng minh thực nghiệm trên máy thật (Máy 24 - 12/09/2026):**
  - Mở profile bằng deep link ADB -> Bấm Follow bằng tay `input tap`.
  - Giữ nguyên màn hình 60s: Nút hiển thị ảo `Nhắn tin` (do app cache local).
  - Thoát ra Home vào lại profile: Nút lập tức quay lại màu đỏ `Follow` -> **Chứng minh server TikTok Silent Drop follow thật sự 100%, không phải do bot phán nhầm hay mạng lag.**

---

## 2. Bản Vá Đa Điểm Cho Lướt Feed (`feed_swipe_smoke.py`)

### 2.1. Nhận diện nút Like bằng Prefix Match & đa ngôn ngữ
```python
liked: UIElement | None = None
like: UIElement | None = None

for element in iter_elements(root):
    desc = (element.content_desc or "").strip()
    txt = (element.text or "").strip()
    desc_lower = desc.lower()

    # Kiểm tra nếu video đã được thích rồi (tránh bấm lại làm hủy like)
    if (
        desc_lower.startswith("đã thích video")
        or desc_lower.startswith("bỏ thích")
        or desc_lower.startswith("liked video")
        or desc == LIKED_BUTTON_CONTENT_DESC
    ):
        liked = element
        break

    # Tìm nút Thích video (LƯU Ý: UIElement truy cập clickable qua attrib dict!)
    if not like and element.center and element.attrib.get("clickable") == "true":
        if (
            desc_lower.startswith("thích video")
            or desc == "Thích"
            or desc_lower.startswith("like video")
            or desc == "Like"
            or "like_icon" in str(element.resource_id or "").lower()
        ):
            like = element
```

### 2.2. Nhận diện nút Follow trên video & loại trừ top header
- Tránh bắt nhầm tab navigation ở đỉnh màn hình (`bounds[1] < 350`):
```python
already_following: UIElement | None = None
follow: UIElement | None = None

for element in iter_elements(root):
    if not element.center or element.center[1] < 350:
        continue
    desc = (element.content_desc or "").strip()
    txt = (element.text or "").strip()
    is_clickable = element.attrib.get("clickable") == "true"

    if is_clickable and (
        desc.startswith("Following") or desc == "Following" or txt == "Following"
        or desc == "Đang follow" or txt == "Đang follow"
        or desc == "Đã follow" or txt == "Đã follow"
        or desc == "Bạn bè" or txt == "Bạn bè"
    ):
        already_following = element
        break

    if not follow and is_clickable:
        if (
            desc.startswith("Follow ") or desc == "Follow"
            or desc.startswith("Theo dõi") or desc == "Theo dõi"
        ):
            follow = element
```

---

## 3. Tối Ưu Thời Lượng Phiên & Nhịp Phân Bổ

### 3.1. Nâng mốc số lượng video trong phiên
- Nâng `FEED_SESSION_MIN_TOTAL_VIDEOS` từ 8 lên **16 video**.
- Nâng `FEED_SESSION_MAX_TOTAL_VIDEOS` từ 11 lên **22 video**.
- Nâng `FEED_SESSION_MAX_SWIPES` từ 15 lên **28 swipes**.

### 3.2. Nhịp Fast Swipe xen kẽ Deep Inspect
- **Fast Swipe (Chỉ áp dụng For You):**
  - Dừng ngẫu nhiên 2.0s - 5.0s (xem nhanh như người thật lướt qua clip không thích), quẹt không dump XML (0% like).
- **Deep Inspect (Xen kẽ mỗi 2-4 video):**
  - Xem chậm 8s - 12s, dump XML, tỷ lệ Like bù trừ tự động tăng lên **40%** (`DEFAULT_DEEP_LIKE_RATE_PERCENT`).
  - Trung bình trên toàn bộ For You: tỷ lệ like đạt **10% - 12%** chuẩn tự nhiên.
- **Tab Following & Bạn bè (30% thời lượng phiên):**
  - **100% Deep Inspect**, xem chậm 4s - 15s, tỷ lệ like 30% (Following) và 70% (Bạn bè).
- **Tổng thời gian phiên thực tế:** Đạt khoảng 16 - 20 phút/máy, nằm gọn trong timeout an toàn 35 phút (2100s).

---

## 4. Giám Sát Watchdog Telegram
- Đã bổ sung chỉ số `total_likes_count` tổng hợp từ `details.like_counts` trong `summary.txt` của tất cả các máy.
- Tiêu đề báo cáo phiên: `• Lướt Feed (N lượt thả tim):` giúp operator phát hiện ngay nếu có đợt cập nhật UI mới từ TikTok làm mất like.
