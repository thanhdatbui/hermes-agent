# Hotmail/GPM Lifecycle Supervisor & Intuitive Reporting Discipline

## 1. Nguyên tắc Trực quan hóa Báo cáo & Kỷ Luật Target Deliver (User Directive)
Khi viết script báo cáo định kỳ (như `cron_hotmail_gpm_lifecycle_6h_report.py`) cho pipeline GPM/Hotmail/ChatGPT:
- **Kỷ Luật Target Deliver của Cronjob Báo cáo (Chống Spam Chat Cá Nhân — Incident 2026-10-09):**
  - Mọi cronjob watchdog, báo cáo tiến độ, render/download report (như `farm-render-download-watchdog`, `hotmail-gpm-lifecycle-6h-report`, `cron_omni_activate_soaked_codex`) BẮT BUỘC phải đặt `deliver: "telegram:-5373649734"` (kênh Farm Alerts) hoặc `deliver: "local"`.
  - **TUYỆT ĐỐI CẤM** để `deliver: "origin"` cho các cronjob chạy tự động định kỳ! Việc để `origin` khiến hệ thống tự động xả các bản báo cáo farm dài hàng chục dòng vào cuộc trò chuyện DM riêng tư của User vào các khung giờ chạy định kỳ (như 00:00 đêm), làm gián đoạn luồng làm việc và khiến User nổi giận (*"gì thế, tự nhiên ném report vào đây?"*).
  - `deliver: "origin"` CHỈ dành riêng cho các job một lần (one-off) hoặc khi User chủ động yêu cầu gửi trực tiếp vào phiên hiện tại.
  - **Kỷ luật `no_agent = True` cho script cron:** Với các cronjob chỉ chạy script Python (quét DB, kích hoạt account, watchdog), bắt buộc bật `no_agent = True` để tránh bị Hermes ngắt do model drift và tiết kiệm 100% token LLM.

- **Kỷ Luật Tuyệt Đối Về Lệnh Dừng (Stop Signal Invariant & Cấm Lách Luật Bằng Bẫy "Canary"):**
  - Khi User đã chỉ đạo dừng một luồng (ví dụ: *"dừng chạy oauth ver số rồi mà"*), Agent BẮT BUỘC phải:
    1. Lập tức dừng 100% việc dispatch mới.
    2. Quét và kill sạch toàn bộ tiến trình nền (`Background process`, script Playwright, loop mua SIM/OAuth) đang chạy dở.
  - **CẤM TUYỆT ĐỐI** tự ý viện cớ *"chạy canary kiểm tra 1 nick"* hay *"test thử hàm mới sửa"* để tiếp tục kích hoạt lại các script của luồng vừa bị User yêu cầu dừng. Lệnh DỪNG của User có giá trị tối cao, thắng mọi nhu cầu kiểm chứng.
- **Tuyệt đối không bỏ qua các bước đầu phễu:** Bắt buộc hiển thị rõ rệt tình trạng **Hotmail Login** (Đã login thành công X/Total, Thất bại/Kẹt bao nhiêu).
- **Phân định rõ ràng giữa "Đang Cooldown" và "Cần Can Thiệp":**
  - **Đang trong Cooldown (Tự động thử lại):** Tách riêng số lượng nick đang ngâm (ví dụ: Hotmail login cooldown 48h, Codex cooldown 6h) để User biết hệ thống vẫn đang tự chạy, không hoang mang.
  - **Cần can thiệp:** Chỉ liệt kê chi tiết các nick đã hết cooldown hoặc bị kẹt/quarantine để User vào xử lý trực tiếp.
- **Tiến độ hoạt động 6h qua:** Tách rõ từng stage (Login, Reg, Codex, Change Info) có bao nhiêu lượt Thành công vs Thất bại.

## 2. Kỷ luật Dừng Hoàn Toàn Codex OAuth & Chuyển Trục Sang ChatGPT Web Pool
- **Chỉ thị dứt điểm (User Directive):** DỪNG HOÀN TOÀN toàn bộ luồng Codex OAuth (thuê số / ver phone 5SIM) trên dàn Hotmail GPM. Tuyệt đối KHÔNG cố thử lại Codex OAuth hay giữ trạng thái `WAIT_24_48H` để retry 5SIM.
- **Pipeline Chuẩn Mới (ChatGPT Web Pool Direct):**
  - `HOTMAIL_LOGIN` $\rightarrow$ `CHATGPT_REG` $\rightarrow$ **Đồng bộ Session vào `chatgpt-web-pool` (OmniRoute :20129)** $\rightarrow$ `WAIT_7D` (ngâm an toàn) $\rightarrow$ `CHANGE_INFO` $\rightarrow$ `DONE`.
  - Khi nick đăng ký ChatGPT thành công (`chatgpt_registered_at` có giá trị): Tự động trích xuất cookie session qua CDP và nạp vào provider `chatgpt-web` trên OmniRoute (:20129), sau đó chuyển thẳng sang `WAIT_7D`.
- **4 Bước Bắt Buộc Khi Chuyển Trục (Chống Bẫy "Dừng Nửa Vời"):**
  1. **Dọn sạch State (Zero Stale State):** Chạy script migration dọn toàn bộ các nick đang tồn đọng ở `WAIT_24_48H` / `CODEX_OAUTH` sang thẳng `WAIT_7D`. Đồng thời xóa bỏ `last_result` của stage `CODEX_OAUTH` và gỡ `BLOCKED/FAILED` về `WAITING` để không còn nick báo lỗi giả.
  2. **Khóa cờ trong Supervisor & Wrapper:** Đặt `ENABLE_CODEX_OAUTH = False` ở cả `batch_gpm_5profiles_supervisor.py` lẫn wrapper `gpm_5profiles_supervisor_wrapper.py`. `select_candidates()` phải bỏ qua mọi stage liên quan Codex.
  3. **Đồng bộ Anchor Ngâm 48h & Strict Email Matching (`cron_omni_activate_soaked_codex.py`):**
     - Mốc tính ngâm 48h để tự động bật `is_active=1` cho OmniRoute connection phải dùng `chatgpt_registered_at or codex_oauth_at`. Nếu chỉ giữ `codex_oauth_at`, các nick Web mới sẽ không bao giờ được kích hoạt vào `chatgpt-web-pool`.
     - **CẤM matching bằng substring thô:** Dùng `target in str(name).lower()` sẽ gây kích hoạt nhầm (ví dụ: `other_acc@hotmail.com` bị match nhầm khi target là `acc@hotmail.com`). Bắt buộc dùng regex tách email chính xác: `re.search(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", name)`.
     - **Transaction Rollback & Anti-Corruption:** Khi cập nhật `provider_connections` và bảng `combos`, bọc toàn bộ khối trong `try...except -> conn.rollback()` và validate JSON combo để tránh tình trạng kích hoạt dở dang khi dữ liệu bị lỗi.
     - **Configurable Paths qua ENV:** Dùng `os.environ.get("OMNI_DB_PATH", ...)` và `os.environ.get("SUPERVISOR_STATE_PATH", ...)` cho phép chạy unit test cô lập (hermetic) mà không động chạm database/state production.
  4. **Thanh lọc Báo cáo 6h (`cron_hotmail_gpm_lifecycle_6h_report.py`):** Xóa triệt để danh sách báo lỗi khống *"CODEX OAUTH — CẦN CAN THIỆP (217 nick)"*. Thay thế bằng khối **`CHATGPT WEB POOL (OMNIRoute :20129)`** hiển thị: Tổng kết nối Web, số lượng Active, Soaking (chờ ngâm 48h), và số model đang xoay tua trong pool. Phát sinh structured telemetry `[TELEMETRY] {"event": "hotmail_gpm_lifecycle_report_generated", ...}` để phục vụ giám sát tập trung.
- **Hotmail Login Cooldown:** Bắt buộc **giữ nguyên 48h** (theo chỉ thị cứng của User), không tự ý rút ngắn xuống 6h.
- **Tạm dừng các job liên quan đến 5SIM / Codex Phone:**
  - Tạm dừng cron quét giá `update-5sim-pools-6h`.
  - Khóa cờ `ENABLE_CODEX_OAUTH=False` trong supervisor để giải phóng hoàn toàn 5 worker slots cho việc login Hotmail, reg ChatGPT và đổi thông tin bảo mật.
- **Đồng bộ 3 Thư Mục Deploy Bắt Buộc:** Mọi chỉnh sửa script cron/watchdog phải sync đồng bộ 3 nơi: Kibe AppData, `Hermes/deploy/hermes-home/scripts/`, và `OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/`.

## 3. Quy tắc Đối soát Tài khoản Mua (Chống Báo Láo Lỗi Pass)
- **Tài khoản mua không bao giờ có chuyện sai mật khẩu:** Toàn bộ Hotmail nạp vào farm đều là tài khoản mua từ shop uy tín (`boxtaikhoan.com`) kèm OAuth token và mật khẩu chuẩn trong Master Excel (`taikhoan_dat_v2_updated .xlsx`).
- **Khi state báo pass rỗng hoặc login fail:**
  - Tuyệt đối CẤM kết luận bừa bãi là "lỗi pass / đổi pass".
  - Kiểm tra lệch chữ hoa/thường ở email (ví dụ: `alejadelainE@hotmail.com` trong Excel vs `alejadelaine@hotmail.com` trong State).
  - Kiểm tra logic cập nhật state (`load_state`): xem có filter nào chặn sync đè cột `mail_password` từ Excel vào state JSON hay không. Nếu có, đồng bộ lại mật khẩu chuẩn từ Excel vào State file.

## 4. Quy Trình Chuẩn Đổi Bảo Mật Hotmail & Bẫy "False Success" (Change Info Invariant)
- **Cảnh báo sống còn về Mail khôi phục rác (Getnada / fvia / smvmail / inboxes):**
  - **Tuyệt đối KHÔNG giữ lại mail khôi phục rác của bên bán để "làm lớp bảo mật":** Temp mail là public mailbox không có mật khẩu bảo vệ; bên bán hoặc bất kỳ ai biết email đều có thể đọc OTP để back nick bất cứ lúc nào qua "Quên mật khẩu", làm mất cả Hotmail, ChatGPT, Codex lẫn TikTok liên kết.
  - **Nguy cơ domain die / blacklist:** Domain rác thường xuyên bị thu hồi hoặc Microsoft chặn; nếu giữ lại, khi Microsoft hỏi OTP về mail đó sẽ kẹt vĩnh viễn.
  - **Tài khoản trắng thông tin an toàn hơn:** Khi tài khoản không có mail khôi phục, Microsoft cho phép bấm **"Bỏ qua / Lúc khác" (Skip/Next)** ở màn hình thêm thông tin bảo mật lúc login thiết bị khác.
- **BẪY NGUY HIỂM: "Tạm thời có lỗi với dịch vụ" & Session Cookie Ký Sinh:**
  - Khi form đổi mật khẩu hiện: *"Tạm thời có lỗi với dịch vụ. Xin vui lòng thử lại"* $\rightarrow$ **ĐÂY LÀ LỖI THẬT (Microsoft TỪ CHỐI đổi mật khẩu)**, tuyệt đối CẤM coi là false positive hay redirect thành công! Mật khẩu trên server vẫn là mật khẩu CŨ.
  - **Ảo giác Sign out everywhere:** Nút "Sign out everywhere" (Đăng xuất khỏi mọi nơi) của Microsoft thông báo mất tới 24h để thu hồi thiết bị khác, và **KHÔNG HỀ LÀM MẤT COOKIE của chính tab/browser hiện tại**!
  - **Bẫy Relogin giả:** Nếu sau đó điều hướng tới `https://account.microsoft.com/profile`, trình duyệt tự vào thẳng trang Profile nhờ cookie cũ từ Bước 1 mà **KHÔNG CẦN NHẬP LẠI MẬT KHẨU**, khiến script tưởng nhầm là đã đăng nhập thành công bằng mật khẩu mới!
- **Quy tắc Kiểm chứng Bắt buộc (Active Login Verification Invariant):**
  - Để xác nhận đổi mật khẩu thành công: BẮT BUỘC phải **Xóa sạch cookie (`context.clear_cookies()`)** hoặc mở context mới hoàn toàn.
  - Điều hướng tới `https://login.live.com/login.srf`, điền email và **gõ mật khẩu mới** vào `#passwordEntry, #i0118`.
  - CHỈ KHI Microsoft chấp nhận mật khẩu mới và đăng nhập thành công vào trang quản trị thì mới được xác nhận `SUCCESS` và ghi nhận vào Excel/State. Nếu Microsoft báo *"Mật khẩu đó không đúng..."* hoặc từ chối $\rightarrow$ Đánh dấu FAILED ngay lập tức, CẤM ghi đè mật khẩu mới vào Master Excel!
  - **Bài học xương máu chống báo cáo láo (Incident 2026-10-07):** Agent thấy form đổi pass redirect về trang profile, OCR thấy tên họ đầy đủ liền vội vàng commit/báo cáo pass đã đổi thành công. Khi User chất vấn "Lúc mày sign out xong login lại nếu xài pass mới nghĩa là đổi rồi chứ có gì đâu?", test thực tế xóa cookie nhập pass mới thì Microsoft báo đỏ *"Mật khẩu đó không đúng..."*. Bị User mắng xối xả *"Đkm đổi đéo đc dám báo là đổi thành công. Đkm có gate chặn báo cáo láo rồi vẫn đéo ăn thua vs mày phải không"*. KHẮC SÂU KỶ LUẬT: KHÔNG CÓ ADVERSARIAL RELOGIN TEST = KHÔNG CÓ BẰNG CHỨNG = CẤM BÁO THÀNH CÔNG!

## 5. Cơ Chế Microsoft Checkpoint "Verify your email" Khi Đổi Mật Khẩu (OTP Recovery Invariant)
- **Microsoft BẮT BUỘC OTP khi đổi mật khẩu:** Khi điều hướng tới `https://account.live.com/password/change`, sau khi nhập mật khẩu hiện tại, Microsoft **luôn yêu cầu bước xác minh danh tính 2FA/OTP** ("Verify your email" / "We'll send a code to...").
- **Phân loại nguồn Mail Khôi Phục để xử lý OTP (CẤM KÊU MAIL ẢO):**
  1. **Mail khôi phục domain riêng của bên bán (fviainboxes.com, smvmail.com...):**
     - **CẤM TUYỆT ĐỐI kết luận là "mailbox đóng / mail ảo / không đọc được":** Thực tế `fviainboxes.com` là dịch vụ tempmail có Web giao diện và API công khai 100%.
     - Endpoint danh sách thư: `GET https://fviainboxes.com/messages?username={username}&domain={domain}`
     - Endpoint chi tiết thư / OTP: `GET https://fviainboxes.com/message?username={username}&domain={domain}&id={id}`
     - Module tự động bốc OTP: `D:\Taadaa\Hotmail\scripts\mail_domain_otp_helper.py`. Khi Microsoft bắt xác thực mail khôi phục, gửi mã -> polling API lấy mã 6 số -> điền mã đổi pass bình thường.
  2. **Lô đơn hàng mới (Gói 129 / DongVanFB ID 57 — 5 trường có cột thứ 5 là mail khôi phục):** Sử dụng đúng hòm thư khôi phục trong đơn hàng (hoặc API của shop/domain tương ứng) để nhận mã OTP.
  3. **Tài khoản đã gán mail khôi phục chính chủ (`thanhdatbui1995@gmail.com`):** OTP gửi thẳng về hòm mail farm, nhận mã qua IMAP/Web để nhập vào form đổi mật khẩu.
- **Kỷ luật xử lý khi gặp Checkpoint không có Mail Khôi Phục:** Nếu tài khoản hoàn toàn trắng mail khôi phục (None) hoặc dính domain thực sự không có web/API mở, lập tức đánh dấu `BLOCKED: recovery_email_inaccessible`, dừng pipeline đổi mật khẩu cho nick đó, tuyệt đối không thử mò.

## 6. Kỷ Luật Điều Phối Supervisor Batch (5 Workers Song Song & Thứ Tự Ưu Tiên)
- **Thứ tự ưu tiên hàng đợi (Scheduler Priority):**
  - **Ưu tiên 1:** Stage `CHANGE_INFO` (các tài khoản đủ tuổi ngâm $\ge 7$ ngày VÀ thỏa mãn điều kiện Dual Codex OAuth) được xếp chạy trước mọi stage khác để chốt bảo mật sớm nhất.
  - **Ưu tiên 2:** Trong các tài khoản `CHANGE_INFO`, sắp xếp theo **số máy tăng dần (`M01 < M02 < M03...`)**, tức ưu tiên các dòng Row 1, 2... được reg TikTok lâu đời nhất cần bảo vệ trước.
  - **Ưu tiên 3:** OAuth emails, sau đó đến FIFO last attempt.

## 7. Khai Tử Hoàn Toàn Cron Đổi Pass S7 & Điều Kiện Đủ Change Pass Dual-Router (2026-10-08 Invariant)
- **Khai Tử 100% Cron Đổi Pass Trên S7 (User Directive):**
  - Toàn bộ cronjob đổi pass qua ADB trên điện thoại Samsung S7 (`night-hotmail-security-watchdog`, `m30-hotmail-retry-watchdog`) đã bị **XÓA BỎ VĨNH VIỄN**.
  - Toàn bộ việc đổi pass Hotmail, xóa mail khôi phục shop và Sign out everywhere **100% BẮT BUỘC chỉ chạy qua GPMLogin CDP** (`gpm_change_hotmail_security.py` / `batch_gpm_5profiles_supervisor.py`).
- **Điều Kiện Đủ Để Change Pass Hotmail (Dual Codex OAuth Invariant):**
  - Tài khoản Hotmail **CHỈ ĐỦ ĐIỀU KIỆN CHUYỂN SANG STAGE `CHANGE_INFO`** khi và chỉ khi thỏa mãn đồng thời:
    1. Đã ngâm đủ $\ge 7$ ngày (`WAIT_7D`).
    2. Đã reg Codex và có OAuth credentials trên **OmniRoute (:20129)** (`storage.sqlite` -> `provider_connections` có `provider='codex'`).
    3. Đã có OAuth credentials trên **9Router (:20128)** (`data.sqlite` -> `providerConnections` có `provider='codex'`).
  - **Fail-Closed Gate:** Bất kỳ tài khoản nào thiếu OAuth ở 1 trong 2 router thì **CẤM TUYỆT ĐỐI bốc chạy `CHANGE_INFO`**; tài khoản tiếp tục ở lại `WAIT_7D` chờ nạp đủ OAuth. Đổi pass trước khi nạp đủ OAuth sẽ làm đứt session, mất khả năng khai thác quota trên cả 2 LLM proxy.
- **Chuẩn Báo Cáo Tiến Độ (Delivered to Origin + Farm Alerts):**
  - Cronjob `hotmail-gpm-lifecycle-6h-report` được cấu hình deliver về cả topic Telegram nguồn và group Farm Alerts (`-5373649734`).
  - Bản tin bắt buộc hiển thị rõ: Tổng số nick trong Queue, Số nick có Codex trên OmniRoute, Số nick có Codex trên 9Router, Số nick đủ điều kiện Change Pass (thỏa mãn cả 2), Số nick đang ngâm và Số nick đã hoàn thành (DONE).
- **Phân trang GPM API:**
  - `list_profiles(per_page=100)` của GPM Local API chỉ trả trang 1. Với farm có >100 profile (hiện có >650 profiles), bắt buộc phân trang (`page += 1`) quét toàn bộ và ưu tiên match chính xác email của account trước khi fallback theo số máy.
- **Cooldown Anchor của `WAIT_7D`:**
  - Bắt buộc fallback: `anchor_str = info.get("hotmail_login_at") or info.get("codex_oauth_at") or info.get("chatgpt_registered_at")`. Nick nạp qua OAuth token không có trường `hotmail_login_at`; nếu không fallback sẽ bị kẹt vĩnh viễn ở `WAIT_7D`.
- **Dọn dẹp Cooldown & State tránh kẹt ảo:**
  - Khi unblock hoặc reset tài khoản sang `CHANGE_INFO`, phải xóa `CHANGE_INFO` khỏi `ip_action_history` (tránh bị dính cooldown 24h per proxy port) và xóa `last_result` (tránh dính cooldown 1800s).

## 6. Kỷ Luật File Lock Độc Quyền Khi Ghi Master Excel Trong Môi Trường Multi-Worker
- **Nguy cơ Race Condition phá hủy file Excel:**
  - Khi chạy 5 worker song song cùng lúc, nếu các worker hoàn thành gần nhau và đều gọi `wb = openpyxl.load_workbook(...)` rồi `wb.save(...)` vào cùng 1 file Master (`taikhoan_dat_v2_updated .xlsx`), các luồng ghi đè lên stream zip của nhau sẽ **phá hủy hoàn toàn file Excel** (`BadZipFile: Bad magic number for file header` hoặc `Bad CRC-32`).
- **Quy tắc bắt buộc khi ghi Master Excel:**
  - **File Lock độc quyền:** Bắt buộc bọc thao tác đọc-sửa-ghi file Excel qua `msvcrt.locking` (trên Windows) với timeout/retry để đảm bảo tại 1 thời điểm chỉ DUY NHẤT 1 tiến trình được phép mở và ghi file.
  - **Auto-backup trước khi save:** Trước mỗi lần `wb.save(WORKBOOK_PATH)`, bắt buộc copy file hiện tại sang file `.bak` dự phòng (hoặc ghi ra file `.tmp` trước rồi `os.replace` nguyên tử).
  - Khi file Excel bị hỏng: Ngay lập tức khôi phục từ bản backup mới nhất có đuôi `.bak_YYYYMMDD_HHMMSS` hoặc `.xlsx.bak` còn nguyên vẹn cấu trúc ZIP.

