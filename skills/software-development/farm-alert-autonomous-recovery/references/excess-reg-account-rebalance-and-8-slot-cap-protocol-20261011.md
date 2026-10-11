# Xử Lý Máy Đụng Trần 8 Acc Do Reg Dư: Quy Tắc Tái Bố Trí, Add 2FA & Đẩy Nick Non Sang Máy Thiếu Slot (11/10/2026)

## 1. Bản chất sự cố dồn 9 nick & Chống bẫy ngộ nhận "Ký sinh"
- **Nguyên nhân dồn thành 9 nick**:
  * Khi mở rộng nuôi hoặc reg bù, script thấy slot trống trên file Excel nên reg thêm tài khoản mới.
  * Tuy nhiên trên thiết bị thật, các nick cũ đã từng login trước đó vẫn còn lưu phiên trong app TikTok (chưa từng được logout).
  * Hậu quả: Máy thật có sẵn 8 nick, script reg thêm nick mới làm máy bị dồn thành 9 nick tranh 8 slot.
- **Kỷ luật định danh tài sản farm**:
  * **CẤM TUYỆT ĐỐI gọi nick cũ của máy là "ký sinh"**: Mọi nick đang login sống trên máy đều là tài sản farm hợp pháp (có mail, pass, lịch sử nuôi).
  * **CẤM TUYỆT ĐỐI tự ý logout vứt nick**: Không được xóa bỏ hay bỏ rơi nick chỉ để nhét nick mới vào.

---

## 2. Điểm nghẽn kỹ thuật khi chạm trần 8 nick trên app TikTok
- **Triệu chứng khi chạy `tiktok_login_v1.py`**:
  * Script mở app TikTok -> vào tab Hồ sơ -> mở dropdown Switcher thành công.
  * Đến bước `[4] Tap Add account`:
    `✗ Không thấy: ('Thêm tài khoản', 'Add account', 'Thêm tài khoản khác', 'Add another account')`
  * Script liên tục vuốt bottom sheet tìm kiếm nhưng không thấy, dẫn đến `UI_XML_TIMEOUT` và fail exit code 1.
- **Cơ chế UI TikTok**: Khi app TikTok đã lưu đủ **8 tài khoản** (mức trần tối đa của ứng dụng), TikTok **ẨN HOÀN TOÀN nút "Thêm tài khoản"** ở đáy Switcher. Muốn thêm nick mới bắt buộc phải giải phóng ít nhất 1 slot (máy còn <= 7 nick).

---

## 3. Quy trình chuẩn tái bố trí & điều chuyển (Rebalance Protocol)

### Bước 1: Khôi phục vị trí gốc của nick cũ & dời lùi các nick sau
- Đưa nick cũ về đúng vị trí slot ban đầu của nó (ví dụ: `samnga2403` về lại Tik 3 / Row 3).
- Giữ nguyên nick quan trọng ở vị trí chỉ định (ví dụ: `muyduyen4589` giữ nguyên Tik 1).
- Các nick khác lùi lại 1 vị trí tương ứng (`nguyentrang86016` -> Tik 4, `evangsyvupe` -> Tik 5, `ninhsyhez6u` -> Tik 6, `julesuqi6h4` -> Tik 7, `angan6670` -> Tik 8).
- Đồng bộ khớp 1:1 trên toàn bộ: `Tik1.xlsx` .. `Tik8.xlsx`, `taikhoan_run_safe.xlsx`, Master DAT `taikhoan_dat_v2_updated .xlsx`, và SQLite DB.

### Bước 2: Xác định nick non nhất để điều chuyển
- So sánh các tài khoản trên máy theo ngày reg và số lượng video đã đăng (`video_count`, `created_at`).
- Chọn tài khoản non nhất (mới reg gần đây nhất, ít video nhất) làm ứng viên chuyển sang máy khác thiếu slot (ví dụ: `hohaian929` reg 18/09, 1 video).

### Bước 3: Cổng an toàn kiểm tra máy nhận (Destination Preflight Gate)
- **BẮT BUỘC** kiểm tra máy đích (ví dụ: Máy 266 trên Cụm Admin) xem **ĐÃ ĐỦ 8 ACC CHƯA**.
- **Chỉ được phép đẩy vào KHI VÀ CHỈ KHI máy nhận còn slot trống** (ví dụ: mới có 5 nick, trống các slot 6, 7, 8).
- Nếu máy nhận đã đủ 8 nick -> Dừng lại, tìm máy khác còn thiếu.

### Bước 4: Kỷ luật bảo mật trước khi điều chuyển (2FA Gate)
- **BẮT BUỘC BẬT 2FA TOTP & ĐẶT PASS ĐẦY ĐỦ** cho nick non trước khi chuyển giao.
- Lưu trữ chính xác Secret Key 32 ký tự và Mật khẩu TikTok vào Master DAT và file Tik của máy nhận.
- **Kỷ luật điều phối:** Điền vào Excel của máy nhận trước, **TUYỆT ĐỐI CHƯA VỘI LOGIN** lên máy nhận khi chưa có lệnh.

### Bước 5: Giải phóng slot trên máy gốc & nạp nick còn thiếu
1. Đăng xuất nick non nhất khỏi máy gốc (Hồ sơ -> Menu 3 gạch -> Cài đặt và quyền riêng tư -> Cuộn đáy -> Đăng xuất).
2. Sau khi máy gốc còn 7 nick, mở lại Switcher để xác nhận nút **"Thêm tài khoản"** đã xuất hiện trở lại.
3. Chạy `tiktok_login_v1.py` đăng nhập nick còn thiếu (ví dụ `muyduyen4589` vào Tik 1) qua Pass và 2FA TOTP có sẵn.
