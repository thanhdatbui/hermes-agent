# Bẫy Tọa Độ Center Row Đáy Trong Bottom Sheet Switcher & Safe-Point Upper-Third Tap (2026-09-25)

## 1. Hiện Tượng & Nguy Cơ
- Khi Account Switcher chứa 7 tài khoản, nút **"Thêm tài khoản"** (hoặc tài khoản thứ 8 ở cuối danh sách) bị dồn xuống sát mép dưới cùng của màn hình thiết bị Samsung S7 (bounds: `[0, 1788][1080, 1920]`, chiều cao row là 132px).
- Hàm tìm và tap thông thường (`find_text_tap` hoặc `tap(cx, cy)`) sẽ lấy tâm của bounding box:
  $$\text{center\_y} = \frac{1788 + 1920}{2} = 1854$$
- Trên các thiết bị Samsung S7 (độ phân giải 1080x1920), vùng $y \ge 1840$ là vùng biên sát thanh điều hướng ảo/cạnh dưới, khiến touch event của Android dễ bị nuốt, rơi vào vùng không phản hồi, hoặc trigger trúng thanh điều hướng thay vì button trong TikTok.
- Kết quả: Script gọi `tap_add_account` nhưng TikTok không phản hồi, dẫn đến việc script bị treo chờ `wait_for_text` / timeout 300s.

## 2. Giải Pháp Chuẩn: Safe-Point Upper-Third Tap
Thay vì chạm vào tâm dọc ($50\%$ chiều cao), đối với các hàng nằm ở đáy danh sách hoặc khi tap các nút trong bottom sheet, bắt buộc tính tọa độ an toàn ở **$1/3$ phần trên của bounding box**:

$$\text{safe\_y} = y_1 + \max\left(1, \frac{y_2 - y_1}{3}\right)$$

### Ví dụ tính toán cụ thể:
- Với bounds `[0, 1788][1080, 1920]`:
  $$\text{safe\_y} = 1788 + \frac{1920 - 1788}{3} = 1788 + 44 = 1832$$
- Tọa độ chạm mới: `(540, 1832)`.
- Kết quả: $1832 < 1840$ $\rightarrow$ Nằm hoàn toàn trong vùng nhận diện an toàn của TikTok, kích hoạt ngay lập tức form đăng nhập mà không bị ảnh hưởng bởi thanh điều hướng.

## 3. Quy Tắc Triển Khai Trong Mã Nguồn (`social_reg_v1.py`)
```python
add_node = find_node_in_xml(
    get_ui_xml(device_id),
    "Thêm tài khoản", "Add account", "Thêm tài khoản khác",
    "Add another account", "add_account",
    prefer_clickable=True,
    package=APP_PACKAGE,
)
if add_node:
    row_bounds = add_node.get("bounds", "")
    bounds_match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", row_bounds)
    if bounds_match:
        x1, y1, x2, y2 = (int(value) for value in bounds_match.groups())
        safe_x = (x1 + x2) // 2
        safe_y = y1 + max(1, (y2 - y1) // 3)
        log(f"   ✓ tap Add account safe row point ({safe_x}, {safe_y}) bounds={row_bounds}")
        tap(device_id, safe_x, safe_y, wait=D_MEDIUM)
        return
```

## 4. Kiểm Thử Hồi Quy
- Đã thêm test case trong `tests/test_tap_add_account_safe_point.py`.
- Xác nhận:
  1. Node bounds `[0, 1788][1080, 1920]` không bao giờ tap `1854`.
  2. Bắt buộc tap chính xác `(540, 1832)`.
