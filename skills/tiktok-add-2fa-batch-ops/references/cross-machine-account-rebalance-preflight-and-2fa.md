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

## 3. Pitfalls Kỹ Thuật Khi Chạy Phase B Trên Nick Điều Chuyển
- **Bẫy Stale 2FA Cell trong Workbook (`WorkbookPreflight has_2fa=True`)**:
  * Khi gán nick mới vào một dòng trên Master Excel (`taikhoan_dat_v2_updated .xlsx`), nếu ô cột 5 (`2FA`) hoặc cột 4 (`PASS`) vẫn còn lưu secret/pass của nick cũ trước đó, `inspect_target()` sẽ trả về `has_2fa=True`.
  * Hậu quả: `run_capture_phase_b.py` fail-closed ngay lập tức với `{"status": "failed", "reason": "WorkbookError"}`.
  * Khắc phục: Trước khi kích hoạt Phase B, bắt buộc clear sạch ô:
    ```python
    ws.cell(row, 4).value = None  # PASS
    ws.cell(row, 5).value = None  # 2FA
    ```
    Đảm bảo kiểm tra `WorkbookPreflight(identity_matches=True, has_2fa=False)` trước khi khởi chạy `--live`.
- **Bẫy Tên File Master Có Khoảng Trắng (`taikhoan_dat_v2_updated .xlsx`)**:
  * Chú ý file Master luôn có dấu cách trước phần mở rộng: `taikhoan_dat_v2_updated .xlsx`. Khi truyền qua bash terminal cần bọc nháy kép cẩn thận, tránh lỗi phân tách tham số hoặc regex guard.
- **Kỷ Luật Output Điều Phối (Cấm Rò Rỉ Gate Text)**:
  * Tuyệt đối không để text của các hook kiểm duyệt nội bộ (`[EVIDENCE FIRST GATE — FAIL-CLOSED VIOLATION]...`) xả thẳng vào output trả lời User trên Telegram. Báo cáo bằng chứng ngắn gọn, trung thực và tập trung vào kết quả thực tế.
