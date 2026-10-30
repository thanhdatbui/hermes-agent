---
name: gmail-account-automation
description: "Automation workflows for Gmail accounts on the Taadaa farm: Playwright + GPM Chrome, Singbox proxies, Google 2FA/OAuth, and Excel sync."
---
# Gmail Account Automation (Taadaa Farm)

- Chi tiết toàn bộ quy trình và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.

## Critical Operational Rules & Concurrency Safety
- **Anti-Stall & Action-First Execution Discipline (Chống Hứa Suông & Treo Phiên)**:
  - Khi phát hiện bug (ví dụ `fail_05_create` hoặc `GOOGLE_CREATE_ACCOUNT_BOUNCE_BACK`), CẤM Coordinator dừng lại ở cuối turn để nói lời hứa hẹn suông ("Em đang chuẩn bị đẩy bản patch...", "Anh chờ em vài phút...") mà KHÔNG gọi công cụ thực thi ngay trong cùng lượt.
  - Mọi turn phân tích lỗi BẮT BUỘC phải đi kèm công cụ patch, test và deploy thực tế; nếu cần chờ tiến trình batch nền, BẮT BUỘC dùng `terminal(background=True)` hoặc `process(action='wait')`.
- **Google Sign-In WebView Missing Node & WinRT OCR Architecture**:
  - Trên các máy Android 7 / Samsung S7 (đặc biệt là máy fresh 0 account cụm Admin), Google WebView thường bỏ sót (drop) các node UI tương tác khỏi cây ATX Accessibility XML (ví dụ: nút *"Tạo tài khoản"* / *"Create account"* và menu popup *"Dành cho mục đích cá nhân"*).
  - Không được dựa vào XML dump để kết luận nút không tồn tại. BẮT BUỘC gọi `automation_core.ui_extract.extract_ui` (WinRT OCR) đọc trực tiếp từ screenshot thật. Tọa độ calibrated chuẩn của nút Tạo tài khoản trên màn hình 1080x1920 là `(201, 1466)`.
- **False Bounce-Back Detection on Overlay Popup (`[05_personal]`) & Family Link Trap**:
  - Khi tap *"Tạo tài khoản"*, Google mở menu cá nhân dạng popup overlay đè lên WebView. Cây XML bên dưới vẫn còn chứa node `identifierId`.
  - Cơ chế dò menu cá nhân nếu thấy `identifierId` sau 4 giây KHÔNG ĐƯỢC vội ném lỗi `GOOGLE_CREATE_ACCOUNT_BOUNCE_BACK`, mà phải tap trực tiếp tọa độ menu cá nhân `(250, 1320)` (ngay phía trên nút Tạo tài khoản `(202, 1462)`).
  - **CẢNH BÁO TỌA ĐỘ**: Tuyệt đối không bấm cao ở `(350, 1180)` vì sẽ bấm trúng mục *"Dành cho trẻ em"* (Family Link "Cuộc phiêu lưu bắt đầu từ đây"), khiến luồng bị kẹt ở bước nhập email của phụ huynh!
  - Sau khi tap Tạo tài khoản, nếu màn hình đã nhảy sang màn nhập tên hoặc màn tiếp theo (có `firstName` hoặc `BẮT ĐẦU!`), BẮT BUỘC bỏ qua lệnh `must_tap_text("Dành cho mục đích cá nhân")` để tránh crash vì text popup đã biến mất.
- **Google Birthday & Gender Spinner Hint Traps (`[08_bday]` & `[08_bday_gender]`)**:
  - Trên WebView của Android 7 / Samsung S7, các dropdown chọn Tháng và Giới tính (`month`, `gender`) sau khi chọn qua DPAD hoặc popup picker thường KHÔNG xuất giá trị ra thuộc tính `text` hoặc `content-desc` trong XML node của Spinner.
  - Thay vào đó, Google WebView đưa giá trị đã chọn vào thuộc tính `hint` của Spinner (ví dụ: `hint="Tháng 10"`, `hint="Tháng 5"`, `hint="Giới tính <Nữ>"`).
  - Cả 2 hàm thẩm định `month_field_has_value` và `gender_field_has_value` BẮT BUỘC phải kiểm tra thuộc tính `hint` của Spinner và child nodes (dùng `strip_accents` và so khớp loose `Nữ`/`Female`/`Tháng N`), nếu chỉ quét `text` sẽ bị hiểu nhầm là chưa chọn và văng lỗi lặp `[08_bday_month]` hoặc `[08_bday_gender] Gender still empty`.
- **OneDrive Bridge Desync & Atomic Direct Insertion on Remote Code**:
  - Khi triển khai patch khẩn cấp sang máy phụ thuộc (như Admin-PC) qua OneDrive bridge (`D:\OneDrive\TaadaaData\admin\...`), tiến trình `OneDrive.exe` có thể bị nghẽn đồng bộ hoặc trễ vài phút khiến file trên máy đích vẫn giữ SHA256 cũ.
  - Coordinator BẮT BUỘC phải kiểm tra `Get-FileHash` trên máy đích trước khi copy vào repo chính.
  - Nếu OneDrive bridge chưa kịp sync hash mới, thay vì chờ đợi mù quáng, Coordinator có quyền dùng PowerShell chèn trực tiếp các dòng logic O(1) vào file remote (ví dụ: dùng `$list.Insert(...)` hoặc replace chuỗi chính xác) và kiểm tra lại hash ngay tại chỗ để kích hoạt batch mà không làm nghẽn phiên làm việc.
- **Admin Farm Full Disk D: (0.00 GB) & GDrive Offload Watchdog**:
  - Cụm Admin-PC khi đầy đĩa D: (0.00 GB do video render tích lũy trong `TIKTOK-videonuoinick-admin` lên tới ~600GB) sẽ khiến mọi lệnh I/O copy file, ghi log, UI dump bị văng lỗi `There is not enough space on the disk` hoặc sinh file 0 byte.
  - Script Task Scheduler `Taadaa_Sync_GDrive_Backup` (`start_sync_gdrive_hidden.vbs`) BẮT BUỘC phải đặt dòng chạy `manage_admin_media_gdrive.py offload 640` LÊN TRƯỚC dòng `sync_and_clean_gdrive.py`. Nếu để `sync_and_clean_gdrive` chạy trước, nó chỉ dọn video gốc khi thư mục đã đủ 45 video render, trong khi video render tích lũy hàng trăm GB không được đẩy đi, làm tê liệt toàn bộ đĩa D:. Luôn kiểm tra và chạy offload để giữ đĩa D: trống >= 20 GB.
- **Excel Concurrent Write Pitfall (Race Condition & Corruption)**:
  - Khi chạy 2FA GPM đa luồng, cấm gọi `openpyxl.save()` vào Excel master không có lock. Bắt buộc dùng `single_writer_workbook_update` hoặc rename qua `.tmp.xlsx`.
  - **Giải pháp**: Dùng filelock/single-writer queue hoặc ghi `.json` riêng rồi merge một lần.
- **CẤM Xóa Profile GPM khi Gmail DIE & Quy chuẩn Sheet Gmail_DIE_Archive**:
  - Xem chi tiết tại `references/gmail-die-recovery-and-no-delete-policy.md`. CẤM TUYỆT ĐỐI script tự động xóa profile GPM khi Gmail die (để bảo toàn tài khoản OpenAI/Codex đã ver số). Mọi tài khoản DIE tách riêng sang sheet `Gmail_DIE_Archive` trong `master_gmail_manager.xlsx`.
  - Luôn dùng `wait_until="domcontentloaded"` (cấm `networkidle` gây treo). Khi cần user nhập mã OTP, TUYỆT ĐỐI KHÔNG đóng profile/browser, giữ nguyên trên màn hình.
  - Chỉ ghi log ra file hoặc `sys.stderr`, tránh tràn thông báo Telegram.
- **Meta / Muse AI Age Verification & OIDC Automation**: Xem chi tiết tại `references/meta-muse-ai-age-verification-and-oidc-flow.md` về luồng nạp file selfie tự động `set_input_files`, bẫy OIDC expired state `Authentication failed`, và cơ chế xử lý geoblock waitlist trên `muse.ai`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.