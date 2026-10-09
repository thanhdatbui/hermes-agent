# Kỷ Luật Bảo Toàn Tài Sản Nick Farm & Đối Soát Đến Cùng (2026-09-25)

## 1. Bối cảnh & Sự cố Phán đoán sai lầm (Root Cause)
- **Hiện tượng**: Khi kiểm tra máy chạm trần 8 nick (ví dụ Máy 3), phát hiện một nick (`@annhubvqttr`) không có tên trong file Excel `taikhoan_dat_v2_updated .xlsx`.
- **Phản xạ sai lầm chết người**: Agent vội vã kết luận nick này là "nick lạ / nick rác không có trong cơ sở dữ liệu" và tự ý thực hiện đăng xuất (logout) khỏi thiết bị để lấy slot trống.
- **Sự thật khi điều tra sâu**: Nick này chính là tài khoản chính chủ của Máy 3 (tạo từ ngày 08/09/2026, tiền tố Gmail `an.nhuan.work64541@gmail.com`). Trong quá khứ, luồng reg đêm bị lỗi chưa kịp ghi vào Excel, sau đó Gmail bị thanh lọc nhầm khỏi `gmail_clean_v2.xlsx`, nhưng phiên TikTok trên máy vẫn sống bình thường.

## 2. Invariant Cốt Lõi: CẤM GỠ TÀI KHOẢN KHI CHƯA CHỨNG MINH KÝ SINH
- **Quy tắc tuyệt đối**: MỌI tài khoản đang tồn tại trên thiết bị ĐỀU LÀ TÀI SẢN CỦA FARM.
- **Định nghĩa nick ký sinh**: Chỉ được coi là ký sinh khi và chỉ khi chứng minh được nick đó thuộc sở hữu chính chủ của một máy khác (trùng username/email với một dòng của máy khác trong Excel).
- **Trường hợp nick không có trong Excel**:
  - TUYỆT ĐỐI CẤM gán nhãn "nick rác" rồi logout.
  - BẮT BUỘC coi đây là **NICK CHÍNH CHỦ BỊ THẤT LẠC / SÓT GHI WORKBOOK** của máy đó.
  - BẮT BUỘC thực hiện quy trình **BACKFILL & PHỤC HỒI**:
    1. Truy vết nguồn gốc qua các file backup (`backup_clean_v2_*`, `gmail_clean_v2.bak*`, log reg cũ).
    2. Nếu tìm thấy thông tin email/pass/2FA: Khôi phục ngay vào dòng trống của máy đó trên `taikhoan_dat_v2_updated .xlsx` và sync `taikhoan_run_safe.xlsx`.
    3. Nếu không tìm thấy thông tin mật khẩu: Báo cáo rõ ràng cho User xin chỉ thị, TUYỆT ĐỐI CẤM tự ý xóa hay logout.

## 3. Cấm Tự Viết Lại Script Logout Khi Đã Có Tool Canonical
- Khi cần thao tác logout nick ký sinh hợp pháp, BẮT BUỘC dùng công cụ canonical có sẵn:
  - `python D:/Taadaa/tools/do_logout_account.py <machine_id> <username> <serial>`
  - `python D:/Taadaa/tools/run_logout_all.py`
- CẤM TUYỆT ĐỐI Coordinator hay Worker tự sinh script `logout_mX.py` tạm bợ. Việc tự sinh script lặp lại luôn dẫn đến lỗi timeout 600s, kẹt API calls và không kế thừa đúng các bẫy UI đã được xử lý.
