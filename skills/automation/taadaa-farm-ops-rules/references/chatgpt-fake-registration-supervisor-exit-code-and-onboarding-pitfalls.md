# Khắc Phục Lỗi "Registered Ảo", Exit Code 0 & Nhận Diện Onboarding "/about-you" (2026-10-26)

## 1. BẢN CHẤT DỮ LIỆU & THUẬT NGỮ CHUẨN
- **Hotmail Farm là Mail MUA (Bought Mail)**: Toàn bộ Hotmail trên farm đều là mail mua từ nhà cung cấp (lưu tại `D:/Taadaa/Hotmail/latest_bought_*.txt`), **hoàn toàn KHÔNG CÓ script reg Hotmail**. 
  - Quy trình supervisor: `[HOTMAIL_LOGIN]` (login mail mua vào GPM) ──► `[CHATGPT_REG]` (dùng mail đó đăng ký ChatGPT) ──► `[WAIT_7D]` ──► `[CHANGE_INFO]` ──► `[DONE]`.
  - CẤM TUYỆT ĐỐI gọi tắt là "reg Hotmail" gây hiểu lầm và báo cáo sai lệch.

## 2. NHẬN DIỆN MÀN HÌNH "BẠN BAO NHIÊU TUỔI?" (`/about-you`)
- **Nguyên lý của OpenAI**:
  - Màn hình hỏi Tên + Tuổi / Ngày sinh (`https://auth.openai.com/about-you` hoặc title *"Bạn bao nhiêu tuổi? - OpenAI"*, *"How old are you? - OpenAI"*) **CHỈ XUẤT HIỆN TRÊN TÀI KHOẢN ĐANG TẠO MỚI LẦN ĐẦU (New User Onboarding)**.
  - Một tài khoản khi đã đăng ký ChatGPT hoàn tất và được cấp token hợp lệ thì trong các lần đăng nhập lại sau này **KHÔNG BAO GIỜ** xuất hiện lại màn hình `/about-you`.
- **Dấu hiệu tài khoản "Registered Ảo"**:
  - Nếu supervisor state ghi `chatgpt_registered_at` có timestamp nhưng khi mở ra trang login lại văng vào `/about-you` -> **BẰNG CHỨNG THỰC TẾ: TÀI KHOẢN CHƯA HỀ ĐƯỢC ĐĂNG KÝ XONG TRƯỚC ĐÓ**.
  - Không được dựa vào timestamp trong file state để kết luận acc đã reg, bắt buộc kiểm chứng bằng sự tồn tại của session token hoặc chat prompt textarea.

## 3. NGUYÊN NHÂN GỐC RỄ CỦA LỖI ĐÓNG DẤU THÀNH CÔNG ẢO
1. **Child Script luôn Exit Code 0**:
   - Trong `chatgpt_gpm_direct_reg.py`, khi không tìm thấy candidate hoặc khi đăng ký thất bại (`FAIL_PASSWORD_NOT_FOUND`, `FAIL_WRONG_OTP`, `FAIL_NO_PROMPT`), hàm `main()` vẫn kết thúc bằng `return 0`.
2. **Supervisor phụ thuộc mù quáng vào Process Exit Code**:
   - Trong `batch_gpm_5profiles_supervisor.py`:
     ```python
     ok_chatgpt = run_cmd([sys.executable, str(CHATGPT_REG_SCRIPT), ...])
     if ok_chatgpt:
         info["chatgpt_registered_at"] = now()
     ```
     `run_cmd` chỉ kiểm tra `proc.returncode == 0`. Do script con exit 0, `ok_chatgpt` luôn là `True`, dẫn tới supervisor tự động đóng dấu thành công và đẩy tài khoản sang `WAIT_7D` rồi `DONE`.
3. **Lệch cấu trúc Workbook giữa các cụm (Kibe vs Admin)**:
   - `chatgpt_gpm_direct_reg.py` chỉ tìm kiếm cột `PASS CHATGPT` trong workbook Kibe (`kibe/taikhoan_dat_v2_updated .xlsx`).
   - Cụm Admin (`admin/taikhoan_dat_v2_updated .xlsx`) chỉ có 10 cột, không có cột 11 `PASS CHATGPT`. Do đó 100% tài khoản Admin bị bỏ qua (`candidates = []`) ➔ kích hoạt exit 0 ➔ supervisor đóng dấu thành công ảo toàn bộ cụm Admin!

## 4. QUY CHUẨN SỬA CHỮA (CONTRACT ENFORCEMENT)
1. **Child Script Exit Code Contract**:
   - `chatgpt_gpm_direct_reg.py` BẮT BUỘC trả về exit code khác 0 (`return 1`) khi:
     - `candidates` rỗng (đặc biệt khi có filter `--email`).
     - Bất kỳ candidate nào có `status` không thuộc `("SUCCESS", "ALREADY_LOGGED_IN", "DRY_RUN_OK")`.
   - CHỈ ĐƯỢC PHÉP `return 0` khi và chỉ khi có ít nhất 1 candidate và 100% candidate đều thành công thực sự.
2. **Password Fallback & Quirk Tên File `gmail_clean_v2.xlsx`**:
   - *Bẫy tên file legacy*: File `D:/OneDrive/TaadaaData/admin/gmail_clean_v2.xlsx` có tên chứa chữ `gmail` vì lý do lịch sử, nhưng thực chất chứa **100% tài khoản HOTMAIL (725 Hotmail, 0 Gmail)**. Mỗi dòng đối chiếu đúng email Hotmail đó với mật khẩu hòm mail chính nó (cột 3) và Graph API refresh token (cột 9-10). Tuyệt đối không nhầm là lấy pass của Gmail gán cho Hotmail.
   - *Quy tắc `normalize_password(pwd)`*: Mật khẩu gốc $\ge 12$ ký tự được giữ nguyên vẹn 100%. CHỈ KHI mật khẩu hòm mail gốc $< 12$ ký tự (Hotmail mua thường chỉ 8-10 ký tự) mới tự động ghép hậu tố `@Taadaa2026` để thỏa mãn chính sách bảo mật bắt buộc $\ge 12$ ký tự của OpenAI khi tạo tài khoản.
3. **Graph Token Pre-Validation**:
   - Trong 692 token Hotmail của Admin, có một phần grant đã hết hạn (`AADSTS70000`). Trước khi mở profile GPM chạy OTP, script nên validate nhanh token bằng request POST đến `https://login.microsoftonline.com/common/oauth2/v2.0/token` để chỉ bốc các account có token còn sống, tránh timeout 30s vô ích trên profile chết grant.
4. **Xử lý trọn vẹn màn hình Onboarding `/about-you`**:
   - Điền Tên (`input[name="name"]`) + Tuổi $\ge 25$ (`input[name="age"]`).
   - Click nút submit (`Tiếp tục` / `Continue`).
   - BẮT BUỘC `p.wait_for_url(lambda u: "chatgpt.com" in u)` để đợi OpenAI hoàn tất cấp session trước khi gọi `extract_session_token()`. Nếu trích xuất ngay khi URL còn ở `about-you` thì cookie chưa được ghi và sẽ bị miss token.
5. **Supervisor Verification Invariant**:
   - Supervisor cấm chỉ tin vào exit code 0. Bắt buộc kiểm tra có session token được sinh ra hoặc report JSON ghi nhận `status: SUCCESS` trước khi cập nhật `chatgpt_registered_at`.
