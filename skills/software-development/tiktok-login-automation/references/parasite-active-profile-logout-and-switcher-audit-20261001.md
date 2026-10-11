# Cạm bẫy đối soát tài khoản ký sinh: Active Profile vs Account Switcher & Quy trình Logout an toàn (2026-10-01)

## 1. NGUYÊN NHÂN LỌT LƯỚI TÀI KHOẢN KÝ SINH (PARASITE ACCOUNT TRAP)
- **Hiện tượng**: Script dọn dẹp tài khoản ký sinh (`watchdog_idle_parasite_reconcile.py`) kiểm tra máy M34, báo tài khoản ký sinh `@anillpboe98` (thuộc M56) "không còn trong switcher", ghi nhận `DONE`. Nhưng khi chạy ca nuôi Row 1, runner văng lỗi `ACCOUNT_MISSING: expected account was not found`.
- **Cơ chế UI TikTok**:
  - Khi mở Bottom-Sheet Switcher (`Chuyển đổi tài khoản`), TikTok **chỉ hiển thị các tài khoản phụ** có thể switch sang.
  - Nếu tài khoản ký sinh đang là **ACTIVE PROFILE** (tài khoản đang mở trực tiếp trên màn hình Hồ sơ chính), tên của nó hiển thị trên header/bio của Profile, **KHÔNG nằm trong danh sách switch của bottom-sheet**.
  - Logic cũ: Quét XML cây bottom-sheet switcher không thấy `@anillpboe98` $\rightarrow$ Kết luận nhầm là máy đã sạch $\rightarrow$ Bỏ qua. Thực tế nick ký sinh vẫn chiếm trọn 1 slot và đứng án ngữ ở Profile active suốt nhiều tuần!

---

## 2. QUY TRÌNH ĐỐI SOÁT 2 BƯỚC BẮT BUỘC (DUAL-SURFACE AUDIT)
Khi kiểm tra tài khoản trên máy (kể cả kiểm tra acc ký sinh hay kiểm đếm 8 slot):
1. **Bước 1 — Audit Active Profile**:
   - Vào tab Hồ sơ (`bounds: [864,1794][1080,1920]`).
   - Trích xuất handle qua XML (`resource-id` chứa `rz5`, `profile_header_name`, `account_name`) hoặc WinRT OCR.
   - Ghi nhận `active_account`.
2. **Bước 2 — Audit Switcher List (Kèm cuộn bottom-sheet)**:
   - Tap dropdown switcher (tên/avatar hoặc chevron `rv5`).
   - Cuộn bottom-sheet từ `[540, 1400]` lên `[540, 600]` để đọc hết các nick bị khuất.
   - Tổng danh sách tài khoản trên máy = `[active_account] + [switcher_sub_accounts]`.

---

## 3. QUY TRÌNH LOGOUT TÀI KHOẢN KÝ SINH ĐANG ACTIVE
### 🛑 CỔNG KIỂM TRA MÁY CHÍNH CHỦ TRƯỚC KHI LOGOUT (User chốt 2026-10-02)
- **Quy tắc bắt buộc**: Trước khi thực hiện logout nick ký sinh trên máy phụ, BẮT BUỘC kiểm tra thực tế trên máy chính chủ (`owner_stt`) xem nick đó ĐÃ CÓ MẶT VÀ ĐANG ĐĂNG NHẬP TRÊN MÁY CHÍNH CHỦ CHƯA (chụp ảnh Switcher/Profile máy chính chủ làm bằng chứng `MEDIA:<path>`).
- **Nguyên tắc quyết định**:
  * Nếu máy chính chủ **ĐÃ CÓ** nick: Cho phép logout nick ký sinh trên máy phụ để giải phóng slot.
  * Nếu máy chính chủ **CHƯA CÓ** nick: **CẤM TUYỆT ĐỐI LOGOUT** trên máy phụ vì sẽ làm mất phiên duy nhất của tài sản farm! Bắt buộc giữ nguyên phiên và báo cáo User.

### Các bước thực hiện logout nếu tài khoản cần đăng xuất đang là `active_account`:
1. **Không tìm trong Switcher**: Tuyệt đối không cố tap switcher để tìm nút logout của chính nó.
2. **Điều hướng Menu Cài đặt**:
   - Tap menu 3 gạch (`Profile menu`) tại góc phải trên: `tap(1005, 150)`.
   - Tap `Cài đặt và quyền riêng tư` (`Settings and privacy`): `tap(548, 1276)`.
   - Cuộn xuống đáy màn hình Cài đặt (vuốt 3-4 lần `[540, 1400]` $\rightarrow$ `[540, 400]`).
   - Tìm và tap `Đăng xuất` (`Log out`) tại toạ độ nút đỏ dưới cùng (`bounds` thường khoảng `y=1662`).
   - Xác nhận pop-up dialog: Tap `Đăng xuất` / `Log out` màu đỏ.
3. **Nghiệm thu giải phóng slot (Capture-before-cleanup)**:
   - Chờ app chuyển về màn hình tài khoản kế tiếp hoặc Profile.
   - Mở lại Switcher: Kiểm tra nút `+ Thêm tài khoản` (`Add account`) đã xuất hiện trở lại ở đáy bottom-sheet.
   - Chụp ảnh WinRT OCR xác nhận slot trống trước khi nạp tài khoản mới.

---

## 4. TRUY VẾT LỊCH SỬ REG GỐC KHI NICK TRÊN MÁY KHÔNG CÓ TRONG EXCEL (ROW OVERWRITE TRAP)
- **Hiện tượng**: Nick thực tế lưu phiên trên app (ví dụ `@gaetiwcu04c` trên M66) hoàn toàn không có trong `taikhoan_run_safe.xlsx` hay `taikhoan_dat_v2_updated .xlsx`.
- **Cấm đoán**: Tuyệt đối **CẤM GÁN NHÃN NICK RÁC** và cấm logout khi chưa điều tra lịch sử reg.
- **Phương pháp truy vết**:
  1. Tìm trong log reg tổng: `D:\Taadaa\Tiktok_Reg\social_reg_log.txt` theo handle hoặc tên hiển thị.
  2. Tìm trong kho artifact lưu kết quả reg gốc:
     `D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\<date>\batch_*\stt_<M>\tracking_result_stt<M>_<email>.json`.
  3. Đọc file JSON để lấy email đăng ký, pass mail, pass TikTok và ngày tạo.
- **Căn nguyên Row Overwrite**: Các đợt reg tài khoản mới trong quá khứ có thể đã ghi đè vào đúng hàng (row) của nick cũ trong file Excel, nhưng trên thiết bị Android app chưa từng logout nick cũ. Đây là **tài sản chính chủ hợp pháp của máy**, cần khôi phục thông tin vào Excel thay vì xóa phiên.

---

## 5. CẠM BẪY PARSER `find_column_indices` TRONG `logout_guard.py` (2026-10-02)
- **Hiện tượng**: Nick ký sinh rõ ràng thuộc máy khác trong Excel nhưng `evaluate_logout` trả về `code='UNRECORDED'` và từ chối cấp phép logout.
- **Nguyên nhân gốc rễ**: Header `"Folder Video"` chứa chữ `"id"` trong `"video"`. Logic `any(k in h for k in ("tiktok", "tik tok", "username", "id"))` match nhầm `"Folder Video"` làm `col_id` (chứa số folder như 167) thay vì cột `"ID"`, khiến guard đọc sai TikTok ID và ném lỗi `UNRECORDED` giả.
- **Giải pháp chuẩn**: Bắt buộc kiểm tra loại trừ:
  `(h == "id" or any(k in h for k in ("tiktok", "tik tok", "username"))) and "video" not in h and "device" not in h`.

---

## 6. KỶ LUẬT ĐIỀU PHỐI DỒN 8 NICK: LOGOUT GIẢI PHÓNG VỀ 7 NICK TRƯỚC KHI GỌI TIKTOK_LOGIN_V1 (2026-10-11)
- **Cơ chế ẩn nút của TikTok**: Khi TikTok app trên thiết bị đã đủ 8 nick lưu phiên, nút `Thêm tài khoản` (`Add account` / `Thêm tài khoản khác`) trong Bottom-Sheet Switcher bị TikTok **ẨN HOÀN TOÀN**.
- **Hiện tượng lỗi**: Nếu chưa logout nick dư/nick non mà đã vội chạy `python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <target>`, script mở Switcher nhưng không tìm thấy lối vào form login, dừng ở Bước 4 với lỗi:
  `✗ Không thấy: ('Thêm tài khoản', 'Add account', 'Thêm tài khoản khác')` $\rightarrow$ cuộn 3 lần vô ích $\rightarrow$ `STOPPED: [adb-timeout] UI_XML_TIMEOUT detail=deadline-exceeded`.
- **Thứ tự thực thi bất di bất dịch (Lockstep)**:
  1. Chọn nick non nhất cần điều chuyển (reg mới nhất, ít video nhất).
  2. Bật 2FA TOTP & đặt mật khẩu TikTok mới cho nick đó ngay trên máy nguồn (chống mất phiên / mất tài sản farm).
  3. Ghi nhận đầy đủ thông tin vào sổ sách máy nhận (chưa vội login lên máy nhận).
  4. **BẮT BUỘC ĐĂNG XUẤT NGAY** nick non khỏi máy nguồn qua menu *Cài đặt và quyền riêng tư > Đăng xuất* để đưa số nick trên máy về 7.
  5. Mở lại Switcher xác nhận nút `Thêm tài khoản` đã hiển thị trở lại.
  6. Mới được phép gọi `tiktok_login_v1.py` để đăng nhập nick đích vào máy nguồn.

---

## 7. CẠM BẪY CUỘN BOTTOM SHEET SWITCHER & THOÁT MÀN HÌNH CÀI ĐẶT COMPOSEVIEW (2026-10-12)
- **Lỗi `ACCOUNT_NOT_IN_SWITCHER` do thiếu method `swipe()` trong Adapter**:
  - Khi máy có 7-8 nick, nick tạo muộn nhất (vị trí 7-8) nằm dưới nếp gấp (fold) của Bottom-Sheet Switcher.
  - Các adapter gọi qua `canonical_account_switcher` (như `_CanonicalAdapter` trong runner 2FA) BẮT BUỘC phải implement method `swipe(self, x1, y1, x2, y2, duration_ms=300)` gọi `adb shell input swipe`. Nếu thiếu `swipe`, `getattr(adapter, "swipe", None)` trả về `None` khiến switcher ném ngay lỗi `ACCOUNT_MISSING` / `ACCOUNT_NOT_IN_SWITCHER` mà không chịu cuộn tìm nick.
- **Biên độ cuộn chuẩn cho Switcher và độ trễ chờ UI settle**:
  - Trên Galaxy S7 (1080x1920), Bottom-Sheet Switcher gần như full màn hình (`[0,96][1080,1920]`).
  - Vuốt biên độ nhỏ (400px: 1500 $\rightarrow$ 1100) chỉ dịch chuyển ~1.8 dòng nick, không đủ làm lộ nút `Thêm tài khoản` hoặc nick cuối.
  - Biên độ chuẩn: từ 80% chiều cao màn hình lên 40-50% (ví dụ `540, 1536` $\rightarrow$ `540, 800`..`960`, duration 450ms).
  - BẮT BUỘC `time.sleep(2.0)` sau khi vuốt để animation dừng hẳn trước khi redump XML; redump dưới 1s sẽ dính XML cũ hoặc làm nghẽn `atx-agent`.
- **Cấm bấm phím BACK sau khi Switch nick**:
  - Trên TikTok v47, sau khi tap chọn nick trong Switcher, app tự đóng bottom sheet. TUYỆT ĐỐI KHÔNG gửi phím BACK (`keyevent 4`) vì sẽ làm thoát văng TikTok ra Launcher Android.
  - Luôn điều hướng bằng cách tap trực tiếp tab Hồ sơ (`bounds: [864,1794][1080,1920]`) $\rightarrow$ tap Menu 3 gạch (`[1005, 150]`) $\rightarrow$ tap Cài đặt và quyền riêng tư.
- **Tự động thoát màn hình Cài đặt con (Jetpack ComposeView)**:
  - Màn hình Cài đặt TikTok v47 viết bằng `ComposeView`, không có thanh điều hướng bottom nav.
  - Trong hàm `go_to_profile`, nếu phát hiện text `cai dat va quyen rieng tu` hoặc icon `quay lai man hinh truoc`, BẮT BUỘC gửi `keyevent 4` (BACK) để đưa app về lại màn hình chính có bottom nav trước khi cố tap tab Hồ sơ.

---

## 8. CẠM BẪY BẪY WEBVIEW SPARKACTIVITY ("THỜI GIAN SỬ DỤNG MÀN HÌNH") (2026-10-12)
- **Hiện tượng**: Script login hoặc go_to_profile chạy loop mãi nhưng không tìm thấy tab Profile hay Switcher, `atx-agent` dump XML chỉ thấy thanh trạng thái Android (`com.android.systemui`), toàn bộ phần dưới trống trơn.
- **Nguyên nhân gốc rễ**: Khi script cuộn trang Cài đặt hoặc mở app, vô tình chạm vào mục "Thời gian sử dụng màn hình" (Screen Time / Wellbeing). Màn hình này chạy dạng Hybrid Webview của ByteDance: `com.bytedance.hybrid.spark.page.SparkActivity`. Do là Webview nội bộ, accessibility tree native không render các thành phần con. `open_app` thấy package TikTok trong foreground nên không relaunch, còn `go_to_profile` bấm tab Profile (972, 1857) vô tác dụng vì SparkActivity không có bottom nav.
- **Giải pháp xử lý**:
  1. Kiểm tra `mCurrentFocus`: nếu chứa `SparkActivity` hoặc `SettingContainerActivity`, BẮT BUỘC bấm phím BACK (`keyevent 4`) 1-2 lần để thoát webview quay về trang chính.
  2. Trước khi chạy các flow quan trọng như `tiktok_login_v1.py`, nên force-stop app sạch (`am force-stop com.ss.android.ugc.trill`) để đảm bảo khởi động từ `MainActivity`, tránh bị dính activity webview rác từ phiên trước.

---

## 9. KỶ LUẬT TUẦN TỰ KHI CƠ CẤU / CHUYỂN NICK TRÊN MÁY KỊCH 8 SLOT (User chỉnh đốn 2026-10-12)
- **Quy tắc tuyệt đối**: Tuyệt đối không nhảy cóc hoặc cố chạy `tiktok_login_v1` khi nick cần chuyển đi chưa được đăng xuất hoàn tất!
- **Thứ tự 4 bước bắt buộc**:
  1. **Bước 1**: Bật 2FA TOTP & khởi tạo mật khẩu chuẩn cho nick chuyển đi ngay trên máy hiện tại.
  2. **Bước 2**: Ghi nhận Secret Key 2FA + Pass vào Master DAT / sổ sách máy nhận.
  3. **Bước 3**: **ĐĂNG XUẤT NGAY** nick đó khỏi máy hiện tại để hạ danh sách Switcher xuống đúng 7 nick. Soi mắt ảnh Switcher xác nhận nick đã biến mất và slot đã trống.
  4. **Bước 4**: Mới được phép gọi script đăng nhập nạp nick mới vào máy. Cấm đốt cháy giai đoạn.

---

## 10. KỸ THUẬT LOGOUT KHI NICK LÀ ACTIVE PROFILE & NÚT THÊM TÀI KHOẢN MÁY 7 NICK (2026-10-12)
- **Cạm bẫy đóng Switcher khi nick là Active Profile**:
  - Khi nick cần logout đang là Active Profile, mở Switcher sẽ KHÔNG thấy tên nick.
  - CẤM tap tọa độ mù `(540, 200)` để đóng Switcher vì trên màn hình Samsung S7 (1080x1920), bottom sheet kéo dài từ `y=96` đến `y=1920`, tọa độ `(540, 200)` vẫn nằm trong header của Switcher $\rightarrow$ Switcher KHÔNG đóng.
  - Các thao tác tap menu tiếp theo sẽ chạm lệch vào các item trên Profile, kích hoạt webview `SparkActivity` ("Thời gian sử dụng màn hình") và gây nghẽn toàn bộ luồng.
  - **Quy chuẩn**: BẮT BUỘC dùng phím **BACK (`keyevent 4`)** để đóng Switcher, sau đó tap `Menu hồ sơ (3 gạch)` tại `(1005, 150)`.
- **Tọa độ chuẩn vào Cài đặt và Đăng xuất**:
  - Tại Menu hồ sơ: tap `Cài đặt và quyền riêng tư` tại `(621, 1278)` (`rid='com.ss.android.ugc.trill:id/dui'`).
  - Trong trang Cài đặt: cuộn 5-6 lần xuống đáy (`540, 1600` $\rightarrow$ `540, 400`).
  - Bấm nút `Đăng xuất` màu đỏ ở đáy: Cần matcher đa thuộc tính `(text + " " + content-desc)` chứa `["đăng xuất", "dang xuat", "log out"]` vì trên TikTok v47 chữ thường nằm trong `content-desc`. Tọa độ fallback kết hợp: `(300, 1640)` và `(540, 1750)`.
  - Khi popup xác nhận xuất hiện: kiểm tra `resource-id` chứa `["a6d", "a6e", "button1"]` hoặc text/desc chứa `"đăng xuất"` với bounds `[48,...` / `[0,...`. Bấm nút xác nhận màu đỏ tại `(540, 1640)` (fallback phụ `(750, 1100)`). CẤM tap mù một tọa độ khi chưa kiểm tra cả text lẫn content-desc.
- **Tọa độ nút "Thêm tài khoản" khi máy có 7 nick**:
  - Khi máy có 7 nick, nút "Thêm tài khoản" (`com.ss.android.ugc.trill:id/ls_`) nằm kịch sàn ở mép đáy màn hình tại tọa độ `(540, 1850)` (bounds `[0,1788][1080,1920]`).
  - Phần text con (`com.ss.android.ugc.trill:id/ndk`) bị lẹm mép dưới nên matcher text XML có thể bỏ sót.
  - Handler trong `social_reg_v1.py` cần tap thẳng tọa độ `(540, 1850)` và kiểm tra modal đăng nhập xuất hiện trước khi thực hiện cuộn hoặc fallback.

---

## 11. BẪY EXIT CODE 1 `TRACKING_ROW_CHANGED` KHI NẠP NICK VÀ XỬ LÝ DEAD LOCK (2026-10-12)
- **Hiện tượng `TRACKING_ROW_CHANGED`**:
  - `tiktok_login_v1.py` đã vượt qua 2FA TOTP, vào đến Home feed và Profile xác nhận `@<username>` thành công (`[profile] handle=@...`).
  - Tuy nhiên ở bước ghi nhận sổ sách `upsert_tracking_account`, script phát hiện dòng dữ liệu bị lệch/thay đổi (`TRACKING_ROW_CHANGED`) và dừng lại với `exit code 1`.
  - **Kỷ luật điều phối**: Coordinator CẤM TUYỆT ĐỐI chỉ nhìn vào `exit code 1` mà kết luận login thất bại rồi chạy lại từ đầu. BẮT BUỘC đọc log kiểm tra xem đã xuất hiện marker `[login-success]` và `[profile] handle=@...` chưa. Nếu nick đã vào máy thành công, chỉ cần cập nhật lại dòng sổ sách tương ứng thay vì lặp lại thao tác UI.
- **Xử lý Dead Lock khi Background Process bị ngắt**:
  - Khi tiến trình chạy nền hoặc subagent thao tác ADB qua `with_device_lock.py` bị timeout/kill, file lock trong `.codex/device-locks/` có thể bị kẹt lại trạng thái `owner_dead`.
  - Các lệnh gọi ADB tiếp theo trên máy đó sẽ bị treo 300s chờ lock.
  - **Quy chuẩn**: Trước khi retry bất kỳ thao tác thiết bị nào sau khi tiến trình nền kết thúc/timeout, BẮT BUỘC chạy `python "D:/Taadaa/tiktok-luot nuoi acc/scripts/reap-dead-owner-locks.py"` để dọn dẹp các dead-owner lock.
- **Cờ `--verify-only` cho script logout**:
  - Script điều tra như `do_logout_account.py` cần hỗ trợ cờ `--verify-only` để chỉ mở Switcher chụp ảnh nghiệm thu (`verify()`) mà không chạy lại toàn bộ quy trình logout.

