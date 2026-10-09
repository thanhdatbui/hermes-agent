# Kỹ Thuật Xử Lý Kẹt Account Switcher Trên Dàn 8 Nick & Banner Bản Nháp Che Profile

## 1. Bối cảnh & Hiện tượng
Khi vận hành feed-session (`feed-session-smoke` / `multi-machine-feed-session`):
1. **Lỗi `manual-needed:account-switcher` trên máy đủ 8 nick:** Switcher mở bình thường nhưng runner vẫn báo lỗi và dừng session.
2. **Lỗi `profile account mismatch and profile username/display name anchor is unavailable`:** Runner vào Profile nhưng không tìm thấy username hoặc display name để mở switcher.

---

## 2. Nguyên nhân kỹ thuật & Giải pháp đã chuẩn hóa

### 2.1. Switcher 8 nick bị thiếu nút "Thêm tài khoản" trong Viewport
- **Đặc điểm:** Dàn máy chuẩn farm nạp tối đa 8 nick/máy. Khi bung bottom sheet Switcher, 8 tài khoản lấp kín từ trên xuống dưới màn hình `[0,252][1080,1920]`. Nút *"Thêm tài khoản"* bị trôi xuống dưới viewport hiển thị.
- **Bẫy code cũ:** `_is_profile_account_switcher_xml` trong `feed_swipe_smoke.py` yêu cầu bắt buộc: `has_title and has_add_account`. Do không thấy nút "Thêm tài khoản", hàm trả về `False`.
- **Chuẩn hóa:**
  ```python
  has_title = bool(values.intersection(_ACCOUNT_SWITCHER_TITLES))
  has_add_account = any(_is_add_account_option_text(value) for value in values)
  account_rows = {
      value.lstrip("@")
      for value in values
      if _is_account_like_switcher_text(value)
  }
  # Chỉ cần có tiêu đề switcher VÀ (có nút thêm tài khoản HOẶC có danh sách dòng tài khoản)
  if has_title and (has_add_account or account_rows):
      return True
  ```

### 2.2. Banner lỗi upload cũ (`tv_tips`) che khuất thanh Profile Header
- **Đặc điểm:** Ca upload trước bị fail khiến TikTok treo banner thông báo: *"Không thể tải video lên. Đã lưu bản nháp. Chạm để thử lại."* (resource-id `tv_tips`, kèm nút đóng `ImageView` `ea5` ở tọa độ `[960,138][1008,186]`).
- **Hậu quả:** Banner đè lên toàn bộ khu vực header đỉnh trang (`[24,102][1056,357]`), làm mất username và display name.
- **Chuẩn hóa:**
  * **Dismiss tự động:** Tìm nút đóng `ea5` (hoặc `ImageView` clickable ở góc trên bên phải) và tap đóng banner ngay khi vừa điều hướng vào Profile:
    ```python
    if not popup_handled and ("không thể tải video lên" in xml_text.lower() or "tv_tips" in xml_text):
        for el in iter_elements(parsed_root):
            if el.attrib.get("resource-id", "").endswith(":id/ea5") or (
                el.attrib.get("class", "").endswith("ImageView")
                and el.attrib.get("clickable") == "true"
                and el.bounds and 900 <= el.bounds[0] <= 1050 and 100 <= el.bounds[1] <= 250
            ):
                if el.center:
                    ctx.adb.shell(["input", "tap", str(el.center[0]), str(el.center[1])])
                    popup_handled = True
                    break
    ```
  * **Lọc bỏ tab "Bản nháp":** Tab bản nháp có chuỗi `"Bản nháp: 1"` (id `tv_draft`). Hàm `is_profile_placeholder` phải chặn các chuỗi bắt đầu bằng `"bản nháp"` hoặc `"draft"` để không nhận nhầm làm tên hiển thị của tài khoản.
  * **Hồi vị đỉnh Profile:** Khi không thấy username do màn hình lỡ bị cuộn xuống lưới video, re-tap tab "Hồ sơ" để kéo màn hình về lại đỉnh trang.

### 2.3. Bẫy Tọa Độ Tap Switcher Hàng Rộng (Samsung Wide Row Tap Dead-Space Pitfall)
- **Đặc điểm:** Khi Switcher mở ra, mỗi dòng tài khoản là một `Button` (`ls_`) hoặc container kéo dài toàn bộ chiều ngang màn hình `[0, y1][1080, y2]`.
- **Bẫy code cũ:** Code tính tâm của Button theo chiều rộng toàn màn hình: `center = [540, (y1 + y2) // 2]`.
- **Hậu quả:** Tọa độ `x=540` rơi vào khoảng trống chết (whitespace) giữa tên tài khoản (kết thúc ở x=521) và mép phải màn hình. Trên thiết bị Samsung (như Galaxy S7), tap vào khoảng trống x=540 bị framework UI nuốt hoặc không chạm vào child view có listener, dẫn đến việc sự kiện chọn tài khoản không được kích hoạt. Runner tưởng đã tap chọn nhưng sau đó profile vẫn giữ nguyên tài khoản cũ, gây lỗi `profile username still mismatched after switch`.
- **Chuẩn hóa:**
  * Giới hạn chiều rộng (`clamp`) của các hàng tài khoản rộng >= 600px về dải `0..700px`. Tọa độ tâm tap dịch từ `x=540` về `x=350`, rơi chính xác vào trọng tâm cụm chữ tên tài khoản:
    ```python
    if node.bounds is not None and (node.bounds[2] - node.bounds[0]) >= 600:
        y1, y2 = node.bounds[1], node.bounds[3]
        best_bounds = (node.bounds[0], y1, min(node.bounds[0] + 700, node.bounds[2]), y2)
    ```
  * Kết quả: bounds `(0, y1, 700, y2)` tạo `center = (350, y_mid)`, chạm thẳng vào vùng text và avatar của tài khoản, kích hoạt chuyển nick 100% ăn.

