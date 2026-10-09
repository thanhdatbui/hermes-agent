# TikTok Account Switcher: Sticky Header Flow & S7 Hardware Safety

## 1. Thiết Kế Chuẩn Của User: Profile Sticky Header Account Switcher
Khi ở trang cá nhân (Profile tab) để mở Account Switcher và thêm tài khoản:
1. **Cuộn Profile để ID ghim lên Sticky Header**:
   - Thực hiện cuộn nhẹ màn hình từ giữa xuống (`swipe 540 1000 540 700 250ms`, biên độ ~300px).
   - Cuộn đưa tên tài khoản / ID hiển thị trượt lên và ghim cố định thành thanh Sticky Header trên cùng chính giữa màn hình (thay vì nút tên tĩnh ở thân profile).
   - Sticky header có resource ID `pmi` / `pmf` / `pq2`, tọa độ bounds điển hình: `[366, 72][732, 228]`, tâm: `(549, 150)`.
2. **Tap vào Sticky ID trên cùng chính giữa**:
   - Tap chính xác vào tâm thanh ghim `(549, 150)` (hoặc `sw // 2, 150`).
   - TikTok sẽ kích hoạt bung bottom-sheet "Chuyển đổi tài khoản" (Account Switcher) chứa danh sách tài khoản đã đăng nhập + nút "Thêm tài khoản" ở cuối.
3. **Tap "Thêm tài khoản"**:
   - Từ bottom-sheet Switcher, tap vào dòng "Thêm tài khoản" / "Add account" (`bounds=[0, 1680][1080, 1896]`, safe-point `(540, 1752)`).

---

## 2. Pitfall & Vùng Cấm Thao Tác (Samsung S7 & TikTok UI)

### ⚠️ Pitfall 1: Xung Đột Cử Chỉ Samsung Pay / Quick Pay Mép Đáy
- Trên dòng máy Samsung Galaxy S7 (và OneUI cũ), mép đáy màn hình `[300, 1893][780, 1920]` có thanh vuốt nhanh của **Samsung Pay / Quick Pay**.
- **CẤM TUYỆT ĐỐI** bắt đầu lệnh swipe từ `y >= 1600` (ví dụ `swipe 540 1650 540 350`). Cử chỉ này chạm vào thanh vuốt Samsung Pay làm TikTok bị minimize và văng ra màn hình Launcher chính Android.
- **Quy tắc an toàn**: Mọi thao tác cuộn (Settings, Profile, Bottom-sheet) bắt buộc giới hạn trong dải an toàn:
  `y_start <= 1350`, `y_end >= 450`.

### ⚠️ Pitfall 2: Máy Mới Có 1 Tài Khoản (1-Account Edge Case) & Giải Pháp Đăng Xuất
- Trên các build TikTok v46.x: Khi thiết bị chỉ mới đăng nhập đúng 1 tài khoản (ví dụ máy mới reg xong acc đầu như Máy 266), thanh Sticky Header là text tĩnh KHÔNG có chevron ▼ và Settings không có mục "Chuyển đổi tài khoản" (chỉ có mục "Đăng xuất").
- Với máy 2+ tài khoản: Sticky header luôn bung switcher 100% (đã nghiệm thu trên máy 249).
- **Quy trình nạp nick thứ 2 cho máy 1 nick**:
  1. Vào Settings ("Cài đặt và quyền riêng tư") -> cuộn an toàn xuống đáy trang.
  2. Tap "Đăng xuất" -> xác nhận modal "Đăng xuất" (TikTok tự lưu session nick cũ vào One-Tap login).
  3. Màn hình Profile trở về trạng thái Đăng ký (nút đỏ "Đăng ký" / "Tiếp tục với Email/Google").
  4. Tiến hành đăng ký nick thứ 2. Sau khi nick thứ 2 hoàn tất, TikTok sẽ tự kích hoạt icon chevron ▼ trên sticky header và switcher.

### ⚠️ Pitfall 2b: Giải Mã Chỉ Đạo Của User ("Vuốt xuống cho ID nằm trên cùng chính giữa")
- Khi user chỉ đạo "vuốt xuống ở profile cho ID nằm trên cùng chính giữa", đây là góc nhìn thị giác: user muốn nội dung profile cuộn lên để ID ghim vào thanh sticky header đỉnh màn hình (`y=150`).
- Lệnh ADB kỹ thuật BẮT BUỘC là vuốt kéo nội dung lên (`swipe 540 1000 540 700 250ms`). TUYỆT ĐỐI CẤM kéo ngón tay từ trên xuống (`540 500 -> 540 1500`), vì thao tác đó sẽ kích hoạt pull-to-refresh của feed profile làm văng vị trí ghim!

### ⚠️ Pitfall 3: Cấm Gửi Ảnh Màn Hình Home/Launcher Làm Bằng Chứng
- User duyệt hiện trường bằng mắt qua ảnh (`MEDIA:`). Gửi ảnh màn hình Home/Launcher khi bot lỗi là vi phạm nghiêm trọng (User: *"Gửi tao màn home của máy chi v"*).
- Phải luôn chụp đúng màn hình Profile / Dialog / Error / Switcher thực tế của app trước khi teardown hoặc force-stop.

---

## 3. Hardware Triage: Phân Biệt Lỗi Script vs Lỗi Cáp Vật Lý (CM_PROB_PHANTOM)
Khi ADB báo `device '<serial>' not found` hoặc `offline`:
1. Kiểm tra ngay trên host qua PowerShell:
   ```powershell
   Get-PnpDevice | Where-Object { $_.InstanceId -like "*<serial>*" } | Select-Object FriendlyName, Status, Present, Problem
   ```
2. Nếu `Present: False` hoặc `Problem: CM_PROB_PHANTOM`:
   - Thiết bị đã bị rớt kết nối vật lý (cáp USB lỏng, sập nguồn, tuột hub).
   - **Hành động**: DỪNG NGAY mọi retry script, KHÔNG sửa code, báo cáo rõ cho chủ farm kiểm tra cáp/nguồn tại rack.
