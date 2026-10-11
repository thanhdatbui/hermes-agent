# Tái Cơ Cấu Tài Khoản Khi Máy Bị Reg Dư & Quy Tắc Bảo Toàn Tài Sản Farm

## 1. Bản chất sự cố máy đụng trần 8 nick do Reg dư
- Khi mở rộng ca nuôi hoặc reg bù cho các slot trống trong quá khứ, runner có thể đăng nhập tài khoản mới vào thiết bị nhưng không đồng bộ danh sách nick cũ có sẵn trên máy.
- Hậu quả: Máy thật lưu đủ 8 nick trên app TikTok, nhưng trên bảng tính (Excel/DB) một nick cũ (ví dụ `@samnga2403`) bị xóa sổ sách để nhét nick mới vào.
- **CẤM ĐOÁN TỐI CAO:** Tuyệt đối KHÔNG ĐƯỢC gọi nick cũ đang lưu phiên trên máy là "ký sinh" và cấm đòi logout vứt nick đi. Mọi nick đang sống và có email/pass hợp lệ đều là TÀI SẢN FARM quý giá.

---

## 2. Quy trình 5 bước tái cơ cấu 8 slot chuẩn hóa
Khi phát hiện máy bị lệch nick (mapping drift) dẫn đến lỗi `ACCOUNT_MISSING`:
1. **Kiểm tra thực tế Dual-Surface:**
   - Audit cả màn hình Hồ sơ chính (Active Profile) và Bottom Sheet (`Chuyển đổi tài khoản`).
   - Lập danh sách đầy đủ toàn bộ nick thực tế đang có mặt trên máy.
2. **Khôi phục nick gốc đúng vị trí cũ:**
   - Nick chính chủ của slot đầu (ví dụ `@muyduyen4589` ở Tik 1) BẮT BUỘC giữ nguyên vị trí.
   - Nick cũ có sẵn trên máy (ví dụ `@samnga2403`) được đưa về đúng vị trí cũ của nó trong bảng tính (ví dụ Tik 3).
3. **Lùi các nick phía sau lại 1 vị trí (Shift-Back Policy):**
   - Các nick từ vị trí khôi phục trở đi được tịnh tiến lùi lại 1 slot (Tik 3 -> Tik 4, Tik 4 -> Tik 5, ...).
4. **Điều chuyển nick non nhất sang máy thiếu slot:**
   - Nick non nhất (mới reg gần đây nhất, ít video nhất, ví dụ `@hohaian929` ở Tik 8) bị dôi ra ở cuối $\rightarrow$ chọn 1 máy khác trong farm đang thiếu slot (ví dụ máy Admin mới có 5 nick) để tiếp nhận.
   - **Bắt buộc bảo mật trước khi di dời:** Bật 2FA TOTP và tạo Password TikTok đầy đủ cho nick non trước khi di chuyển.
   - Ghi nhận thông tin vào Excel/DB của máy đích trước, nhưng **CHƯA ĐƯỢC LOGIN** lên máy đích cho đến khi có lệnh rõ ràng của User.
5. **Giải phóng slot & Login nick chính chủ:**
   - Đăng xuất nick non nhất khỏi máy hiện tại để giải phóng slot (từ 8 nick về 7 nick).
   - Đăng nhập nick chính chủ còn thiếu (ví dụ `@muyduyen4589`) vào máy qua pass + 2FA TOTP để hoàn tất đủ 8 nick.
