# TikTok Parasite Account Reconcile & UI Automation Pitfalls

## 1. Bối Cảnh Lỗi Ký Sinh & Chạm Trần 8 Accounts
- Khi một máy farm (ví dụ M53) bị đăng nhập tài khoản thuộc về máy khác (ví dụ `@chichi13853` thuộc M26), số lượng tài khoản trên app TikTok chạm ngưỡng trần tối đa (8/8).
- Nút "Thêm tài khoản" bị ẩn hoàn toàn, khiến các tiến trình đăng ký bù (reg bù / preflight) bị chặn lại bởi chốt chặn bảo vệ tài sản `MACHINE_FULL_8_ACCOUNTS`.
- Tuyệt đối CẤM đăng xuất bừa bãi tài khoản đang hoạt động của máy. Bắt buộc đối soát danh sách tài khoản thực tế trên app với Workbook tracking (`taikhoan_dat_v2_updated .xlsx`) để xác định chính xác UID ký sinh ngoại lai.

## 2. Quy Trình Đăng Xuất An Toàn (Clean Logout Pipeline)
1. **Khởi động app và mở Switcher:**
   - Đánh thức máy: `input keyevent 224 && input keyevent 82`
   - Khởi động TikTok: `monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1`
   - Vào Profile (tap `972 1857`) -> Vuốt và mở Switcher: swipe `540 1100 540 600 250` rồi tap dropdown `500 140`.
2. **Switch sang đúng tài khoản ký sinh:**
   - Tap vào dòng chứa UID ký sinh trên danh sách popup (hoặc theo tọa độ định vị chính xác).
   - Đợi chuyển tài khoản hoàn tất (sleep 5-6s).
3. **Thực hiện Logout trong Cài đặt:**
   - Vào Profile (tap `972 1857`) -> Menu 3 gạch (tap `1005 150`).
   - Mở Cài đặt và quyền riêng tư -> Vuốt xuống đáy trang (5-6 lần swipe `540 1600 540 300 250`).
   - Tap nút "Đăng xuất" ở đáy -> Tap xác nhận Đăng xuất màu đỏ trên popup.
4. **Nghiệm thu trực quan (Gate 6 - Visual Evidence):**
   - Mở lại Profile và Switcher tài khoản.
   - Chụp screencap màn hình Switcher: `screencap -p > <path_anh>`.
   - Xác minh: UID ký sinh đã biến mất, tổng số nick còn <= 7 và nút "Thêm tài khoản" đã xuất hiện trở lại.
   - Báo cáo đính kèm `MEDIA:<path_anh>`.
5. **Teardown:**
   - `am force-stop com.ss.android.ugc.trill` và `input keyevent 3` (HOME).

## 3. Pitfall: Đánh Giá Boolean của XML Element trong Python
- Trong thư viện chuẩn `xml.etree.ElementTree`, một `Element` không có con cháu (`len(elem) == 0`) sẽ đánh giá `bool(elem) == False`.
- Khi duyệt tìm node tài khoản trên UI dump XML:
  ```python
  # SAI: Sẽ kích hoạt nhánh lỗi dù node đã tìm thấy (vì node lá rỗng con)
  target_node = find_account_node(xml_root, username)
  if not target_node:
      raise Exception("Node not found")

  # ĐÚNG: Luôn kiểm tra định danh rõ ràng
  if target_node is None:
      raise Exception("Node not found")
  ```
- Với các thao tác điều khiển thiết bị nhanh và tránh phụ thuộc XML dump bridge bị timeout, ưu tiên áp dụng sequence ADB trực tiếp với tọa độ đã định vị ổn định.
