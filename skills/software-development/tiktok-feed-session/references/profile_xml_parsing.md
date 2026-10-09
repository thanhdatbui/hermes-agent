# Profile XML Parsing & Video Views Extraction

## Quy tắc bóc tách video views trong trang cá nhân (`_profile_identity_from_xml`)
- File: `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py`
- Các node biểu thị số lượt xem video (như `1.2M`, `450`, `12.5K`) nằm trên lưới thumbnail cá nhân, thường ở tọa độ nửa dưới màn hình (`y >= 850`).
- Cần loại bỏ các nhãn đặc thù như: `Đã ghim`, `Pinned`, `Nháp`, `Draft`, `Thích`, `Like`.
- Regex pattern nhận diện view: `^\d+(\.\d+)?[KMkm]?$`.
- Thứ tự lấy: Sắp xếp theo vị trí hiển thị từ trên xuống dưới (`y1 // 100`), từ trái sang phải (`x1`) và lấy tối đa 6 view gần nhất (`latest_views`).

## Lưu ý kiểm thử / verification độc lập
- `feed_swipe_smoke.py` thực hiện import `from core.actions import Actions` (với thư mục `core` nằm trực tiếp dưới `python_runner`).
- Khi viết script kiểm thử / import độc lập vào Python REPL, cần thêm `python_runner` vào `sys.path`:
  ```python
  import sys
  sys.path.insert(0, r'D:/Taadaa/tiktok-luot nuoi acc/python_runner')
  from flows.feed_swipe_smoke import _profile_identity_from_xml
  ```
