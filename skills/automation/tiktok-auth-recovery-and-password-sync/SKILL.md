---
name: tiktok-auth-recovery-and-password-sync
description: Use when TikTok login has wrong pass. Reset via token.
---

# TikTok Auth Recovery & Password Sync

> Reference Case Studies: `references/case-study-m211-recovery.md` (M211 wrong password recovery via Graph API OTP & single-writer lock), `references/case-study-m261-fake-password-and-canary-row-trap.md` (M261 data governance on fake password vs empty/None, remote Admin socket & anti-performative canary row selection), `references/case-study-m274-switcher-digit-collision-and-winrt-ocr-enforcement.md` (M274 switcher digit suffix collision bug fix, WinRT OCR primary enforcement to protect S7 CPU, and GPM profile OTP fallback).

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
7. **Bẫy OAuth Grant Expired (`AADSTS70000`) & Xử Lý Token Hết Hạn Sau >30-40 Ngày**:
   - Khi Hotmail/Outlook được cấp `refresh_token` từ lâu (sau >30–40 ngày không sử dụng), Microsoft Graph API có thể trả về lỗi:
     `AADSTS70000: The user could not be authenticated as the grant is expired. The user must sign in again.`
   - **Bẫy kẹt logic**: Trong `social_reg_v1.py` / `hotmail_provider.py`, khi phát hiện mail có `refresh_token`, script tự động áp dụng luật cứng "Đã có token Graph -> CẤM mở app Outlook trên điện thoại". Nhưng do token đã chết, Graph API không lấy được OTP, dẫn tới script treo chờ đủ 120s rồi fail timeout.
   - **Cách xử lý chuẩn xác**:
     * *Phương án ưu tiên*: Mở GPM / trình duyệt trên PC đăng nhập lại hòm thư Hotmail để refresh lại OAuth grant, cập nhật `refresh_token` mới vào cột 9 của `gmail_clean_v2.xlsx`.
     * *Phương án bypass tạm thời*: Xóa giá trị `refresh_token` đã chết trong `gmail_clean_v2.xlsx` về `None` (chỉ giữ `mail_pass`), runner sẽ nhận diện mail không có token và tự động kích hoạt fallback mở app Outlook trên thiết bị để đọc OTP.
     * *Phương án tự động hóa qua GPM Profile CDP (`read_otp_gpm.py`)*: Nếu hòm thư đã có profile trên GPM Login (cổng 19995), tích hợp `read_tiktok_otp_from_gpm_profile(email, timeout=90, exclude_codes=...)` làm fallback khi Graph API token hết hạn. Script khởi động profile qua CDP, bóc OTP 6 số trực tiếp từ web Outlook và tắt profile trong `finally`. **BẮT BUỘC** truyền `exclude_codes` để loại trừ các mã OTP cũ đã nhận trước đó trong hộp thư, tránh đọc lại mã hết hạn.
8. **Kỷ Luật Tác Phong Điều Phối Khi User Đã Lệnh Thực Thi ("Làm đi" / "Fix đi")**:
   - Khi user đã chỉ đạo rõ ràng ("Làm đi", "Fix đi", "Làm luôn"): CẤM TUYỆT ĐỐI dừng lại ở cuối turn để đặt câu hỏi xin phép lại ("Em tích hợp... nhé anh?", "Anh muốn làm phương án nào?").
   - BẮT BUỘC tự động chọn phương án tối ưu nhất và thực thi dứt điểm bằng code/script, đưa ra bằng chứng thực tế thay vì dừng lại xin phép lặp lại.
9. **Ép WinRT OCR Primary Chống Spam XML Dump Làm Treo/Offline Samsung S7**:
   - Các kịch bản legacy (`social_reg_v1.py` / `tiktok_login_v1.py`) chứa hơn 100 chỗ gọi `get_ui_xml()`. Việc spam Accessibility/UiAutomator Java liên tục trên thiết bị S7 cũ làm CPU Exynos 8890 quá tải 100%, văng lỗi `Killed 137` và làm crash daemon `adbd` trên điện thoại dẫn đến trạng thái thiết bị `offline` hoặc ngắt kết nối USB vật lý.
   - BẮT BUỘC cập nhật `find_text_tap` và `text_exists` trong runner đăng nhập sang WinRT OCR Primary: chụp màn hình (`screencap`) $\rightarrow$ bóc tách tọa độ chữ qua `automation_core.ocr.ocr_screen_boxes` trên PC $\rightarrow$ tap tâm nút `(cx, cy)`. Chỉ fallback sang XML khi OCR không thấy chữ.
   - Đảm bảo tuân thủ `INVARIANT UI-OCR-1` và vượt qua `python D:/Taadaa/tools/ui_policy_check.py`.
10. **Bẫy Fuzzy Match Account Switcher Lẫn Nick Khác Số Đuôi (`matches_switcher_identity`)**:
   - Trong `automation_core.tiktok.account_switcher.matches_switcher_identity`, logic `v1.rstrip("0123456789+ ") == v2.rstrip("0123456789+ ")` vô tình cắt bỏ toàn bộ số đuôi, khiến các tài khoản có cùng tiền tố chữ nhưng khác số (ví dụ: `khanhthu2275` vs `khanhthu1609`) bị coi là trùng khớp!
   - Hậu quả nghiêm trọng: Switcher tap nhầm vào nick có sẵn trên máy thay vì nhận diện thiếu nick để nạp bù, dẫn đến việc cày feed nhầm nick và cuối phiên báo lỗi `profile account mismatch`.
   - Khắc phục bắt buộc: Dùng regex kiểm tra số đuôi (`re.search(r"\d+$", v)`). Nếu cả hai giá trị đều kết thúc bằng số mà số đuôi khác nhau, BẮT BUỘC trả về `False` ngay lập tức.
11. **Bẫy OCR Méo Chữ Tiếng Việt và Bấm Nhầm Header Title Bar ($y < 220$)**:
   - Khi dùng WinRT OCR tìm nút bấm form (như "Tiếp tục"), chữ tiếng Việt dễ bị méo ký tự (ví dụ: `Tiếp tục` thành `'Tiép tvc'` do chữ `u` bị méo thành `v`). Dùng `norm_text` thô sẽ miss nút.
   - Đồng thời, màn hình `SignUpOrLoginActivity` có tiêu đề ở đỉnh màn hình ($y \approx 150$) mang chữ "Đăng nhập" (`'Däng nhäp'`). Nếu danh sách tìm kiếm có `"Đăng nhập"` (trong `tap_next`), hoặc OCR miss nút "Tiếp tục" và fallback sang box tiêu đề: script sẽ tap nhầm vào tiêu đề $y=154$ thay vì nút submit ở $y=1808$!
   - Hậu quả: Form email không được submit, script rơi vào vòng lặp `detect_after_continue=unknown` và timeout.
   - Khắc phục bắt buộc:
     1) Chuẩn hóa méo chữ: `.replace("tvc", "tuc")` trong hàm tìm kiếm OCR.
     2) Lọc bỏ tuyệt đối các box ở vùng đỉnh màn hình ($y_2 < 220$) khi tìm kiếm nút bấm hành động form.
     3) Trong `tap_next`, ưu tiên các từ khóa hành động cụ thể (`"Tiếp tục"`, `"Tiếp theo"`, `"Next"`, `"Continue"`) trước các từ khóa tiêu đề chung (`"Đăng nhập"`, `"Log in"`).
12. **Trễ Mạng ADB Remote Khi Lấy Thiết Lập Góc Xoay Màn Hình (`user_rotation` empty)**:
   - Khi chạy trên dàn máy cụm Admin qua ADB server remote (`192.168.110.119:5037`), ngay sau khi đánh thức màn hình (`wake_screen`), lệnh `settings get system user_rotation` có thể bị trễ một nhịp và trả về rỗng, khiến `device_prepare.py` ném lỗi `user_rotation: expected 0, got empty` và fail-closed ở giây thứ 10.
   - Khắc phục bắt buộc: Bọc retry loop với backoff `time.sleep(0.4)` trong `ensure_portrait_rotation` thay vì chỉ gọi 1 lần rồi ném lỗi ngay.
13. **Giải Phóng Tự Động Interstitial Popup "Follow Bạn Bè Của Bạn" Khi Preflight Profile**:
   - Khi chuyển sang tài khoản mới, TikTok có thể hiển thị trang toàn màn hình "Follow bạn bè của bạn" che khuất hoàn toàn thanh điều hướng dưới.
   - Khắc phục bắt buộc: Tích hợp `find_matching_handler` và tự động gọi `dismiss_follow_friends_suggestion_popup` ngay trong bước preflight guard (`_maybe_handle_profile_add_phone_guard`) trước khi đánh giá là `unknown state` hoặc chặn phiên.
14. **Forward Tham Số `exclude_codes` Trong Wrapper `read_tiktok_otp_from_gpm_profile`**:
   - Khi `social_reg_v1.py` fallback đọc OTP qua GPM profile, nó gọi:
     `read_tiktok_otp_from_gpm_profile(email, timeout=90, exclude_codes={"369520", ...})`
   - Bẫy: Hàm wrapper trong `D:/Taadaa/Tiktok_Reg/hotmail_provider.py` nếu chỉ nhận `(profile_id_or_email, timeout=120)` mà quên khai báo `exclude_codes=None` thì Python sẽ ném ngay:
     `TypeError: read_tiktok_otp_from_gpm_profile() got an unexpected keyword argument 'exclude_codes'`.
   - Khắc phục bắt buộc: Luôn khai báo `exclude_codes=None` ở chữ ký wrapper và chuyển tiếp trọn vẹn xuống `reader.read_tiktok_otp_from_gpm_profile(profile_id_or_email, timeout=timeout, exclude_codes=exclude_codes)` để loại trừ các mã OTP cũ đã nằm sẵn trong inbox.

