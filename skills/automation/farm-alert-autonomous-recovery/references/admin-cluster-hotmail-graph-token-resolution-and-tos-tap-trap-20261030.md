# Admin Cluster Hotmail Graph Token Dual-Workbook Resolution & Terms-of-Service Misclick Trap (30/10/2026)

## 1. Lệch File Workbook OAuth Token Trên Cụm Admin (Dual-Cluster Workbook Trap)
- **Hiện tượng:** Khi chạy `tiktok_login_v1.py` cho các máy Admin (M201–M280) dùng Hotmail loại 2 (đăng nhập qua mã OTP/Graph API), tiến trình bị timeout 420s (Fast Login) và 600s (Reconcile) dù hòm thư Hotmail hoàn toàn LIVE và có Refresh Token hợp lệ trong `admin/gmail_clean_v2.xlsx`.
- **Nguyên nhân gốc:**
  - Trong `D:/Taadaa/Tiktok_Reg/hotmail_provider.py`, hàm `resolve_graph_credentials(email)` mặc định chỉ đọc một file duy nhất:
    `workbook = str(Path(r"D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx"))`
  - Các tài khoản của dàn Admin nằm trong `D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx`.
  - Khi tra cứu token cho nick Admin (ví dụ `shackmierez11@hotmail.com`), hàm chỉ tìm trong file Kibe nên trả về `(None, None)` và ngộ nhận là mailbox không có token Graph.
- **Quy chuẩn sửa đổi (Candidate Iteration):**
  Trong `resolve_graph_credentials`, danh sách candidate workbooks bắt buộc phải duyệt qua cả hai cụm:
  ```python
  candidate_wbs = []
  if env_wb := os.environ.get("HOTMAIL_WORKBOOK"):
      candidate_wbs.append(Path(env_wb))
  if SOURCE_WORKBOOK:
      candidate_wbs.append(Path(SOURCE_WORKBOOK))
  candidate_wbs.extend([
      Path(r"D:/OneDrive/TaadaaData/kibe/gmail_clean_v2.xlsx"),
      Path(r"D:/OneDrive/TaadaaData/admin/gmail_clean_v2.xlsx"),
  ])
  ```
  Vòng lặp phải duyệt tuần tự: nếu tìm thấy email thì trả về `(tok, cid)`; chỉ trả về `(None, None)` sau khi đã quét toàn bộ các file mà không thấy.

---

## 2. Bẫy Tự Bấm Mở Webview "Điều Khoản Dịch Vụ" Trong `dismiss_android_permission_dialog`
- **Hiện tượng:** Khi app TikTok ở màn hình Login, script liên tục ghi nhận `[permission] dismiss Android permission dialog` và tap vào tọa độ `y > 3000` (ví dụ `y = 11319` hoặc `y = 5967`), mở ra màn hình `SparkActivity` (Webview "Điều Khoản Dịch Vụ | TikTok") và làm kẹt bot vĩnh viễn.
- **Nguyên nhân gốc:**
  - Hàm `_permission_dialog_xml(xml)` kiểm tra lỏng lẻo:
    `any(k in flat for k in ["tu choi", "deny"]) and any(k in flat for k in ["tep", "phuong tien", ...])`
  - Chân trang form đăng nhập TikTok có đoạn ghi chú: *"kết hợp Dịch Vụ... chúng tôi bảo lưu quyền từ chối cung cấp dịch vụ..."*. Đoạn này chứa cả cụm *"từ chối"* và từ *"tệp/dịch vụ"*.
  - `dismiss_android_permission_dialog` gọi `find_text_tap(device_id, "TỪ CHỐI", "Từ chối", "Tu choi")`. Hàm tìm thấy substring `"từ chối"` trong khối văn bản điều khoản dài ngoằng (bounds `[0, 1500][1080, 21138]`), tính tọa độ tâm `y = 11319` và tap vào đúng link Điều khoản dịch vụ.
- **Quy chuẩn khắc phục:**
  - Hộp thoại quyền Android (`PackageInstaller` / `PermissionController`) chỉ xuất hiện khi package foreground thực sự là hệ thống, KHÔNG phải `com.ss.android.ugc.trill`.
  - Bắt buộc kiểm tra `_permission_dialog_focused(device_id)` trước khi đọc XML, hoặc ràng buộc node bấm phải có bounds nằm trong vùng nhìn thấy được của màn hình (`y2 <= 1920`) và text của nút phải ngắn gọn (`len(text) <= 30`), cấm match substring trong các đoạn văn bản dài.

---

## 3. Kỷ Luật Đối Soát Cột Excel & Răn Đe Chống Ảo Giác Dữ Liệu
- **CẤM TUYỆT ĐỐI:** Không bao giờ dùng `row[i]` với các nhãn gán thủ công để vội vã kết luận "tài khoản không có dữ liệu / thiếu pass" báo cáo User khi chưa in header thật `ws.iter_rows(max_row=1)`.
- **Căn nguyên kiến trúc:** Excel không có schema cứng, việc truy cập theo số cột là nguồn cơn phát sinh lỗi liên tục. Hướng đi chiến lược dài hạn là di trú toàn bộ runtime farm sang SQLite tập trung (`farm_master.db`) có Data Access Layer (DAL) trả về Dataclass theo tên trường (`account.username`, `mailbox.oauth_refresh_token`), biến Excel thành lớp view-only export.

---

## 4. Kiến Trúc Tra Cứu SQLite Trực Quan Qua Web Dashboard Nội Bộ (`kibe:1905`)
- **Yêu cầu người dùng (UX Invariant):** Người vận hành không dùng DB Browser hoặc SQL CLI để tra cứu dữ liệu hàng ngày. Toàn bộ dữ liệu SQLite `farm_master.db` phải được tích hợp hiển thị trực tiếp lên Web Dashboard nội bộ `http://kibe:1905` (`D:/Taadaa/tools/tiktok_dashboard.py`).
- **Các thành phần bắt buộc:**
  1. **Tab "Sổ Cái Tài Khoản / Fleet Sổ Cái":** Hiển thị danh sách 160 máy (Kibe M1-M80, Admin M201-M280), click vào từng máy bung ra 8 slot tài khoản, username TikTok, pass, hòm thư Hotmail/Gmail, trạng thái Token OAuth (🟢 Live / 🔴 Expired), Proxy port MikroTik.
  2. **Thanh tìm kiếm nhanh O(1):** Tìm kiếm tức thì theo username `@...` hoặc email hòm thư trên toàn bộ 160 máy.
  3. **Nút Export Excel 1-chạm:** Cho phép người dùng tải ngay file Excel tổng hợp mới nhất (`*_VIEW.xlsx`) từ SQLite mà không khóa tiến trình runtime của bot.
