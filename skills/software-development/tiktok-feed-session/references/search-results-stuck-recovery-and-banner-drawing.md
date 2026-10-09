# TikTok Search Results Stuck Recovery & Red Banner Drawing (Case 119)

## 1. Hiện tượng & Triệu chứng (Sự cố Máy 74)
- **Triệu chứng Alert:** `unknown TikTok state; swipe recovery (2 swipes) still stuck`.
- **Hiện trường thực tế:** Màn hình TikTok kẹt ở trang Kết quả tìm kiếm (Search Results / Tab Top với từ khóa tìm kiếm, ví dụ `lu.huyn926`).
  + Có ô `search_edit_text` hoặc `et_search` chứa từ khóa tìm kiếm.
  + Có các tab danh mục kết quả: `Top`, `Người dùng` (Users), `Video`, `Âm thanh` (Sounds), `Live`...
  + Danh sách kết quả dạng grid chứa thẻ user card hoặc video.
  + Góc trên bên trái có nút Back arrow (←).
- **Nguyên nhân gốc rễ (Anti-Pattern):**
  1. Thao tác vuốt feed chuẩn (`input swipe 540 1400 540 400 300`) khi đang ở Search Results chỉ cuộn danh sách kết quả tìm kiếm, không làm thay đổi video hay chuyển màn hình, dẫn đến 2 lần swipe recovery đều thất bại và báo lỗi kẹt `unknown TikTok state`.
  2. Hàm `detect_search_landing_page` (`core/benign_popup.py`) trước đây chỉ nhận diện màn hình gợi ý tìm kiếm (Landing) với các từ khóa tĩnh (`"bạn có thể thích"`, `"nội dung tìm kiếm thịnh hành"`). Khi chuyển sang Search Results, các thẻ user có chữ `"follower"` / `"following"` kích hoạt bộ lọc loại trừ Profile (`negative_markers`), khiến detector trả về `None`.
  3. Hàm `_swipe_recovery_on_stuck` (Section 1B trong `feed_swipe_smoke.py`) chỉ kiểm tra `DetailActivity` và nút `:id/bq7`, hoàn toàn thiếu logic nhận diện màn hình Search Results để điều hướng quay về Home Feed.

---

## 2. Giải Pháp Chuẩn 2 Tầng (Dual-Layer Fix)

### Tầng 1: Nhận diện Search Results trong `detect_search_landing_page` (`core/benign_popup.py`)
- Nhận diện `has_search_input`:
  ```python
  has_search_input = any(
      (element.attrib.get("class", "").endswith("EditText")
      or any(term in (element.resource_id or "").lower() for term in ("search_input", "et_search", "search_edit_text", "tv_search_input", "tv_search_textview")))
      and (not element.attrib.get("package") or _is_tiktok_context_element(element))
      for element in elements
  )
  ```
- Nhận diện các tab danh mục `search_tab_terms`:
  ```python
  search_tab_terms = {"top", "người dùng", "users", "video", "videos", "âm thanh", "sounds", "live", "địa điểm", "places", "bài viết"}
  has_search_tabs = sum(1 for t in texts + descs if (t or "").strip().lower() in search_tab_terms) >= 1
  is_search_results = has_search_input and has_search_tabs
  ```
- **Bỏ qua loại trừ Profile (`follower`, `following`) khi `is_search_results` là True:**
  ```python
  if not is_search_results:
      profile_markers = ("đã follow", "following", "follower", "followers")
      if any(neg in combined for neg in profile_markers):
          return None
  ```
- Gắn thêm marker tag `search_results_page` để caller ghi nhận chính xác.

### Tầng 2: Thoát Search Results trong `_swipe_recovery_on_stuck` (`flows/feed_swipe_smoke.py`)
Tại Section 1B:
1. Phát hiện `is_search_results`:
   - Activity chứa `"search"`.
   - Hoặc XML chứa `search_edit_text`, `et_search` và các tab kết quả (`search_tab_count >= 1`).
2. Điều hướng thoát màn hình:
   - Tìm nút Back (resource-id kết thúc bằng `:id/bq7`, `btn_back`, text/desc `"quay lại"`, `"back"`, `"←"` hoặc fallback ô bấm không nhãn góc trên bên trái `bounds[0] <= 180, bounds[1] <= 320`).
   - Fallback nếu không tap được nút Back: gửi `input keyevent 4` (BACK).
   - Bổ sung fallback chạm tab Trang chủ đáy (`:id/home` hoặc `"trang chủ"`, `"home"`) để chắc chắn app quay về Feed chính trước khi thực hiện vuốt.

---

## 3. Kỹ Thuật Vẽ Banner Đỏ Cảnh Báo `[MAY N]` Không Lỗi PIL C-Extension

### Cạm bẫy:
Trên Windows, môi trường host mặc định của Hermes Agent (`C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv`) có thể gặp lỗi ABI C-extension:
```text
ImportError: cannot import name '_imaging' from 'PIL'
```
Nếu gọi `python -c "from PIL import ..."` trực tiếp qua terminal, bash sẽ mượn python của host venv và văng lỗi trên, không vẽ được banner đỏ.

### Cách xử lý an toàn:
Bắt buộc chạy bằng Python của môi trường farm (`automation`) kèm xóa rỗng `PYTHONPATH`:
```bash
PYTHONPATH="" "D:/Taadaa/python-envs/automation/Scripts/python.exe" -c "
from PIL import Image, ImageDraw, ImageFont
import datetime

img_path = 'C:/Users/Kibe/AppData/Local/Temp/machine_N_canary.png'
out_path = 'C:/Users/Kibe/AppData/Local/Temp/machine_N_canary_banner.png'
im = Image.open(img_path)
w, h = im.size
banner_h = int(h * 0.05)
draw = ImageDraw.Draw(im)
draw.rectangle([(0, 0), (w, banner_h)], fill=(220, 20, 60))
now_str = datetime.datetime.now().strftime('%H:%M:%S %d/%m')
text_str = f'[MAY N] CANARY PASS - {now_str}'
try:
    font = ImageFont.truetype('arial.ttf', int(banner_h * 0.6))
except Exception:
    font = ImageFont.load_default()
bbox = draw.textbbox((0, 0), text_str, font=font)
tw = bbox[2] - bbox[0]
th = bbox[3] - bbox[1]
draw.text(((w - tw) // 2, (banner_h - th) // 2), text_str, fill=(255, 255, 255), font=font)
im.save(out_path)
"
```
Đảm bảo file ảnh banner đỏ `[MAY N]` luôn được tạo thành công 100% để gửi kèm tin nhắn recovery.
