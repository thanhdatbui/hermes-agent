# Triage Tài Khoản Tồn Đọng Quá Trần 8 Nick & Kỷ Luật Bảo Toàn Tài Sản Farm

**Ngày ghi nhận:** 11/10/2026  
**Ngữ cảnh:** Máy farm (ví dụ M74) gặp lỗi `[ACCOUNT_SWITCHER_FAILED]` / `ACCOUNT_MISSING` do danh sách tài khoản thực tế trên thiết bị không khớp với sổ sách (`taikhoan_run_safe.xlsx` / `Tik1..Tik8.xlsx`).

---

## 1. Căn Nguyên: Lệch Ánh Xạ Do Reg Dư & Đụng Trần 8 Nick TikTok

1. **Trần cứng 8 Nick của TikTok trên Android:**
   - Ứng dụng TikTok trên một thiết bị chỉ cho phép lưu tối đa **8 tài khoản** trong switcher cùng lúc.
2. **Nguyên nhân dồn thành > 8 tài khoản:**
   - Khi farm mở rộng từ 3 ca lên 4 ca (8 slot/máy) hoặc thay thế tài khoản, hệ thống chạy chuỗi **Reg bù**.
   - Nếu script reg chỉ thực hiện *"Thêm tài khoản khác"* để nạp nick mới mà **không đối soát danh sách thực tế trên máy**, máy sẽ bị reg dư nick.
   - Các tài khoản cũ (đã từng gán trên máy) vẫn còn phiên đăng nhập trong app, chiếm slot khiến các tài khoản mới theo sổ sách không vào được hoặc bị đẩy rớt ra ngoài.
3. **CẤM TƯ DUY "KÍ SINH / PHÁ HOẠI TÀI SẢN":**
   - **Mọi tài khoản đang login sống trên máy đều là tài sản thật của Farm** (có Gmail, UID, dữ liệu nuôi).
   - **TUYỆT ĐỐI CẤM** tự tiện gọi tài khoản cũ là "kí sinh" rồi vội vã logout, xóa bỏ hay đánh dấu DIE.

---

## 2. Quy Tắc Điều Phối & Bảo Toàn Tài Sản

Khi phát hiện máy bị lệch nick giữa sổ sách và thiết bị:

1. **Khớp nối ưu tiên nick có sẵn trên máy:**
   - Nếu nick cũ vẫn đang sống khỏe trên app: **Ưu tiên map lại nick đó vào đúng slot của máy trên Excel (`taikhoan_run_safe.xlsx`, `TikN.xlsx`) và database (`account_mapping`)**.
   - Việc này giúp máy tiếp tục chạy nuôi feed và upload ngay lập tức, không gây gián đoạn phiên và không cần thao tác logout/login rủi ro trên thiết bị.
2. **Tái phân bổ nick dư sang máy còn trống (Ví dụ Farm Admin):**
   - Thay vì xóa bỏ tài khoản thừa, kiểm tra các máy còn trống slot (như cụm Admin các máy mới có 5 nick, còn trống slot 6, 7, 8).
   - Chọn tài khoản **non nhất** trên máy đầy để luân chuyển sang máy thiếu slot.
3. **Kỷ luật bảo mật trước khi luân chuyển nick:**
   - Trước khi đẩy nick sang máy mới: **BẮT BUỘC cài đặt mật khẩu TikTok và kích hoạt 2FA TOTP đầy đủ**, lưu Secret vào Master DAT.
   - Cập nhật thông tin vào Excel của máy nhận trước (`MISSING_ID` -> `OK`), **chỉ thực hiện login thiết bị khi có lệnh chỉ đạo cụ thể của User**.
