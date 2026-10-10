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
