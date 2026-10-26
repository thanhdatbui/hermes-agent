---
name: tiktok-auth-recovery-and-password-sync
description: Use when TikTok login has wrong pass. Reset via token.
---

# TikTok Auth Recovery & Password Sync

## Invariant Vận Hành (User Rule 2026-10-25)
- **Cấm ném "kỷ luật suông" vào memory thay vì sửa script**: Khi phát hiện lỗi pass sai, TUYỆT ĐỐI CẤM Agent chỉ lưu các điều khoản "kỷ luật" vào persistent memory rồi dừng lại báo cáo suông. BẮT BUỘC phải vá logic trực tiếp vào script canonical (`tiktok_login_v1.py` / `login_runner.password_change`) để toàn bộ dàn máy tự động hành động.
- **Tự động cứu tài khoản khi sai pass**: Khi TikTok login báo sai mật khẩu (`Mật khẩu sai`, `Bạn cần trợ giúp đăng nhập?`, `WRONG_PASS_HINTS`) hoặc tài khoản reg email-only thiếu pass: **TUYỆT ĐỐI CẤM** dừng lại báo `[AUTH_BLOCKED]` / `PASSWORD_RETRY_BLOCKED`, đoán mò pass hay hỏi xin phép lý thuyết suông ("Ủa sao lại là skill. T ép chạy thành script hết r mà?").
- **Quy trình 2 bước thực thi tự động khi gặp sai pass**:
  1. **Đối soát dữ liệu O(1) (Data Audit)**: Tra soát kỹ lại dữ liệu trong `taikhoan_dat_v2_updated .xlsx` (cột PASS) và `gmail_clean_v2.xlsx` (xem có đầy đủ refresh_token / client_id hay không) xem có lưu sai mật khẩu không.
  2. **Kích hoạt ngay script canonical phục hồi mật khẩu**: Nếu dữ liệu không lưu nhầm (pass mặc định từ lúc reg email-only qua Outlook không khớp server TikTok), lập tức chạy script `change_tiktok_passwords.py` để reset qua Microsoft Graph API trên PC và đồng bộ pass mới:
     ```bash
     python D:/Taadaa/tiktok-log-in/scripts/change_tiktok_passwords.py \
         --workbook-path "D:/OneDrive/TaadaaData/<cluster>/taikhoan_dat_v2_updated .xlsx" \
         --machines <N> \
         --rows <excel_row_index> \
         --allow-live-password-change \
         --full-scope-takeover \
         --runtime-root "D:/Taadaa/runtime/<cluster>"
     ```
- **BẮT BUỘC 100% tự động chuyển flow cứu tài khoản trong `drive_login_screens`**:
  1. Xóa bỏ lệnh `return` ngắt luồng; set cờ `account["needs_password_reset"] = True` và `force_otp = True`.
  2. Tap *"Bạn cần trợ giúp đăng nhập?"* / *"Quên mật khẩu?"* / *"Đăng nhập bằng mã xác minh"* trên form đăng nhập TikTok.
  3. Lấy mã xác minh OTP trực tiếp từ Microsoft Graph API trên PC (cột 9-10 `gmail_clean_v2.xlsx`, CẤM mở app Outlook trên điện thoại).
  4. Hoàn tất đăng nhập vào Home feed.
  5. Kích hoạt module `login_runner.password_change`, sinh mật khẩu mới ngẫu nhiên 16 ký tự, submit vào TikTok và đồng bộ ngay lập tức vào cột PASS của `taikhoan_dat_v2_updated .xlsx` sheet `Tài Khoản`.
  6. Sau khi sync Excel thành công, BẮT BUỘC gọi `journal.purge(target)` để xóa sạch file encrypted recovery `.dpapi` trong runtime, tránh tồn dư state cũ.

## Các Pitfalls Kỹ Thuật Khi Chạy `password_change.py`
1. **Biến môi trường Single-Writer Lock bắt buộc**:
   - `os.environ["TIKTOK_PASSWORD_EXPECTED_WRITER_ID"] = "password_change_runner"`
   - `os.environ["TIKTOK_PASSWORD_WRITER_ID"] = "password_change_runner"`
   - `os.environ["HOTMAIL_WORKBOOK"] = r"D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx"`
   - `os.environ["TIKTOK_PASSWORD_WORKBOOK"] = r"D:\OneDrive\TaadaaData\admin\taikhoan_dat_v2_updated .xlsx"`
   - `os.environ["TIKTOK_F2A_PROVIDER_ROOT"] = r"D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner"` (BẮT BUỘC trỏ vào thư mục con `python_runner`, không trỏ vào repo root).
   - Nếu thiếu `TIKTOK_PASSWORD_EXPECTED_WRITER_ID`, hàm `acquire_single_writer_workbook_lock` ném `BLOCKED_EXPECTED_WRITER_ID_MISSING` và không lưu được mật khẩu mới vào workbook dù TikTok đã đổi pass thành công.
2. **Pitfall "Mật khẩu mới không thể giống mật khẩu cũ"**:
   - Khi candidate password từ journal đã được submit thành công lên TikTok ở attempt 1 nhưng tiến trình bị ngắt trước khi ghi Excel: khi chạy attempt 2 với cùng candidate password đó, TikTok sẽ hiển thị thông báo lỗi: *"Mật khẩu mới không thể giống mật khẩu cũ"*.
   - Đây là bằng chứng xác thực TikTok ĐÃ CẬP NHẬT mật khẩu mới. Phải trích xuất mật khẩu từ journal (`<account_id>.dpapi` giải mã bằng entropy `codex-tiktok-password-change-v1`) và gọi `write_password_preserving_archive` để đồng bộ vào file Excel.
3. **Popup Solver từ `automation-core`**:
   - Khi form login / switcher bị chắn bởi bottom-sheet *"Thêm số điện thoại của bạn để tăng cường bảo mật"*, tích hợp `automation_core.tiktok_popup` (rule `add_phone_number_vi`, click nút "Đóng" `bounds=[936,861][1056,993]`) để giải phóng giao diện tự động. CẤM viết parser regex riêng.
4. **Excel Row Index vs Slot/Folder Video & Admin Remote ADB**:
   - Tham số `--rows <N>` của `change_tiktok_passwords.py` nhận **chỉ số hàng vật lý trong Excel (1-indexed physical row)** (ví dụ: dòng 171 trong Excel sheet `Tài Khoản`), **CẤM NHẦM** với số cột Folder Video (ví dụ: 482) hay account index theo máy. Bắt buộc tra cứu đúng số dòng vật lý trong workbook trước khi truyền `--rows`.
   - Với máy cụm Admin ($m \ge 200$), `AdbClient` kết nối qua host remote `192.168.110.119:5037`. Provider roots bắt buộc trỏ đúng `D:/Taadaa/tiktok-add-bao-mat-f2a/python_runner` và `D:/Taadaa/Tiktok_Reg`.
   - Timeout cho luồng đổi pass và recovery qua Graph API trên remote host tối thiểu $\ge 600s$.
5. **Kỷ Luật Dữ Liệu Excel (Chưa đặt pass thì để None/Blank, CẤM ghi bậy pass ảo)**:
   - Các tài khoản reg email-only (như qua Outlook app) chưa qua bước tạo pass thật sự trên TikTok thì cột `PASS` trong Excel BẮT BUỘC để trống (`None` / blank).
   - TUYỆT ĐỐI CẤM tự ý sinh pass random rồi ghi bậy vào cột PASS khi chưa xác thực thành công trên TikTok. Việc này khiến các runner lầm tưởng tài khoản đã có pass, thử login bằng pass dẫn tới lỗi `Mật khẩu sai` và nguy cơ bị TikTok khóa nick / rate limit.
   - Khi cột `PASS` để `None`, runner sẽ tự động nhận diện tài khoản reg email-only và đi thẳng vào luồng OTP hoặc phục hồi mật khẩu mà không gõ pass mù.
6. **Canary Tái Hiện Lỗi Bắt Buộc Nhắm Trúng Account/Row Bị Lỗi (Chống Test Nhầm Acc Hoạt Động)**:
   - Khi chạy Canary kiểm chứng sau bản vá login/recovery: BẮT BUỘC tra cứu đúng `--row <N>` của tài khoản bị lỗi/vắng mặt.
   - TUYỆT ĐỐI CẤM test nhầm `--row 1` có sẵn tài khoản đã login trên máy, vì `profile_preflight` sẽ báo `already matched` và pass thành công ảo mà hoàn toàn không kích hoạt luồng login cần test.
   - Timeout Canary cho toàn bộ luồng recovery/login trên dàn máy remote Admin bắt buộc $\ge 720s$ để bù đắp độ trễ ADB remote và thời gian OTP Graph API.
