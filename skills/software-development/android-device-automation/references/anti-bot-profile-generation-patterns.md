# Anti-Bot Profile Generation Patterns (Name, Username, Password)

Cơ chế sinh thông tin tài khoản tự động (Profile Generation) cho luồng đăng ký trên Farm (Google / Gmail, TikTok, Hotmail) để tránh bị hệ thống AI / Anti-Bot gắn cờ pattern.

## 1. Tên Người Dùng (Vietnamese Names & Middle Names)
- **Anti-pattern**: Chỉ random `Họ + Tên` 2 từ (`Nguyen An`, `Tran Dung`), thiếu tự nhiên và không gian tổ hợp nhỏ (~5,000 tổ hợp).
- **Quy chuẩn tự nhiên**:
  - **Tên 2 từ (20-25%)**: `Họ + Tên chính` (vd: `Tran Dung`, `Son Tra`).
  - **Tên 3 từ (55-60%)**: `Họ + Tên đệm + Tên chính` (vd: `Nguyen Van An`, `Bui Minh Tuyen`).
  - **Tên 4 từ (15-20%)**: `Họ + Đệm 1 + Đệm 2 + Tên chính` (vd: `Cao Bao Duc My`, `Gia Duc Thanh Tuong`).
- **Pool Tên đệm (`DEM_POOL`)**:
  `Van`, `Thi`, `Ngoc`, `Hoang`, `Minh`, `Quang`, `Thanh`, `Duc`, `Dinh`, `Huu`, `Xuan`, `Hai`, `Thu`, `Bao`, `Anh`, `Cong`, `Trong`, `Gia`, `Tuan`, `Phuoc`, `Kim`, `Tien`, `Hong`, `Phuong`, `Khanh`, `Duy`, `Nhat`, `Thao`, `My`, `Quoc`.
- **Lưu ý nhập liệu ADB với tên có khoảng trắng (CRITICAL)**:
  Khi gõ Tên có tên đệm (có chứa khoảng trắng như `"Hoang Tuoc"`), `adb shell input text` trên Android bắt buộc phải mã hóa khoảng trắng thành `%s` (vd: `text.replace(" ", "%s")`) hoặc dùng `human_type` / `AdbKeyboard`. Nếu truyền khoảng trắng trực tiếp, lệnh Android shell `input` sẽ bị tách đối số `argv` và không gõ được chữ nào vào ô nhập (dẫn đến lỗi bỏ trống ô tên và kẹt form).

## 2. Cấu Trúc Username (Email / Account ID)
- **Anti-pattern**: 
  - Chèn chuỗi ký tự rác vô nghĩa ở giữa chữ số (vd: `nguyenanabc1502`).
  - Cố định một vài format duy nhất hoặc bắt buộc phải có ngày sinh đầy đủ.
- **Quy chuẩn tự nhiên (đa dạng 10+ styles)**:
  1. `{ho}.{ten}{nam2}` *(vd: `nguyen.an99`)*
  2. `{ten}.{ho}{nam2}` *(vd: `an.nguyen01`)*
  3. `{ho}{dem}{ten}{nam2}` *(vd: `nguyenvanan99`)*
  4. `{ho}.{dem}.{ten}{nam2}` *(vd: `nguyen.van.an02`)*
  5. `{ten}{ho}{random_3digits}` *(vd: `annguyen672`)*
  6. `{ho}{ten}{ngay}{thang}` *(vd: `nguyenan1508`)*
  7. `{ten}.{ho}.{ngay}{thang}` *(vd: `an.nguyen.1508`)*
  8. `{ho}{ten}{nam4}` *(vd: `nguyenvanan2001`)*
  9. `{ho}{ten}{suffix}{nam2}` với suffix là từ ngắn tự nhiên (`vn`, `hn`, `hcm`, `pro`, `work`, `dev`, `k`, `tb`...).
  10. `{ten}{dem}{ho}{random_2digits}` *(vd: `anvannguyen88`)*
- **Ràng buộc chuẩn**:
  - Độ dài chuẩn: 6 đến 30 ký tự.
  - Tự động strip dấu chấm đầu/cuối `.`, thay thế chấm kép `..` thành chấm đơn `.`.

## 3. Cấu Trúc Mật Khẩu (Password Entropy)
- **Anti-pattern**: Dùng hậu tố cố định cho toàn bộ tài khoản farm (vd: `@Ks` ở đuôi toàn bộ account). Khi 1 account bị soi, AI dễ truy vết hàng loạt account cùng format.
- **Quy chuẩn bảo mật & tự nhiên**:
  - Độ dài 10–22 ký tự, đủ chữ hoa, chữ thường, số, ký tự đặc biệt.
  - Random ký tự đặc biệt trong tập `[@, #, !, $, %]`.
  - Phân tán cấu trúc:
    - `{Ho}{Ten}{ddmmyyyy}{sym}` *(vd: `NguyenVanAn15082001@`)*
    - `{Ho}{Ten}@{nam}` *(vd: `NguyenVanAn@2001`)*
    - `{Ten}{Ho}#{ddmmyyyy}` *(vd: `AnNguyen#15082001`)*
    - `{Ho}{Ten}{sym}{Word}{nam2}` *(vd: `NguyenVanAn@Plus02`, `NguyenAn!Pro99`)*
    - `{Ten}{sym}{Ho}{nam}` *(vd: `VanAn@Nguyen2001`)*
    - `{Word}{Ho}{Ten}{nam}{sym}` *(vd: `StarNguyenAn2001#`)*
