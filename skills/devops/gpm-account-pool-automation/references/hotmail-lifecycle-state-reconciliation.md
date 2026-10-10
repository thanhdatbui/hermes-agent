# Hotmail Lifecycle State Reconciliation & Dual-OAuth Guard

Patterns for diagnosing and reconciling Hotmail/GPM lifecycle state between independent trackers and batch supervisor runners.

## 1. Nguyên nhân gây lệch State (State Drift)
- **Tool chạy độc lập ngoài Supervisor**: Khi chạy script lẻ (ví dụ `gpm_change_hotmail_security.py` can thiệp thủ công hoặc qua watchdog khác), kết quả thành công được ghi vào `hotmail_changed_tracker.json`, nhưng file state tổng của supervisor (`batch_gpm_5profiles_supervisor_state.json`) không tự biết, dẫn đến tài khoản vẫn mang trạng thái cũ (`CHANGE_INFO` / `BLOCKED`).
- **Lỗi kết nối hạ tầng tạm thời (Transient GPM Downtime)**: Khi GPM tắt máy (`WinError 10061: Connection refused`), các profile đang lookup/create bị đánh dấu `BLOCKED`. Khi GPM API online trở lại, các tài khoản này cần được unblock về `PENDING` và xóa `last_result` cũ để không bị báo cáo là lỗi vĩnh viễn.
- **Tài khoản chuyển Stage trước khi đủ điều kiện**: Trước khi có Dual-OAuth Gate (2026-10-08), các tài khoản ngâm đủ 7 ngày tự động nhảy lên `CHANGE_INFO`. Nếu chưa có Codex OAuth trên cả 2 server (:20129 và :20128), chúng bị chặn đổi pass hoặc fail. Cần trả về `WAIT_7D` (`WAITING`).

## 2. Quy trình Reconcile chuẩn (Standard Reconciliation Flow)
1. **Đối soát Tracker với State tổng**:
   - Quét `hotmail_changed_tracker.json` lấy danh sách `changed_emails`.
   - Nếu email đã đổi pass thành công trong tracker nhưng supervisor state != `DONE` / `COMPLETED`: Cập nhật ngay `stage = "DONE"`, `status = "COMPLETED"`.
2. **Kiểm tra Điều kiện Tiên quyết cho Stage `CHANGE_INFO`**:
   - **Chính sách cập nhật (2026-10-10)**: Bỏ kiểm tra Dual-OAuth Gate trên OmniRoute/9Router. Thay vào đó, kiểm tra 2 điều kiện cốt lõi:
     * `has_tiktok`: Đã có ID và PASS TikTok (đã reg TikTok thành công).
     * `has_chatgpt`: Đã có PASS CHATGPT (Cột 12 Master Excel) hoặc đã có timestamp `chatgpt_registered_at`.
   - Các tài khoản thiếu 1 trong 2 điều kiện trên bị giữ lại ở `WAIT_7D` (status `WAITING`), không đẩy lên `CHANGE_INFO`.
   - Không còn yêu cầu Dual Codex OAuth vì token Graph cũ sẽ bị xóa sạch khỏi Cột 9 sau khi đổi mật khẩu thành công.
   - **Đồng bộ Báo cáo 6h**: File báo cáo `cron_hotmail_gpm_lifecycle_6h_report.py` phải căn cứ theo `eligible_change_pass_count` (TikTok + ChatGPT) thay vì `dual_codex_eligible_count` để không báo lệch số lượng tài khoản sẵn sàng đổi pass.
3. **Phục hồi tài khoản kẹt hạ tầng**:
   - Kiểm tra `GPMClient.check_health()` hoặc endpoint `http://127.0.0.1:19995/api/v3/profiles`.
   - Nếu GPM đã 200 OK: Chuyển các tài khoản bị `BLOCKED` do `NewConnectionError` về `PENDING`, dọn `last_result = None`.

## 3. Tự động hóa chống hồi quy (In-Code Auto-Reconciliation)
Trong hàm `load_state()` của `batch_gpm_5profiles_supervisor.py`, luôn nhúng đoạn auto-reconcile:
```python
ch_tracker_path = STATE_PATH.parent / "hotmail_changed_tracker.json"
if ch_tracker_path.is_file():
    try:
        ch_map = json.loads(ch_tracker_path.read_text(encoding="utf-8")).get("changed_emails", {})
        ch_set = {c.strip().lower() for c in ch_map}
        for info in profiles.values():
            if (info.get("email") or "").strip().lower() in ch_set:
                info["stage"] = "DONE"
                info["status"] = "COMPLETED"
    except Exception:
        pass
```

## 4. Kiểm chứng hình ảnh lỗi Hotmail Login & Chống bẫy đổ lỗi nguồn bán (Gate 6 OCR)
- Khi Hotmail login báo fail: Không đoán mò lỗi proxy hay code.
- Dùng WinRT OCR đọc ảnh `outputs/screenshots/post_login_*.png`.
- Nếu có dòng `"Mật khẩu đó không đúng với tài khoản Microsoft của bạn"`:
  * **CẤM TUYỆT ĐỐI kết luận vội là lỗi mật khẩu từ shop bán** nếu chưa kiểm tra giá trị thực tế truyền vào form đăng nhập!
  * **Cạm bẫy Fallback nhầm Pass dịch vụ khác (Cross-Service Fallback Trap)**: Nếu tài khoản đã từng nhận OTP reg TikTok hoặc dịch vụ khác thành công mà login Hotmail web báo sai pass, nguyên nhân hàng đầu là **code lấy nhầm Pass TikTok (cột PASS) thay vì Pass Mail (cột PASS MAIL)** do fallback tai hại `info.get("mail_password") or info.get("password")`.
  * **Cạm bẫy State Desynchronization**: Kiểm tra xem state supervisor có bị giữ `mail_password` rỗng không được refresh từ Master Excel (`taikhoan_dat_v2_updated .xlsx`) hay không.
  * Chỉ khi đã xác minh 100% mật khẩu truyền vào form khớp đúng chuỗi ở cột `PASS MAIL` trong Master Excel mà Microsoft vẫn từ chối thì mới kết luận là sai mật khẩu gốc, và duy trì cooldown 48h để bảo vệ dải IP.

## 5. Truy vết tài khoản sai mật khẩu gốc (Root Cause & Procurement Forensics)
Khi phát hiện tài khoản báo sai mật khẩu ngay từ bước `HOTMAIL_LOGIN`, thực hiện quy trình điều tra 4 bước:
1. **Kiểm tra tính logic nghiệp vụ (Cross-Service Reality Check)**:
   - Nick đã reg TikTok hoặc nhận OTP thành công chưa? Nếu đã reg TikTok thành công, kiểm tra ngay mapping mật khẩu giữa cột `PASS` (TikTok) và cột `PASS MAIL` (Hotmail) trong Master Excel và state supervisor.
2. **Kiểm tra tính toàn vẹn của State Supervisor**:
   - Đối chiếu trường `mail_password` trong file state với cột `PASS MAIL` của Excel. Đảm bảo hàm `load_state()` luôn đồng bộ `mail_password` từ Excel vào state, và tuyệt đối cấm fallback sang `password` TikTok khi login Hotmail.
3. **Xác minh lịch sử đổi pass (`hotmail_changed_tracker.json`)**:
   - Nếu email vắng mặt trong `changed_emails` và supervisor state vẫn là `HOTMAIL_LOGIN` (`history: []`, `hotmail_login_at: None`): Khẳng định tài khoản **CHƯA TỪNG ĐỔI PASS**.
4. **Truy xuất đơn hàng & file Master (`taikhoan_dat_v2_updated .xlsx`)**:
   - Tra cứu vị trí Row, số Máy, Folder video, ID TikTok và mật khẩu gốc cột `PASS MAIL`.
   - Đối chiếu ngày nhập/ngày tạo: Các tài khoản Hotmail thường mua tự động từ shop `boxtaikhoan.com` (Loại 1 GraphAPI 262đ hoặc Loại 2 OAuth2 393đ qua API key `a0ed850f635d5c7042e89f68b41476bb`).
   - Đánh giá hạn bảo hành của Shop: Chính sách bảo hành sai pass của shop là **24 giờ** kể từ lúc mua (đơn hàng tự xóa sau 3 ngày). Nếu tài khoản mua từ 1–2 tháng trước phục vụ reg TikTok qua điện thoại thì đã hết hạn bảo hành; không thể khiếu nại shop. Cần đánh dấu cách ly hoặc thay thế mail mới khi cần nuôi web/Codex.

## 6. Cạm bẫy ảnh trắng chuyển hướng Microsoft Silent OAuth (White-Screen Transition Trap)
- **Hiện tượng**: Playwright / CDP báo login thành công, URL đạt `https://account.microsoft.com/auth/complete-client-signin-oauth-silent?state=...`, nhưng ảnh chụp màn hình nghiệm thu `post_login_*.png` chỉ có kích thước ~2KB, 1 màu trắng duy nhất (RGB single color), WinRT OCR không đọc được bất kỳ chữ nào.
- **Nguyên nhân**: Điểm kết thúc của luồng OAuth login Microsoft là URL redirect ngầm `complete-client-signin-oauth-silent`. Trong 1-2 giây chuyển tiếp này, DOM của trình duyệt hoàn toàn rỗng/trắng trước khi nhảy sang trang chủ `account.microsoft.com/account`. Nếu script chụp ảnh ngay khi URL vừa đổi sẽ chụp trúng khung hình trắng, vi phạm Gate 6 (ảnh mù/lỗi hiển thị).
- **Giải pháp xử lý (Mandatory Settling Guard)**:
  * Khi phát hiện URL chứa `complete-client-signin` hoặc `oauth-silent`: Bắt buộc gọi `page.wait_for_url(lambda u: "complete-client-signin" not in u, timeout=10000)` hoặc chủ động điều hướng sang `https://account.microsoft.com` với `wait_until="domcontentloaded"`.
  * Chờ tối thiểu 2-3 giây để giao diện Dashboard tải xong (hiện avatar/header/chữ "Tài khoản Microsoft").
  * Chỉ chụp ảnh sau khi màn hình đích thực sự hiển thị nội dung để đảm bảo OCR đọc được bằng chứng đăng nhập thành công.

## 7. Cạm bẫy Cookie Banner che màn hình & Đứt gãy luồng Relogin (Post-Signout Artifact Integrity)
- **Cạm bẫy MSN Redirect Race sau Sign Out Everywhere**: Gọi `/logout.srf` sau khi bấm Sign out everywhere trên Microsoft thường kích hoạt redirect race sang `https://www.msn.com/vi-vn`, làm văng lệnh `goto("https://login.live.com")` với lỗi navigation interrupted. Giải pháp: Tuyệt đối không dùng `/logout.srf`, điều hướng trực tiếp sang `https://login.live.com` kèm vòng lặp retry (2-3 lần) và xác minh URL domain hợp lệ trước khi thao tác form đăng nhập lại.
- **Cạm bẫy Cookie Consent Banner làm méo ảnh Checkpoint 5 (Dashboard)**: Khi vừa relogin vào `account.microsoft.com`, Microsoft thường đè một modal toàn màn hình "Quản lý tùy chọn cookie" ("Chấp nhận" / "Accept"). Nếu gọi `page.screenshot(full_page=True)` khi banner đang hiển thị, ảnh Dashboard sẽ bị kéo giãn, méo mép hoặc che khuất thông tin tài khoản (trông như ảnh bị lỗi/corrupted). Giải pháp: Bắt buộc tìm và click đóng/chấp nhận cookie banner trước (`button:has-text('Chấp nhận')`, `#acceptButton`), chờ 2-4 giây cho modal biến mất hoàn toàn rồi mới chụp viewport thông thường (không dùng `full_page=True` trên Dashboard SPA).

## 8. Đồng bộ Credential & Telemetry Observability khi lọc Candidate (Closeout Gate Lesson)
- **Tính nhất quán giữa Credential và Readiness Flag**:
  * Khi thay đổi nguồn kiểm tra readiness (ví dụ: chuyển từ OAuth sang cờ nghiệp vụ `has_chatgpt`), bắt buộc đảm bảo credential thực tế (`chatgpt_password`) và cờ readiness (`has_chatgpt`) cùng trích xuất từ một nguồn thống nhất (Cột 12 `PASS CHATGPT`).
  * CẤM TUYỆT ĐỐI để `chatgpt_password` fallback sang `PASS MAIL` trong khi `has_chatgpt` chỉ kiểm tra `PASS CHATGPT`. Điều này gây ra trạng thái bất nhất: tài khoản có mật khẩu nhưng cờ readiness lại là false, hoặc ngược lại.
- **Telemetry Observability cho Candidate Filtering**:
  * Khi bộ lập lịch `select_candidates()` loại bỏ tài khoản ở các stage chờ (`WAIT_7D`, `CHANGE_INFO`) do chưa đủ điều kiện `has_tiktok` hoặc `has_chatgpt`, BẮT BUỘC phát sự kiện structured telemetry `candidate_ineligible_skip` ghi nhận rõ `key`, `stage`, `has_tiktok`, `has_chatgpt`, `reason`.
  * Điều này đảm bảo tính quan sát (observability), giúp việc giám sát và debug nguyên nhân tài khoản bị giữ/bỏ qua trong pipeline hoàn toàn minh bạch qua telemetry mà không cần đọc mò file state/Excel.

## 9. Nguyên Tắc Phủ Kín Cả 2 Farm (Dual-Farm Coverage Invariant: Kibe 1-80 & Admin 201-280)
- **Quy tắc bất biến từ User**: Toàn bộ pipeline, cron, nạp tài khoản, supervisor vòng đời GPM/Hotmail và báo cáo định kỳ BẮT BUỘC phải chạy đồng thời cho CẢ 2 FARM (Kibe 1-80 và Admin 201-280), tuyệt đối không được cấu hình thiên vị hoặc bỏ quên Farm Admin!
- **Tách biệt Data Dir, State & Wrapper**:
  * Farm Kibe: `DATA_DIR = D:\OneDrive\TaadaaData\kibe`, state `D:\Taadaa\runtime\kibe\cron-state\batch_gpm_5profiles_supervisor_state.json`, cron `gpm-5profiles-lifecycle-supervisor` (chạy phút */5).
  * Farm Admin: `DATA_DIR = D:\OneDrive\TaadaaData\admin`, state `D:\Taadaa\runtime\admin\cron-state\batch_gpm_5profiles_supervisor_state.json`, cron `gpm-5profiles-supervisor-admin` (chạy so le phút 2,7,12,17...).
- **Xử lý bất đồng nhất schema Excel (Missing Column Guard)**:
  * Master Excel của Admin (`D:\OneDrive\TaadaaData\admin\taikhoan_dat_v2_updated .xlsx`) có thể khuyết cột hoặc ít hơn 12 cột so với Kibe.
  * Hàm `load_accounts()` bắt buộc kiểm tra biên mảng an toàn qua helper `_cell(col_name, fallback_idx)` với điều kiện `idx < len(row)`, cấm index trực tiếp `row[col.get("PASS CHATGPT", 11)]` gây crash `IndexError: tuple index out of range`.
- **Kỷ luật Proxy Mikrotik Farm**:
  * Dải IP Mikrotik PPPoE (`10001 - 10040`) là IP nội bộ của Farm. CHỈ dùng đăng nhập đúng tài khoản Hotmail của dàn máy farm đó. CẤM TUYỆT ĐỐI dùng ké dải IP này để đăng nhập các tài khoản ngoài farm / tài khoản thử nghiệm.
- **Hợp nhất Báo cáo 6h Toàn Farm**: Script `cron_hotmail_gpm_lifecycle_6h_report.py` bắt buộc đọc song song cả 2 state (`kibe` + `admin`), báo cáo tổng queue và chi tiết từng farm (Kibe 1-80 vs Admin 201-280).
- **Kế thừa biến môi trường Subprocess & Child Script Path Resolution**:
  * `batch_gpm_5profiles_supervisor.py` bắt buộc chạy `subprocess.run(argv, env=os.environ.copy())` để truyền cấu hình môi trường cụm (Kibe vs Admin) xuống tiến trình con.
  * Các script hạ tầng được gọi con như `gpm_change_hotmail_security.py` BẮT BUỘC đọc `GPM_SUPERVISOR_DATA_DIR`, `GPM_SUPERVISOR_ACCOUNT_XLSX`, `GPM_SUPERVISOR_STATE_PATH`, tuyệt đối không hardcode cứng đường dẫn `kibe` để tránh việc chạy `CHANGE_INFO` cho Admin nhưng lại đọc/ghi nhầm Excel và state của Kibe.

## 10. Kỷ Luật Dọn Dẹp & Quản Lý Pool ChatGPT Web Trong OmniRoute ("Ban Xóa DB Giữ GPM")
- **Phân loại triệt để HTTP 401**:
  * `AccountDeactivated` / `token_revoked`: Tài khoản bị OpenAI quét ban vĩnh viễn. Phải xóa dứt điểm khỏi bảng `provider_connections` trong `storage.sqlite` của OmniRoute để tránh kích hoạt Circuit Breaker 30 phút của pool `chatgpt-web`.
  * `Session Expired / No Token`: Tài khoản chỉ hết hạn cookie phiên trình duyệt (sau 7–14 ngày ngâm không tương tác). Tài khoản và mail vẫn sống 100%, chỉ cần re-login qua Playwright CDP và lấy cookie mới.
- **Quy tắc bất biến "Ban xóa DB giữ GPM"**:
  * Xóa tài khoản bị vô hiệu hóa khỏi CSDL OmniRoute, nhưng TUYỆT ĐỐI GIỮ NGUYÊN profile trên GPMLogin để bảo vệ hồ sơ máy và phục vụ các tác vụ tài khoản khác.
- **Tự động gắn Proxy khi đăng ký ChatGPT Web mới**:
  * Khi hàm `sync_registered_chatgpt_web_connection` thêm connection mới vào `provider_connections`, BẮT BUỘC kiểm tra và chèn bản ghi tương ứng vào `proxy_assignments` với một proxy đang hoạt động (`status NOT IN ('inactive','error','disabled','dead','down')`) từ bảng `proxy_registry`.

## 11. Kỷ Luật Proxy Mikrotik Farm vs Mobile Proxy Khi Re-login Web
- **Dải Mobile Proxy (`5101 - 5140`)**: Do lưu lượng farm hoạt động liên tục, dải IP này dễ bị OpenAI rate-limit khi bắt đầu luồng login web mới (`auth/error?error=undefined`). Tuân thủ nghiêm ngặt **GATE 6 & Anti-Insanity**: Khi gặp rate limit phải dừng ngay, đóng profile an toàn để tránh cháy proxy; tuyệt đối không chạy vòng lặp mù cố đấm ăn xôi.
- **Dải Mikrotik PPPoE (`10001 - 10040`)**: Residential dynamic IP sạch của gia đình, không bị OpenAI rate-limit form đăng nhập web. TUY NHIÊN, đây là IP độc quyền của dàn máy Farm: **CHỈ DÙNG để đăng nhập các tài khoản thuộc dàn máy đó**, tuyệt đối cấm dùng ké để thử nghiệm nick ngoài farm làm ảnh hưởng độ tin cậy của thiết bị thật.
