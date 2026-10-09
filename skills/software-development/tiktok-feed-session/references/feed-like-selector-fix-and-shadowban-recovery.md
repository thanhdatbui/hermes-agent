# Root Cause & Fix: Feed Like Button Selector Mismatch & Shadowban Recovery

## 1. Hiện tượng & Bằng chứng sự cố (Incident Evidence)
- **Thực tế vận hành ngày 2026-09-12:**
  - 80 máy chạy Ca 1 Row 2 lướt feed hoàn thành 556 lượt swipe.
  - **TỔNG SỐ LƯỢT LIKE (THẢ TIM) CỦA TOÀN BỘ 80 MÁY = 0!** (`"like_counts": {"for-you": 0, "following": 0, "friends": 0}`).
  - Toàn bộ dàn tài khoản lướt feed như "zombie": quẹt màn hình liên tục mỗi 2–3 giây nhưng không có bất kỳ tương tác cảm xúc / engagement nào.
  - Kết quả: Điểm Trust Score của tài khoản trên TikTok server = 0. Hơn 90% nick Tik 1 và Tik 2 (127/144 nick) bị dính `fail_streak >= 1` và `Action Block: Silent Follow Drop` (nhả follow).

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Lỗi Selector So Sánh Bằng Tuyệt Đối (`feed_swipe_smoke.py:13584`):**
   - Hằng số cũ: `LIKE_BUTTON_CONTENT_DESC = "Thích"`.
   - Hàm `find_by_fields(root, content_desc=LIKE_BUTTON_CONTENT_DESC)` so sánh bằng tuyệt đối: `element.content_desc == "Thích"`.
   - **Thực tế trên giao diện TikTok 46.x (Android):**
     `content-desc="Thích video. 41,3K lượt thích"` hoặc `"Thích video. 2.462 lượt thích"` hoặc `"Like video. 1.2M likes"`.
     TikTok luôn gắn kèm số lượng lượt thích vào content-desc!
   - Do so sánh bằng tuyệt đối, `find_by_fields` LUÔN LUÔN trả về `None`. 100% video đều bị bỏ qua không tap!
2. **Cạm bẫy `UIElement` trong `automation-core`:**
   - Đối tượng `UIElement` parse từ XML **không có thuộc tính trực tiếp `.clickable`** (truy cập `element.clickable` sẽ ném `AttributeError`).
   - Bắt buộc phải đọc qua dict thuộc tính: `element.attrib.get("clickable") == "true"`.
3. **Lỗi bắt nhầm Top Tab trong `_maybe_follow_video` (`feed_swipe_smoke.py:13673`):**
   - Kiểm tra `FOLLOWING_BUTTON_TEXT = "Following"` trên toàn màn hình làm bắt nhầm vào thanh điều hướng tab "Following" / "Đang follow" ở đỉnh màn hình (`center[1] < 350`).
   - Cần lọc bỏ vùng header (`center[1] >= 350`) để chỉ bắt nút Follow/Following ở thân video.

## 3. Giải pháp chuẩn hoá (Standard Fix)
Trong `python_runner/flows/feed_swipe_smoke.py`:
```python
# Kiểm tra nếu video đã được thích rồi (tránh bấm lại làm hủy like)
for element in iter_elements(root):
    desc = (element.content_desc or "").strip().lower()
    if (
        desc.startswith("đã thích video")
        or desc.startswith("bỏ thích")
        or desc.startswith("liked video")
        or desc == LIKED_BUTTON_CONTENT_DESC.lower()
    ):
        liked = element
        break

# Tìm nút Thích video (hỗ trợ cả For You, Following, Bạn bè trên EN/VN)
if not like and element.center and element.attrib.get("clickable") == "true":
    if (
        desc.startswith("thích video")
        or desc == "thích"
        or desc.startswith("like video")
        or desc == "like"
        or "like_icon" in str(element.resource_id or "").lower()
    ):
        like = element
```

## 4. Thực nghiệm Verify trên thiết bị thật (Máy 24 Canary)
- **Lệnh chạy:**
  `python python_runner/run_tiktok.py --device ce0117112b2a0e3a04 --machine 24 --account hodat07102 --mode feed-session-smoke --allow-feed-swipe --allow-navigation-only --allow-benign-popup-dismiss --no-verify-profile --allow-like --like-rate-percent 20 --max-swipes 3`
- **Kết quả log (`log.jsonl`):**
  `{"step": "swipe_1_after/like", "action": "like_video", "selector": {"content_desc": "Thích", "center": [999, 1064]}, "result": "success"}`
- **Kết quả `summary.txt`:** `"like_counts": {"for-you": 1}` -> Thả tim thành công trên màn hình thật!

## 5. Bản chất Shadowban & Quy luật hồi phục Cooldown
- **Cooldown thuần túy (chỉ ngâm ngày chờ hết hạn) KHÔNG THỂ giúp nick tự hồi phục**:
  - Dữ liệu quét 144 file state: 100% nick từng bị cờ nhả follow (127 nick) khi hết hạn cooldown (dù ngâm 4 hay 7 ngày) vừa bấm lại đều bị nhả tiếp nếu feed session trước đó là zombie (0 likes).
  - Thuật toán TikTok yêu cầu tín hiệu người dùng thật (Thả tim 15-25%, xem video có dwell time, đăng video đều đặn 48h) trong thời gian ngâm để bù đắp điểm Trust Score.
- **Thực tế thời lượng chạy (Fleet Timing Reality):**
  - Mặc dù chỉ lướt 8–11 video, thời gian chạy thực tế trung bình của mỗi máy là **13.7 phút** (dao động 10–25 phút) do độ trễ dump UI XML, xử lý popup, delay settling và chuyển tab.
  - CẤM tăng số lượng video lên 25–30 nếu không dùng cơ chế `fast_swipe` (bỏ qua dump XML), vì sẽ đẩy thời gian chạy lên 40–50 phút gây vượt `DEFAULT_DEVICE_TIMEOUT_SECONDS` (35 phút) làm sập lịch chạy toàn farm.
