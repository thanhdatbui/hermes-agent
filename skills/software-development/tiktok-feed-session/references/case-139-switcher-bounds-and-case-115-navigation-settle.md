# Case 139 (Account Switcher Row Bounds) & Case 115 (Navigation Settle & Focus Recovery)

## 1. Case 139 (07/09/2026): Toạ Độ Container Switcher Full-Width & Cạm Bẫy Ghi Đè Sang Child Non-Clickable

### Triệu chứng & Hiện tượng
- Phiên chạy lướt feed dừng với lỗi: `profile username still mismatched after switch` khi chuyển từ tài khoản hiện tại sang tài khoản đích trên Máy 8 (`tolmavhj12k`).
- Script đã nhận diện được tài khoản trong bottom-sheet Switcher và thông báo `tap_expected_account`, nhưng sau 2 lần thử, profile vẫn giữ nguyên tài khoản cũ.

### Nguyên nhân gốc rễ
1. Trên TikTok 46.x (và Samsung S7), cấu trúc bottom-sheet Account Switcher:
   - Mỗi dòng tài khoản là một container `android.widget.Button` (`com.ss.android.ugc.trill:id/lkp`, `clickable="true"`, bounds `[0, 600][1080, 816]`, center $x=540, y=708$).
   - Bên trong chứa `TextView` hiển thị username (`com.ss.android.ugc.trill:id/n72`, `clickable="false"`, bounds `[252, 678][534, 738]`, center $x=393$).
2. Commit `60b3253` đã bỏ nhánh kiểm tra `clickable == true`, cố tình override toạ độ tap sang inner `TextView` ($x \approx 393$) do ngộ nhận $x=540$ là "dead whitespace bên phải".
3. **Thực tế:** Container Button full-width nhận touch event trên toàn bộ bề ngang. Khi ép tap vào child TextView có `clickable="false"`, Android nuốt sự kiện chạm hoặc không chuyển giao lên Button cha, khiến TikTok không thực hiện switch nick.

### Quy định khắc phục
- **Giữ nguyên bounds container clickable:** Khi node tìm được có `clickable == "true"`, BẮT BUỘC giữ nguyên bounds và tap vào giữa container ($x=540$). CẤM ép toạ độ sang inner TextView không nhận click.
- **Kỷ luật Ground Truth First:** Khi nghi ngờ toạ độ tap hay màn hình kẹt, BẮT BUỘC chụp ảnh màn hình (`screencap`) và dump XML hiện trường trước khi kết luận. Tuyệt đối không thay đổi toạ độ theo suy đoán chủ quan.

---

## 2. Case 115 (05/09/2026): Settle Retry & Phục Hồi 2 Tầng Khi Navigation Tap Dính 'Unknown' Package

### Triệu chứng & Hiện tượng
- Phiên chạy dừng với alert: `TikTok focus lost after navigation tap: unknown` (Máy 6 - Nick `alemafxjvxw`).
- Hiện trường thực tế TikTok vẫn đang mở và đang chuyển cảnh hoặc vừa kết thúc animation.

### Nguyên nhân gốc rễ
1. Sau cú tap điều hướng (`tap_navigation_target`), WindowManager trên các máy cấu hình thấp (Samsung S7) đang trong quá trình chuyển cảnh (transition animation).
2. Lệnh `get_focused_activity` query ngay lập tức có thể trả về `package: None` hoặc chuỗi rỗng (`unknown`).
3. Khối code kiểm tra focus cũ bỏ sót trường hợp `not post_package`, xem package rỗng là lỗi nghiêm trọng và lập tức dừng máy thay vì chờ settle hoặc kích hoạt phục hồi.

### Quy định khắc phục
1. **Settle Retry:** Khi `not post_package`, chờ 1.0s và query lại `get_focused_activity` một lần nữa để đợi animation hoàn tất.
2. **Phục hồi 2 tầng (Two-Tier Focus Recovery):**
   - Tầng 1: Thử gửi `input keyevent 4` (KEYCODE_BACK) để thoát khỏi popup hoặc dialog tạm thời làm che khuất TikTok.
   - Tầng 2: Nếu vẫn chưa lấy lại focus TikTok, sử dụng lệnh `monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1` để kéo TikTok về lại foreground an toàn.
