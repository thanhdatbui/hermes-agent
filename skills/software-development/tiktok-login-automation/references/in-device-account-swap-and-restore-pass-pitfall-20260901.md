# In-device Account Retention & Workbook Swap (2026-09-01)

## Bối cảnh
Khi một máy nuôi đang đăng nhập đủ 6 nick (ví dụ Máy 1 có: `tranngan767`, `lipsellczaw`, `duongkien1202`, `ginnyhanstei80`, `ahmetsguthe17`, `buithudung2011`), nhưng lịch chạy ca 3 (Tik5) theo Excel lại yêu cầu nick `janayerton71` (đang thiếu trên máy).

## Quy tắc xử lý: Workbook Re-mapping First
1. **Không logout/login vòng trên cùng máy**:
   - Việc đăng xuất 1 nick đang live để đăng nhập nick khác vào máy làm tăng nguy cơ checkpoint, văng session hoặc kích hoạt security challenge của TikTok.
   - Luôn ưu tiên tận dụng các nick đã đăng nhập và đang sống trên máy.

2. **Quy trình swap trên 3 file Excel**:
   - **File 1 (`taikhoan_dat_v2_updated .xlsx`)**:
     - Chuyển nick đang có trên máy (`buithudung2011`) vào đúng Slot ca nuôi còn thiếu (Slot 5). Dọn sạch các slot rác/slot thừa (Slot 7/8).
     - Chuyển nick đang thiếu (`janayerton71`) sang một máy khác còn trống slot ca 5 (ví dụ Máy 61).
   - **File 2 (`taikhoan_run_safe.xlsx`)**:
     - Cập nhật ID nick tương ứng cho máy hiện tại và máy nhận nick mới.
   - **File 3 (`TikN.xlsx`)**:
     - Cập nhật ID nick trong sheet `TaiKhoan`, đánh dấu `Kiểm Tra Dữ Liệu = OK`.

## Bẫy khôi phục tài khoản từ Hotmail / Gmail Clean (Restore Password Pitfall)
- Khi khôi phục tài khoản bị mất dòng từ file nguồn `gmail_clean_v2.xlsx`, **CẤM** lấy mật khẩu mail Hotmail/Gmail ghi đè vào cột `PASS` TikTok của `taikhoan_dat_v2_updated .xlsx`.
- Mật khẩu TikTok luôn được sinh ngẫu nhiên có chữ hoa, số và ký tự đặc biệt (`make_tiktok_password`), không bao giờ trùng với mật khẩu email nguồn (thường chỉ gồm chữ thường + số).
- Nếu không có mật khẩu TikTok thật, để trống hoặc sử dụng quy trình **Quên mật khẩu** nhận OTP qua OAuth2 Hotmail / Gmail để đặt lại mật khẩu mới.
