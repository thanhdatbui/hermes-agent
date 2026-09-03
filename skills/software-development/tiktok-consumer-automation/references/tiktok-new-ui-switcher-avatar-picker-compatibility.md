# TikTok New UI Switcher & Avatar Picker Compatibility (2026-09-03)

## 1. Account Switcher Anchor trên TikTok UI Mới

### Hiện tượng & Root Cause
- Trên giao diện TikTok mới (46.x+), Profile header đặt ảnh đại diện ở trên cùng (`bounds [366,162][714,510]`), bên dưới là Display Name (`id: sv6`, `bounds [372,519][707,585]`, center `(540, 552)`), và dưới cùng là Username (`id: sxa`, `bounds [382,594][698,639]`, center `(540, 616)`).
- `sxa` (`@username`) là text tĩnh (chỉ dùng để copy username vào clipboard khi bấm), **KHÔNG** mở được sheet Switcher.
- Điểm mở switcher thật sự là Display Name `sv6` hoặc tọa độ `(540, 552)`.
- Các prompt/badge overlay như `pxu` ("Tám chuyện nào", "Bạn đang nghĩ gì...", "Thì thầm to nhỏ") nếu bị tap trúng sẽ mở modal Tạo Nhật ký / Story thay vì Switcher.

### Giải pháp kỹ thuật trong `adapter.py`
1. **`sanitize_switcher_profile_xml`:**
   - Xóa `text` và `content-desc` của các node có `resource-id` kết thúc bằng `sxa` và `pxu` trước khi chuyển XML cho `open_switcher` của `automation-core`.
   - Việc này ngăn `find_switcher_anchor` chọn nhầm `@username` tĩnh và để core fallback về Display Name hoặc `coordinate_fallback("switcher")` trả về `(540, 552)`.
2. **`prepare_switcher_anchor`:**
   - Bổ sung `sv6`, `s7w` vào danh sách `resource_id` kiểm tra trực tiếp.
   - Tăng `header_limit` từ `320px` lên `650px` (`max(650, int(screen_height * 0.35))`) để không bỏ sót Display Name ở tọa độ y ~ 550px.

---

## 2. Avatar Picker & In-Memory XML Lookup trong `state_machine.py`

### Pitfall nghiêm trọng: `_find_adapter_element` gọi `_wait_for_element`
- Khi kiểm tra danh sách nhiều resource ID (`o_9`, `xip`, `wrj`, `rts`, `qii`, `rou`, `sca`), hàm trợ giúp `_find_adapter_element` **TUYỆT ĐỐI KHÔNG** được fallback sang `adapter._wait_for_element(**kwargs)`.
- `_wait_for_element` có timeout mặc định lên đến 60s cho mỗi selector không tồn tại. Lặp qua 7 selectors trong vòng lặp while sẽ khiến tiến trình bị treo hơn 7 phút cho 1 vòng lặp!
- **Chuẩn:** `_find_adapter_element` CHỈ đọc trực tiếp XML string đã dump qua `adapter._find_ui_element(xml_text, **kwargs)`.

### Selector & Tọa độ nút Tiếp / Lưu Crop
- Selector nút Tiếp (Picker): `o_9`, `xip`, `wrj`, `rts`, `qii`, `rou`, `sca` hoặc text `Tiếp (1)`, `Tiếp`, `Next (1)`, `Next`.
- Tọa độ fallback nút Tiếp: `(924, 1842)`.
- Tọa độ fallback Lưu Crop avatar: `(792, 1794)`.

---

## 3. Popup "Save Login" sau khi chuyển Account tại `ACCOUNT_READY`

### Hiện tượng
- Sau khi chọn account trong sheet Switcher, TikTok load profile mới và đồng thời hiển thị popup "Lưu thông tin đăng nhập" (`save_login`).
- Nếu verify account ngay lập tức, `verify_selected_account` sẽ fail vì username chưa hiển thị kịp hoặc bị popup che.

### Giải pháp
- Trong `_handle_account_ready`: Polling tối đa 20s, tự động gọi `_dismiss_simple_close_popup` và dismiss benign popup `save_login`.
- Nếu verify lần đầu chưa khớp, re-tap Profile tab (`(972, 1840)`) và retry thay vì ngay lập tức báo lỗi `ACCOUNT_SWITCHER_FAILED`.
