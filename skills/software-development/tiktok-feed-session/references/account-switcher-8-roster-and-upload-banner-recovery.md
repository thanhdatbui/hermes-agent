# Kỹ Thuật Xử Lý Account Switcher 8 Nick & Banner Bản Nháp Trên TikTok Farm

## 1. Hiện Tượng Switcher Đầy 8 Tài Khoản Mất Nút "Thêm tài khoản"
- **Bối cảnh:** Dàn farm chuẩn 8 nick/máy. Khi mở Switcher ("Chuyển đổi tài khoản"), danh sách 8 tài khoản chiếm trọn chiều cao màn hình (từ `y=1140` đến đáy).
- **Cạm bẫy nhận diện:** Hàm `_is_profile_account_switcher_xml` cũ bắt buộc đồng thời:
  1. `has_title`: Có chữ "Chuyển đổi tài khoản" hoặc "Switch account".
  2. `has_add_account`: Có nút "Thêm tài khoản" hoặc "Add account".
- **Hậu quả:** Nút "Thêm tài khoản" bị trượt xuống dưới màn hình (off-screen/below the fold). Script không tìm thấy `has_add_account`, ngộ nhận Switcher là màn hình lạ, dừng phiên và văng alert:
  `[ALERT] [MÁY N] Dừng: manual-needed | Lý do: account switcher requires manual review`.
- **Giải pháp chuẩn:** Khi đã có `has_title` và phát hiện có danh sách các dòng tài khoản (`bool(account_rows)`), công nhận ngay đây là Switcher hợp lệ mà không đòi hỏi nút "Thêm tài khoản" phải hiển thị trong viewport.

---

## 2. Bẫy Chạm Khoảng Trắng Trên Dòng Tài Khoản Samsung (Blank Tap Trap)
- **Bối cảnh:** Trên giao diện Samsung S7, mỗi dòng tài khoản trong Switcher là một container `Button` trải dài toàn bộ chiều rộng màn hình: `[0, y1][1080, y2]`.
- **Cạm bẫy tọa độ:**
  - Tên username (ví dụ: `huehoafi23`) chỉ kéo dài từ `x=252` đến `x=521`.
  - Nếu tính tọa độ tâm hàng `center = ((0 + 1080) // 2, y_mid) = (540, y_mid)`, điểm chạm rơi vào khoảng trống bên phải chữ.
  - Widget trên TikTok/Samsung không kích hoạt sự kiện click khi chạm vào khoảng trắng này. Switcher tự đóng hoặc không phản hồi, tài khoản active trên Profile vẫn giữ nguyên nick cũ, dẫn đến lỗi:
    `profile username still mismatched after switch`.
- **Giải pháp chuẩn:** Giới hạn chiều rộng (`clamp`) của bounding box tài khoản rộng >= 600px về dải `0..700px`. Tọa độ tâm tap dịch từ `x=540` về `x=350`, rơi chính xác vào trọng tâm cụm chữ tên tài khoản:
  ```python
  if r_right - r_left >= 600:
      best_bounds = (r_left, r_top, min(r_right, 700), r_bottom)
  ```

---

## 3. Banner Lỗi Tải Video / Bản Nháp Che Khuất Header Profile
- **Bối cảnh:** Khi ca upload video trước đó bị lỗi hoặc hủy giữa chừng, TikTok hiển thị banner cảnh báo đỏ trên đỉnh tab Hồ sơ:
  `"Không thể tải video lên. Đã lưu bản nháp. Chạm để thử lại"` (resource-id `tv_tips`, nút đóng `ea5` ở góc phải `[960,138][1008,186]`).
- **Tác động tiêu cực:**
  1. Banner chiếm toàn bộ header (`y=102..357`), che mất thanh hiển thị username / display-name anchor.
  2. Tab nháp `"Bản nháp: 1"` bị bộ trích xuất text XML nhận diện nhầm thành display name người dùng.
- **Giải pháp chuẩn:**
  1. Thêm từ khóa `"bản nháp"`, `"draft"` vào danh sách loại trừ `is_profile_placeholder` để không nhận nhầm thành tên nick.
  2. Khi phân tích Profile, kiểm tra sự hiện diện của banner upload/draft (`tv_tips` hoặc text "không thể tải video lên"). Tự động chạm nút đóng `ea5` để dọn dẹp trước khi đọc anchor tài khoản.

---

## 4. Xử Lý Màn Hình Lỗi Mạng / Thử Lại Tại Bước Khởi Động Baseline
- **Bối cảnh:** Tại bước `baseline` khi TikTok vừa mở lên, nếu proxy chập chờn hoặc mạng trễ, màn hình có thể hiện: *"Không có kết nối Internet. Hãy nhấn để thử lại."* kèm nút *"Thử lại"* (`dd9`).
- **Cạm bẫy:** Logic kiểm tra trong `_capture_step` chỉ kích hoạt bộ xử lý `benign_popup_registry` tự bấm nút "Thử lại" khi `require_feed == True`. Nhưng bước `baseline` lại truyền `require_feed = False`, dẫn đến việc không ai bấm "Thử lại", session dừng sớm dạng `manual-needed:network`.
- **Giải pháp chuẩn:** Mở rộng điều kiện xử lý nút thử lại mạng cho cả khi `(require_feed or step == "baseline")`.
