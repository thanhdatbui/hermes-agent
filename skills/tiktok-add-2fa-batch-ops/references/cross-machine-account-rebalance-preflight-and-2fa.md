# Điều Phối Nick Dư Giữa Các Máy & Quy Trình Bật 2FA Trước Khi Chuyển (11/10/2026)

## 1. Bối cảnh Tràn Trần 8 Nick trên thiết bị
- TikTok trên Android chỉ cho phép lưu tối đa 8 tài khoản trong Switcher.
- Khi máy bị dồn thừa nick (ví dụ máy 74 có 8 nick trong app nhưng cần đưa nick chính chủ khác vào), tài khoản trên máy KHÔNG PHẢI KÍ SINH mà là tài sản farm.
- Quy trình: chọn nick non nhất (reg gần nhất, ít video, ít fl) chuyển sang máy thiếu slot (< 8 nick, ví dụ M266 Admin).

## 2. Kỷ luật Bật 2FA & Đặt Pass trên máy nguồn trước khi chuyển
- **Invariant**: Tuyệt đối KHÔNG logout nick non ra khỏi máy nguồn khi chưa có mật khẩu và 2FA.
- **Thực thi Phase B**:
  - Chạy `run_capture_phase_b.py --live` trên máy nguồn (máy đang giữ phiên login của nick).
  - Tự động đặt mật khẩu đạt chuẩn và bật 2FA TOTP (Authenticator App), trích xuất Secret Key 32 ký tự.
  - Ghi nhận đầy đủ Mật khẩu + Secret Key vào workbook.
- **Ghi sổ trước, login sau**:
  - Cập nhật thông tin nick vào các file Excel của máy nhận (TikN.xlsx, taikhoan_run_safe.xlsx, taikhoan_dat_v2_updated .xlsx).
  - TUYỆT ĐỐI CHƯA vội login lên máy nhận cho đến khi có ca chạy hoặc chỉ đạo.
  - Đăng xuất nick khỏi máy nguồn để nhả slot cho nick chính chủ.
