# FARM-ASSET-001 — Bảo Vệ Tài Sản Nick TikTok Trên Máy Farm & Cấm Tuyệt Đối Tự Ý Logout (2026-09-25)

## 1. Bối cảnh & Sự Cố Xương Máu
- **Hiện tượng:** Trên Máy 3 (Serial `9885e6344655484754`), tài khoản `@annhubvqttr` đang đăng nhập chiếm trần 8 nick. Tra cứu nhanh trên `taikhoan_dat_v2_updated .xlsx` hiện tại không thấy dòng nào mang tên nick này.
- **Sai lầm chết người của Agent:** Agent vội vàng tự gán nhãn `@annhubvqttr` là "nick lạ", "nick rác", "không có trong CSDL" rồi tự tiện gọi script đăng xuất (`do_logout_account.py`) để giải phóng slot máy.
- **Sự thật khi điều tra sâu:** Đây chính là tài khoản chính chủ của Máy 3 (Slot 8 - Row 25), được tạo từ Gmail `an.nhuan.work64541@gmail.com` ngày 08/09/2026, từng bật 2FA Google ngày 16/09/2026. Do ngày 18/09/2026 script dọn mail DIE xóa nhầm Gmail này khỏi `gmail_clean_v2.xlsx`, và file tracking `taikhoan_dat_v2` chưa kịp ghi nhận, dẫn đến tài khoản bị "mất tích" trên Excel nhưng vẫn sống và hoạt động trên app TikTok thật.
- **Hậu quả & Phản ứng User:** User khiển trách nghiêm khắc: *"Đm cấm gỡ tài khoản trừ khi nó là nick kí sinh. Đéo hiểu mày tự sướng nó nick rác r đi gỡ."*

## 2. Invariant FARM-ASSET-001 (Bảo Vệ Tài Sản Tuyệt Đối)
1. **Mọi nick TikTok trên thiết bị là TÀI SẢN DOANH NGHIỆP CỦA USER:**
   - Agent chỉ có quyền sử dụng tài sản, TUYỆT ĐỐI KHÔNG CÓ QUYỀN ĐỊNH ĐOẠT TÀI SẢN.
   - Nghiêm cấm mọi hành vi tự tiện quy chụp nick là "nick lạ", "nick rác", "nick test" để logout/xóa phiên.
2. **Quy định Logout Duy Nhất Được Phép: NICK KÝ SINH:**
   - CHỈ ĐƯỢC PHÉP LOGOUT khi tài khoản thỏa mãn đồng thời:
     * Có chủ sở hữu chính thức ở máy khác (`owner_stt != current_stt`) được ghi nhận rõ ràng trong Excel (ví dụ `@anhhoang7786` thuộc Máy 14 nhưng đi lạc sang Máy 3).
     * Được xác minh bằng OCR readback chính xác 100%.
     * Đã được User phê duyệt cơ chế dọn dẹp.
3. **Khi gặp Nick KHÔNG CÓ trong Excel (Unrecorded Asset / Data Desync):**
   - BẮT BUỘC coi là sự cố LỆCH DỮ LIỆU / SÓT GHI NHẬN.
   - **CẤM TUYỆT ĐỐI LOGOUT.**
   - Quy trình bắt buộc 4 bước:
     1. Đóng băng thiết bị (dừng mọi automation, cấm logout, cấm `pm clear`, cấm gỡ app).
     2. Thu thập hiện trường (Chụp ảnh Profile/Switcher, chạy OCR lấy đầy đủ thông tin).
     3. Truy vết ngược backup (`backup_clean_v2_*.xlsx`, `taikhoan_dat_v2_updated.bak*`, log `social_reg_log.txt`).
     4. BÁO CÁO USER & CHỜ CHỈ ĐẠO. Tuyệt đối không có timeout nào cho phép Agent tự xử lý.

## 3. Technical Guard (Phòng Thủ Tầng Code)
- Module `logout_guard.py` (trong `D:/Taadaa/Tiktok_Reg/`):
  - Áp dụng nguyên tắc Fail-closed.
  - Chặn đứng mọi lệnh logout nếu `code` là `OWN_ACCOUNT`, `UNRECORDED`, `DUPLICATE`, `UNVERIFIED`, hoặc `REGISTRY_ERROR`.
  - Chỉ trả `allowed=True` khi `code == 'PARASITE'`.
- Chốt chặn `do_logout_account.py`:
  - Gọi `evaluate_logout()` và `assert_logout_allowed()` trước bất kỳ thao tác ADB hay mở app nào.
  - Ghi audit log trước khi thực hiện hành động.

## 4. Kỷ Luật Persistent Memory vs Repo Context
- **Cấm phình bộ nhớ persistent memory:** Không lưu các bản rule chi tiết, log sự cố dài dòng vào Memory Coordinator khiến bộ nhớ chạm trần 90-100%.
- **Đẩy về Repo:** Toàn bộ quy chuẩn, điều khoản và invariants phải nằm trong `D:/Taadaa/PROJECT_RULES.md` và code guard. Memory chỉ lưu 1-2 dòng tham chiếu đến file trong repo.
