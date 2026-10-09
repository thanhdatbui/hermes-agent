# Case 81: CapCut Template Preview / Hub Dismissal & Camera Upload Hot Area Recovery

## 1. Triệu chứng & Hiện trường
- Khi bấm nút Tạo (+) hoặc trong lúc chuyển cảnh giữa Feed và Camera, TikTok hiển thị màn hình Template Preview ("Thử mẫu này", "Use this template", "Bởi CapCut") hoặc Template / Creation Hub ("Video mới", "Mẫu", "AutoCut", "Trình chỉnh sửa ảnh", "Phụ đề").
- UI XML không hiển thị các node upload tiêu chuẩn, khiến flow chờ timeout hoặc gửi lệnh tap sai vùng.
- Trên một số thiết bị Samsung (như Máy 1, Máy 38), nút thumbnail mở Gallery picker trong Camera nằm tại `upload_hot_area` góc dưới bên trái (`bounds=[0,1692][204,1896]` hoặc center `(120, 1821)`), không lộ text "Tải lên" / "Upload".

## 2. Quy tắc xử lý chuẩn (Case Fix)
1. **Phát hiện màn hình Template / Hub (`_is_capcut_template_surface`):**
   - Kiểm tra các markers: "thử mẫu này", "use this template", "bởi capcut", "autocut", "trình chỉnh sửa ảnh", "phụ đề", hoặc resource-id chứa `use_template`, `:id/bq3`, `:id/h32`.
   - Loại trừ trường hợp media picker thật (`viewpager_choose_media`, `j6k`, v.v.).
2. **Dismiss tự động (`_dismiss_capcut_template_surface`):**
   - Ưu tiên tìm và tap nút Back / Close ở góc trên bên trái (`top <= 400`, content-desc/text "quay lại", "đóng", "back", "close", "<", hoặc resource-id kết thúc bằng `/bq3`, `/h32`, `/back`, `/btn_close`).
   - Nếu không tìm thấy node nút bấm, fallback gửi `adapter.back()` và xác thực lại XML.
3. **Mở Gallery Picker từ Camera Surface (`upload_hot_area`):**
   - Nếu XML chứa `upload_hot_area` hoặc các thumbnail tương tự, tap tọa độ `(120, 1821)` và kiểm tra `_is_verified_media_picker_xml`.
   - Giảm timeout chờ picker từ 60s xuống 5s để tránh treo luồng khi UI đã chuyển cảnh.
4. **Media Fingerprint Ledger Rebind:**
   - Khi chạy retry hợp lệ trên cùng máy, cùng target account và video number, tự động rebind reservation SHA-256 từ run ID cũ sang run ID mới thay vì raise `MEDIA_FINGERPRINT_PENDING`.
