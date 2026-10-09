# Hướng dẫn xử lý Nick ký sinh (2 máy nuôi chung 1 nick) & Kỷ luật Watchdog

## 1. Bản chất sự cố "Nick ký sinh" (Parasitic Account Duplication)
- **Hiện tượng**: Một tài khoản TikTok (thường do lỗi cấp trùng mail Hotmail/Gmail từ trước) được đăng nhập đồng thời trên 2 máy khác nhau.
- **Hệ quả nghiêm trọng**:
  1. 2 máy cùng tương tác nuôi chung 1 nick dẫn đến hành vi bất thường, nguy cơ TikTok shadowban hoặc checkpoint tài khoản.
  2. Máy bị "nhận vơ" nick (máy ký sinh) bị đẩy tổng số nick lên trần cứng 8 tài khoản -> ẩn nút "Thêm tài khoản" (Add account) -> crash flow reg bù slot thiếu (`fail_04_add_account`).
  3. Trong Excel, máy ký sinh có thể vẫn hiển thị thiếu (Slot = None) hoặc bị copy đè trùng lặp nick cũ, khiến coordinator hiểu lầm là thiếu nick.

## 2. Quy trình 6 bước Logout dứt điểm Nick ký sinh qua UI
Tuyệt đối không dùng `pm clear` (sẽ xóa sạch toàn bộ 7 nick còn lại trên máy). Phải thực hiện logout chọn lọc qua UI:

1. **Mở Switcher & Chuyển sang nick ký sinh**:
   - Mở app TikTok: `reg.open_app(dev)`.
   - Mở sheet Chuyển đổi tài khoản: `reg.open_account_dropdown(dev)`.
   - Tìm node chứa username ký sinh trong XML (qua `content-desc` hoặc `text`).
   - Tap vào tọa độ tâm của node để TikTok chuyển active account sang nick ký sinh (`wait=8s`).

2. **Vào màn hình Profile của nick ký sinh**:
   - Tap Profile tab: tọa độ chuẩn `(972, 1857)` (hoặc tìm node có `content-desc="Hồ sơ"`).
   - Đảm bảo header hiển thị đúng `@username` của nick ký sinh.

3. **Mở Menu hồ sơ & Cài đặt**:
   - Tap Menu 3 gạch (top-right): `(1005, 150)` hoặc tìm `content-desc="Menu hồ sơ"`.
   - Trong bottom sheet/menu, tìm và tap `Cài đặt và quyền riêng tư` (resource-id hoặc text). Tọa độ thường gặp: `(621, 1248)`.

4. **Cuộn xuống đáy trang Cài đặt**:
   - Thực hiện vuốt ngược từ dưới lên 5-6 lần: `adb shell input swipe 540 1600 540 300 300`.
   - Dump UI XML để tìm node text hoặc desc chứa `"Đăng xuất"` (hoặc `"Log out"`).
   - Tap nút `Đăng xuất` (tọa độ thường gặp: `(540, 1668)`).

5. **Xác nhận popup Đăng xuất**:
   - TikTok sẽ hiện bottom sheet: *"Bạn có chắc chắn muốn đăng xuất?"*.
   - Tìm nút `Đăng xuất` trên sheet (resource-id chứa `a6e` hoặc bounds `[48, 1632][1032, 1692]`).
   - Tap xác nhận: `(540, 1662)` và chờ `6s` để TikTok xử lý logout và tự động chuyển sang nick khác.

6. **Nghiệm thu bắt buộc (Verification Gate)**:
   - Mở lại dropdown Switcher: `reg.open_account_dropdown(dev)`.
   - Xác nhận:
     1. Nick ký sinh không còn trong danh sách tài khoản.
     2. Nút `"Thêm tài khoản"` (Add account) đã xuất hiện trở lại.
   - Chụp screencap bằng chứng: `adb exec-out screencap -p > report.png` và đính kèm `MEDIA:<path>`.
   - Force-stop app và đưa máy về HOME (`keyevent 3`).

## 3. Bẫy Ngộ Nhận "Đã Hết Ký Sinh" Khi Chỉ Nhìn Excel PASS & Danh Sách 14 Cặp Nick Reg Trùng Lịch Sử
- **Bản chất khiến "cứ vài ngày lại lòi ra 1 acc"**:
  1. `excel_preflight_validator.py PASS 100%` chỉ chứng minh trong các file Excel không có dòng nào trùng lặp. Nó **hoàn toàn không chứng minh** trên thiết bị thật đã sạch nick ký sinh!
  2. Toàn bộ nick ký sinh trên farm bắt nguồn từ một tập hữu hạn: **14 tài khoản bị bốc trùng email Hotmail** trong các batch reg cũ ngày 25–26/08/2026 (`artifacts/runs/social-batch-all/*/tracking_result_*.json`) do chạy đa luồng chưa có khóa phân bổ mail thời gian thực.
  3. Khi sửa Excel gán cho 1 máy chính chủ, máy phụ vẫn âm thầm ngậm phiên trên app TikTok. Hàng ngày máy phụ vẫn lướt feed bình thường nên không ai biết. Chỉ đến khi có đợt reg bù mở Switcher chạm trần 8 nick (`MACHINE_FULL_8_ACCOUNTS`) thì lỗi mới phát tác.
  4. **CẤM TUYỆT ĐỐI** khẳng định "farm đã sạch ký sinh" khi chỉ dựa vào Excel/DB mà chưa kiểm tra thực tế và có ảnh Switcher hiện nút "Thêm tài khoản" trên thiết bị.

- **Bảng 14 Cặp Nick Bị Reg Trùng Lịch Sử Toàn Farm**:
  1. `@miumiu67971`: Máy chính = M5 (Slot 7), Máy phụ ký sinh = **M3**
  2. `@verdhsclf6f`: Máy chính = M16 (Slot 5), Máy phụ ký sinh = M40 (Đã out)
  3. `@gabruync3o9`: Máy chính = M40 (Slot 6), Máy phụ ký sinh = **M19**
  4. `@rillecoq5ml`: Máy chính = M21 (Slot 7), Máy phụ ký sinh = **M11**
  5. `@jomegbym8n8`: Máy chính = M51 (Slot 6), Máy phụ ký sinh = **M24**
  6. `@yanesbgvmuq`: Máy chính = M26 (Slot 5), Máy phụ ký sinh = **M42**
  7. `@phamnhi1770`: Máy chính = M30 (Slot 7), Máy phụ ký sinh = M75 (Đã out)
  8. `@lebaothao8787`: Máy chính = M33 (Slot 6), Máy phụ ký sinh = **M69**
  9. `@anillpboe98`: Máy chính = M56 (Slot 4), Máy phụ ký sinh = **M34**
  10. `@cyennffqko8`: Máy chính = M36 (Slot 8), Máy phụ ký sinh = M76 (Đã out 02/10)
  11. `@thleyzilkva`: Máy chính = M37 (Slot 5), Máy phụ ký sinh = **M13**
  12. `@annapmfdh0a`: Máy chính = M44 (Slot 6), Máy phụ ký sinh = M28 (Đã out)
  13. `@chichi13853`: Máy chính = M26 (Slot 6), Máy phụ ký sinh = **M53**
  14. `@anggiathinh2905`: Máy chính = M28 (Slot 5), Máy phụ ký sinh = M61 (Đã out)
  *(Kèm 1 nick M32 `@thanhlee372` có máy chính là M37)*.

## 4. Kỹ Thuật Điều Hướng Switcher & Bẫy Cố Định Tọa Độ / ATX HTTP 500
- **Bẫy atx-agent HTTP 500 / uiautomator treo**:
  * Khi máy S7 tải nặng hoặc service uiautomator bị kẹt, gọi dump hierarchy qua port 7912 thường trả về `HTTP 500 Internal Server Error` hoặc timeout 90s.
  * **Giải pháp chuẩn**: Sử dụng pipeline **Screencap + Windows Native OCR (WinRT OCR)** (`tools/fast_parasite_scanner.py`). Chụp ảnh kéo về PC rồi chạy `winrt_ocr.py <img_path> --boxes` để trích xuất text và tọa độ center `(cx, cy)` trong < 1s, hoàn toàn miễn nhiễm với lỗi crash uiautomator.
- **Bẫy nghẽn USB ADB khi chạy song song (Parallel ADB Concurrency Trap)**:
  * Khi quét và dọn nick ký sinh đồng thời trên nhiều máy (`run_parallel_parasite_scan.py` qua `ThreadPoolExecutor`):
  * **Nguy cơ**: Các lệnh shell ngắn như `input keyevent 4` hoặc `input tap` dễ bị timeout nếu đặt timeout quá thấp (5s) do xung đột bus USB hoặc hàng đợi ADB daemon bị nghẽn.
  * **Kỷ luật cấu hình**:
    1. BẮT BUỘC đặt ADB command timeout tối thiểu 15s - 20s (`timeout=15..20`).
    2. Giới hạn `max_workers` ở mức 4 - 6 luồng đồng thời; nếu gặp timeout cục bộ, retry ngay với thread pool 2 luồng (`max_workers=2`) để tránh nghẽn hub USB.
- **Bẫy lệch tọa độ tab Hồ sơ (Profile)**:
  * Tọa độ `(972, 1857)` nằm ở viền trên khung tab Hồ sơ (`[864, 1864][1080, 1903]`), dễ bị hụt click trên nhiều máy Samsung S7.
  * **Tọa độ chuẩn xác**: `(972, 1883)`.
- **Bẫy Switcher nông (Fold truncation)**:
  * Switcher mặc định chỉ hiện 7 account. Account thứ 8 hoặc nút "Thêm tài khoản" bị ẩn dưới mép màn hình.
  * BẮT BUỘC thực hiện vuốt nhẹ bottom sheet lên: `adb shell input swipe 540 1500 540 1000 300` trước khi chụp ảnh nghiệm thu. Chỉ được coi là sạch khi ảnh OCR thấy rõ nút *"Thêm tài khoản"* (Add account).
- **Bẫy dính Banner Webview "Tài khoản được đề xuất" khi mở Switcher**:
  * **Hiện tượng**: Trên màn hình Profile hoặc Feed thường xuất hiện banner pop-up gợi ý: *"Bạn có tin vui? Cho phép TikTok truy cập danh bạ..."* hoặc *"Đề xuất tài khoản"*. Nếu tap mù hoặc tap tọa độ header khi banner đang che, TikTok sẽ mở WebView bài viết trợ giúp: *"Tài khoản được đề xuất"* (Help Center).
  * **Hậu quả nghiêm trọng**: Script chụp nhầm trang webview Help Center và gửi làm ảnh nghiệm thu khiến User bức xúc phản hồi: *"Mày vào trang tài khoản đc đề xuất chi v? Cái t cần là chứng minh ở account switcher chứ"*.
  * **Kỷ luật kiểm chứng ảnh nghiệm thu bắt buộc (Verification Gate)**:
    1. Ảnh nghiệm thu Switcher BẮT BUỘC phải chứa tiêu đề *"Chuyển đổi tài khoản"* (Switch account) và danh sách các dòng tài khoản / nút *"Thêm tài khoản"*.
    2. CẤM TUYỆT ĐỐI gửi ảnh nghiệm thu nếu OCR phát hiện các từ khóa webview Help Center: `"Tài khoản được đề xuất"`, `"Trung tâm trợ giúp"`, `"Điều khoản"`, `"Cài đặt và quyền riêng tư"`.
    3. Nếu phát hiện bị lọt vào WebView: BẮT BUỘC bấm Back (`input keyevent 4`), cuộn profile lên ghim ID (`swipe 540 1100 540 600 250`), rồi tap chính xác vào ID ghim ở đỉnh giữa `(540, 140)` để bung đúng bottom sheet Switcher thật trước khi chụp ảnh nghiệm thu.

## 5. Kết Quả Nghiệm Thu Thực Tế Toàn Farm (Audit 2026-10-02)
- **4 Máy phát hiện có nick ký sinh thật và đã Logout thành công**:
  1. **M76** (`@cyennffqko8` - Máy chính M36): Đã logout ➔ khôi phục nút *"Thêm tài khoản"* cho Slot 2.
  2. **M34** (`@anillpboe98` - Máy chính M56): Đã logout ➔ khôi phục 7 nick chính chủ.
  3. **M69** (`@lebaothao8787` - Máy chính M33): Đã logout ➔ khôi phục 7 nick chính chủ.
  4. **M11** (`@rillecoq5ml` - Máy chính M21): Đã logout ➔ khôi phục 7 nick chính chủ.
- **7 Máy còn lại kiểm tra vật lý xác nhận sạch 100%**:
  * M03, M13, M19, M24, M32, M42, M53: Đều có ảnh Switcher xác nhận không chứa nick ký sinh.
- **Trạng thái Watchdog**: Toàn bộ 17 keys được cập nhật `"DONE"` trong `parasite_reconcile_state.json`.

## 6. Kỷ luật sống còn: Canh sự kiện (Event-Driven) vs Hẹn giờ cố định
- **CẤM TUYỆT ĐỐI**: Hẹn giờ cứng (hardcoded time) kiểu `13:00`, `14:40`, `23:30` để kích hoạt can thiệp hay dọn dẹp farm.
- **NGUYÊN TẮC BẮT BUỘC**:
  1. **Event-driven**: Phải kiểm tra trường `end_time` trong `run_manifest.json` của phiên chạy gần nhất (`row-*-*`).
  2. **Device Locks gate**: Phải kiểm tra thư mục `.codex/device-locks/` — chỉ khi số active lock bằng `0` (farm tĩnh, all máy rảnh) mới được kích hoạt.
  3. **Không hứa mồm**: Mọi cam kết canh phiên phải được hiện thực hóa bằng Cron Watchdog script cụ thể ghi nhận vào scheduler (`cronjob action='create'`), tuyệt đối không nhận lời suông rồi để trôi thời gian.
