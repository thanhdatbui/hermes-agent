# Kỷ Luật Giải Tỏa Trần 8 Nick & Tái Phân Bổ Khi Máy Bị Reg Dư (8-Slot Rebalance Protocol)

## 1. Bản chất sự cố Máy đụng trần 8 nick & Báo động giả "Mất phiên / Văng Account"
- **Nguyên nhân hình thành 9 nick trên 1 máy:**
  * Lịch sử farm mở rộng từ 3-4 ca lên 8 ca/ngày (Tik 1 -> Tik 8).
  * Trong các đợt reg bù tài khoản tự động, tool reg chỉ bấm "Thêm tài khoản" mà không kiểm tra số lượng nick thực tế đang login trên máy và không logout nick cũ.
  * Hậu quả: Nick cũ (`samnga2403`) vẫn lưu phiên trên app, các nick mới được nạp vào làm tổng số nick chạm trần cứng 8 tài khoản của TikTok Android.
  * Khi đó, một nick chính thức (ví dụ Tik 1 `muyduyen4589`) có tên trên Excel nhưng không còn chỗ trên app thật -> Khi ca chạy tìm nick không thấy -> Ném exception `ACCOUNT_MISSING: expected account was not found` -> Watchdog farm bắt nhầm thành "Văng account / Mất phiên".

---

## 2. Kỷ luật phân loại tài sản: CẤM GỌI BỪA LÀ "KÝ SINH" ĐỂ XÓA VỨT NICK
- **Định nghĩa Tài sản Farm:** Mọi nick đang login sống trên máy đều là tài sản đã được tạo, nuôi và có tài nguyên (Gmail, Pass, 2FA).
- **CẤM TUYỆT ĐỐI:**
  * Không được vội vàng coi nick cũ chưa logout là "ký sinh/rác" rồi đòi chạy script logout vứt bỏ nick.
  * Không được tự ý xóa nick khỏi bảng tính Master để che đậy việc reg dư.
  * Nhận định đúng: Lỗi là do hệ thống reg dư làm máy có 9 nick tranh nhau 8 slot, cả 9 nick đều là tài sản cần được bảo toàn.

---

## 3. Quy trình chuẩn 5 bước giải tỏa trần 8 nick & Tái phân bổ (Rebalance Protocol)

### Bước 1: Khảo sát thực tế trên thiết bị (Soi mắt Switcher)
- Chụp ảnh màn hình danh sách tài khoản trong Bottom Sheet "Chuyển đổi tài khoản" (Account Switcher).
- Dùng Native OCR / Vision đọc chính xác danh sách 8 nick đang login thực tế trên app.
- Đối chiếu 1:1 với Master DAT và `taikhoan_run_safe.xlsx` để xác định:
  * Nick nào đang có trong máy nhưng thiếu trên Excel (ví dụ `samnga2403`).
  * Nick nào có trên Excel nhưng chưa vào được máy (ví dụ `muyduyen4589`).

### Bước 2: Xác định nick non nhất để di dời
- Kiểm tra số lượng video đã đăng, ngày reg, số follower của 8 nick trên máy:
  * Ưu tiên giữ lại các nick nuôi lâu, nhiều video, có lịch sử chạy ổn định.
  * Chọn nick **non nhất** (mới reg gần nhất, ít hoặc chưa có video, ví dụ `hohaian929` reg 18/09 mới có 1 video) làm ứng viên chuyển máy.

### Bước 3: Tìm máy đích tiếp nhận (Thiếu slot < 8 acc)
- Rà soát các máy trong cụm Kibe hoặc Admin còn trống slot (ví dụ Máy 266 Admin mới có 5 nick, trống slot 6, 7, 8).
- Ghi nhận nick non nhất vào bảng tính của máy đích (`TikN.xlsx`, `taikhoan_run_safe.xlsx`, Master DAT của cụm đó).
- **LƯU Ý:** Ghi sổ sách trước, TUYỆT ĐỐI CHƯA login lên máy đích khi chưa có lệnh.

### Bước 4: Sắp xếp lại thứ tự slot trên máy nguồn (Bảo toàn vị trí gốc)
- **Quy tắc sắp xếp:**
  * Nick quan trọng / nick gốc (ví dụ Tik 1 `muyduyen4589`) giữ nguyên vị trí cũ.
  * Nick cũ đang có sẵn trong app (`samnga2403`) được trả về đúng vị trí slot cũ của nó (ví dụ Tik 3).
  * Các nick ở giữa lùi lại 1 vị trí (Tik 3 -> Tik 4, Tik 4 -> Tik 5, Tik 5 -> Tik 6...).
  * Đồng bộ đồng thời và nhất quán 100% trên 4 tầng:
    1. `Tik1.xlsx` -> `Tik8.xlsx`
    2. `taikhoan_run_safe.xlsx`
    3. Master DAT `taikhoan_dat_v2_updated .xlsx`
    4. SQLite Database (`account_mapping` & `farm_account_info`)

### Bước 5: Bảo mật trước khi di dời & Luân chuyển thực tế
- Trước khi đẩy nick non nhất ra khỏi máy, bắt buộc phải bảo đảm tài khoản đã có Mật khẩu TikTok và bật 2FA TOTP đầy đủ.
- Logout nick non nhất khỏi máy nguồn để giải phóng chỗ (máy nguồn còn 7 nick).
- Login nick còn thiếu (Tik 1 `muyduyen4589`) vào lại máy nguồn để hoàn thiện đủ 8 nick trên app.

---

## 4. Cảnh báo kỹ thuật đường dẫn file Master Excel
- File Master của Cụm Kibe có khoảng trắng trước đuôi mở rộng: `taikhoan_dat_v2_updated .xlsx` (chú ý `" .xlsx"`).
- Khi dùng glob hoặc duyệt thư mục bằng Python:
  * `glob.glob('*taikhoan_dat*')[0]` sẽ bắt trúng file backup `.bak_...` xếp trước theo bảng chữ cái.
  * Bắt buộc dùng `Path(root) / ('taikhoan_dat_v2_updated' + ' .xlsx')` hoặc kiểm tra chính xác `p.name == 'taikhoan_dat_v2_updated .xlsx'` để tránh sửa nhầm file backup.
