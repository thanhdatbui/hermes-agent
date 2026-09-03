# TikTok 46.x Account Switcher: Body Username Exclusion & Fuzzy Header Anchor Resolution (Case 71, 02/09/2026)

## 1. Triệu chứng & Bối cảnh (Sự cố Máy 60)
- Màn hình Profile của tài khoản (ví dụ `crystal.1.1`) trên TikTok 46.x khi chưa cuộn trang:
  - Display name nằm ở `com.ss.android.ugc.trill:id/su7` (`text='crystal.1.11'`).
  - Body username nằm ở `com.ss.android.ugc.trill:id/sr3` (`text='@crystal.1.15'`) tại tọa độ `bounds=[36,370][273,415]`.
  - Vùng đỉnh màn hình chưa render sticky header anchor.
- Lỗi: Khi script không tìm thấy sticky header trên cùng, hàm fallback anchor vô tình trả về `username_element` (`id/sr3` `@crystal.1.15` tại `y=392`). Tapping vào body username chỉ copy handle vào clipboard, không kích hoạt mở bottom sheet *Chuyển đổi tài khoản*, dẫn đến fail-closed:
  `manual-needed:account-switcher-not-open: profile switch anchor could not be resolved safely`.

## 2. Nguyên nhân Gốc (Root Cause)
1. **Fallback Tapping Body Username Sai Mục Đích:** Nút `@username` ở thân trang Profile (y > 260px, x < 300px) là nút copy ID link của TikTok, không phải anchor mở Account Switcher.
2. **Nhiễu Ký Tự Số/Badge Nối Đuôi do UIAutomator:** Text dump của `su7` và `sr3` bị ghép thêm ký tự số (`crystal.1.11` / `@crystal.1.15`). Khi cuộn trang xuất hiện sticky header `:id/pke` (`crystal.1.1`), phép so sánh chuỗi chính xác `node_value in identity_values` bị sai lệch (`'crystal.1.1' not in {'crystal.1.11', 'crystal.1.15'}`).

## 3. Quy chuẩn Xử lý
1. **Giới hạn tọa độ Fallback Anchor:**
   - Trong `_profile_switch_fallback_anchor(identity)`: Tuyệt đối không trả về `username_element` khi nó nằm ở vùng thân Profile (`center[1] > 260` hoặc `bounds[0] < 300`). Chỉ chấp nhận khi username thực sự là sticky header ở đỉnh giữa (`center[1] <= 250` và `300 <= center[0] <= 780`).
2. **So khớp Danh tính dạng Prefix / Fuzzy:**
   - Trong `_find_sticky_profile_header` và `find_switcher_anchor`: So khớp `node_value` và `identity_values` cho phép prefix match hoặc strip ký tự số/badge nối đuôi để nhận diện chính xác `:id/pke` / `:id/pkh`.
3. **Tự động Cuộn Re-derive Identity:**
   - Khi Profile root ban đầu chưa có sticky header, thực hiện vuốt nhẹ (`_profile_scroll`), re-capture XML và phân giải sticky header anchor `:id/pke`.
