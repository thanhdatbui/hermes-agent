# TikTok Profile Video Pinning & Upload Reconciliation

## 1. Cơ chế Ghim (Pin) Video trên TikTok Profile qua ADB
- **Thao tác tối ưu:** Mở video player rồi bấm nút Share/Options, không đè cảm ứng profile tránh lỗi gesture trên một số phiên bản TikTok.
- **Thao tác qua Video Player (Đã kiểm chứng Canary 100%):**
  1. Từ lưới Profile, tap vào ô video top view (`center` của tile).
  2. Bấm nút Chia sẻ/Khác ở cột action bên phải (`x=1000, y=1556` hoặc `(1000, 1580)` trên màn 1080x1920).
  3. Bottom sheet Chia sẻ hiện ra: Cấu trúc 3 hàng icon:
     - Hàng 1 (Gửi bạn bè): $Y \approx 1200 - 1280$.
     - Hàng 2 (Chia sẻ MXH - SMS, Facebook, Direct): $Y \approx 1530 - 1580$.
     - Hàng 3 (Tác vụ video): Nút **`Ghim`** (Pin) nằm ở vị trí thứ 3 từ trái sang tại tọa độ tâm icon `(472, 1750)` (text label bounds `[431, 1820, 512, 1846]`, center `(472, 1833)`).
     - **BẪY LỆCH TỌA ĐỘ ACTION SHEET:** CẤM TUYỆT ĐỐI tap `(180, 1750)` vì đó là nút "Tải về" hoặc "Tăng lượt xem" (`Tăng lượt xem` ở `x=291`). Tap lệch sẽ không ghim được video.
  4. Tap vào nút Ghim `(472, 1750)` $\to$ Bấm `KEYCODE_BACK (4)` quay về Profile.
  5. **BẮT BUỘC NGHIỆM THU OCR TRƯỚC KHI BÁO DONE:** Video xuất hiện nhãn chữ nổi màu đỏ **"Đã ghim"** (Verified qua WinRT OCR: `"Dä ghim"` tại bounds `[34, 1095, 181, 1131]`). TUYỆT ĐỐI CẤM báo "đã ghim" nếu ảnh chụp Profile Grid chưa có OCR chữ `"Dä ghim"` / `"Đã ghim"` (tránh bị user bắt lỗi "Mày bảo ghim đâu?").
- **Giới hạn TikTok:** Mỗi tài khoản ghim tối đa 3 video.

## 2. Ảnh hưởng đối với quy trình đối soát & Upload
- **`_verify_profile_post_increment` (state_machine.py):**
  - Script đếm tổng số video tiles qua hàm `_count_profile_video_tiles_across_grid()` (`baseline` vs `current`).
  - Video được ghim vẫn là một video tile hợp lệ (có `tv_play_count`, `id/eti`, `id/cover`), chỉ mang thêm nhãn `"Đã ghim"` / `"Pinned"`.
  - Khi đăng video mới, tổng số tiles tăng từ $N \to N + 1$ $\implies$ điều kiện `current > baseline` thỏa mãn 100%.
  - Script **không phụ thuộc** vào việc video mới nhất phải nằm ở ô đầu tiên `[0, 0]`.
- **`VIDEO_PICK` (Upload flow):**
  - Chọn video từ thư viện máy (`Download` folder), không đụng vào lưới Profile.
  - Tại `state_machine.py:10061` (`_is_video_pick_profile_action_sheet`), hệ thống đã có sẵn handler nhận diện Action Sheet ghim video để tự bấm Back nếu vô tình chạm trúng khi bấm nút `+`.
- **Workbook & Tracker:**
  - Workbook ghi nhận theo số thứ tự file video nguồn (`context.video_number`).
  - Tracker (`tiktok_account_tracker.py`) đọc chỉ số `stats['videoCount']` từ JSON, không bị ảnh hưởng bởi thứ tự ghim.

## 3. Công cụ Chuẩn Hóa: `D:/Taadaa/tools/pin_top_videos.py`
Công cụ tự động hóa việc dò quét và ghim video nổ view cho từng kênh trên phone farm:

### A. Ngưỡng View Tối Thiểu (`--min-views`, Mặc định: 1.000 view)
- **Bản chất thuật toán:** Video thông thường nếu không đặc sắc sẽ dừng ở mức đáy thử nghiệm (seed pool) **200 – 500 view**. Khi vượt mốc **1.000 view**, video đã vượt qua vòng lọc bot/audience ban đầu và bắt đầu cắn đề xuất.
- **Cơ chế Floor Filter:** Chỉ lọc các video có view $\ge 1.000$ và sắp xếp giảm dần để ghim clip cao nhất trước. Nếu toàn bộ video trên kênh $< 1.000$ view, tool tự động bỏ qua không ghim clip nào (tránh làm gượng trang cá nhân).

### B. Cú Pháp Vận Hành
```bash
# 1. Chạy thử kiểm tra trước (Dry-run — chỉ quét, không thao tác cảm ứng):
python D:/Taadaa/tools/pin_top_videos.py --machine 18 --account huy010822 --min-views 1000 --dry-run

# 2. Ghim thật cho 1 máy theo ID máy (tự động tra cứu serial Kibe Local / Admin Remote):
python D:/Taadaa/tools/pin_top_videos.py --machine 67 --account hoangthu18044 --min-views 1000

# 3. Ghim trực tiếp theo ADB Serial:
python D:/Taadaa/tools/pin_top_videos.py --serial ce12160cf82a303b0c --min-views 1000

# 4. Tùy chỉnh ngưỡng view cao hơn (cho nick khỏe / viral):
python D:/Taadaa/tools/pin_top_videos.py --machine 28 --min-views 5000 --max-pins 3
```

### C. Kỷ Luật An Toàn Thiết Bị (Device Invariants)
- **100% ATX-agent (port 7912):** Đọc UI XML qua `capture_atx_session_ui` hoặc curl direct port 7912, tuyệt đối cấm shell uiautomator dump tránh crash thiết bị yếu (S7 Android 7).
- **Hồi phục an toàn:** Nếu sau khi mở video mà Share Sheet không hiển thị nút Ghim (hoặc video đã được ghim từ trước), tool tự động gửi phím `KEYCODE_BACK` để giải phóng màn hình Profile về trạng thái sạch.

### D. Kiểm Chứng Độc Lập
- Bộ unit test offline: `pytest D:/Taadaa/tools/test_pin_top_videos.py` (bao phủ `parse_view_count`, `parse_action_sheet`, `parse_profile_tiles`).

## 4. Kỷ Luật Tự Động Hóa Mở Profile Từ Automation-Core (CẤM GỌI USER MỞ TAY)
- **Quy tắc bất biến:** Khi chạy Canary hoặc thao tác trên tài khoản mục tiêu, **CẤM TUYỆT ĐỐI** hỏi User: *"bạn đang mở máy số mấy"*, *"bạn mở sẵn Profile đi để mình bắn lệnh"*. Đây là hành vi đùn đẩy việc vi phạm kỷ luật Coordinator.
- **Quy trình tự động 100%:**
  1. **Tra cứu máy & slot:** Quét `Tik1-Tik8.xlsx` hoặc `taikhoan_run_safe_combined.xlsx` để xác định nick mục tiêu (ví dụ `@hoangthu18044` $\to$ Máy 67, Tik 6; `@huy010822` $\to$ Máy 18, Tik 5).
  2. **Đánh thức thiết bị:** Kiểm tra `dumpsys power`, gửi `KEYCODE_WAKEUP` + `82` (unlock).
  3. **Khởi chạy TikTok:** Dùng `am start -n com.ss.android.ugc.trill/.MainActivity`.
  4. **Tự động vào Profile & Chuyển tài khoản:**
     - Sử dụng trực tiếp `open_profile_root(adapter)` từ `automation_core.tiktok.account_switcher`.
     - Nếu nick hiện tại chưa đúng nick cần ghim: Dùng `select_exact_account(adapter, username)` để tự động mở switcher và chuyển sang đúng nick.
     - Thoát video overlay / Live popup: Nếu vướng overlay Live (*"Nhận để xem LIVE"*), vuốt nhẹ `swipe(540, 1400, 540, 700, 300)` để trượt qua rồi tap Profile tab `(970, 1850)`.

## 5. Xử Lý Video Rớt Xuống Dưới & Thứ Tự Ghim Lũy Tiến (Multi-Candidate Grid)
- **Thực tế lưới video:** Các video nổ view thường không nằm ở ô đầu tiên mà rớt xuống Hàng 2 ($Y \approx 1400$), Hàng 3 ($Y \approx 1650$) hoặc sâu hơn do tài khoản đã đăng thêm nhiều video sau đó (ví dụ kênh `@huy010822`: clip 19,4K ở Hàng 1 Cột 1, clip 1.442 ở Hàng 2 Cột 2, clip 5.008 ở Hàng 3 Cột 3).
- **Cơ chế bóc tách tọa độ độc lập:**
  * Hàm `parse_profile_tiles(xml)` tính toán bounding box và tâm (`center`) riêng biệt cho từng ô trong toàn bộ lưới hiển thị, bất kể video nằm ở hàng nào.
  * Bộ lọc `cands` sắp xếp toàn bộ video thỏa mãn $\ge \text{min\_views}$ theo thứ tự view giảm dần: clip view cao nhất luôn được chọn ghim trước.
  * **Hiệu ứng dồn lưới:** Khi một video ở hàng dưới (ví dụ Hàng 3) được ghim, TikTok sẽ đưa video đó lên chiếm ô đầu tiên `[0, 0]` trên Profile và gắn nhãn đỏ `"Đã ghim"`. Các video còn lại tự động dịch chuyển 1 ô.
  * **Ghim nhiều clip (vòng lặp lũy tiến & Bẫy Grid Reorder Race):**
    - **Bẫy dịch chuyển lưới:** Khi một video được ghim thành công, TikTok đưa ngay video đó lên chiếm ô `[0, 0]` (Hàng 1, Cột 1). Các video còn lại trên lưới tự động bị đẩy dịch sang phải hoặc xuống hàng dưới (ví dụ video 19.5K ban đầu ở Hàng 1 Cột 1, sau khi ghim 2 clip khác bị dạt sang Hàng 1 Cột 3).
    - **Cơ chế chống tap nhầm clip đã ghim:** BẮT BUỘC re-dump UI XML sau MỖI lần ghim thành công và tính toán lại danh sách `cands` còn lại. TUYỆT ĐỐI CẤM tái sử dụng tọa độ cũ vì sẽ tap trúng clip vừa ghim $\to$ Action Sheet hiện `"Bỏ ghim"` (UNPIN) khiến script tưởng hết video cần ghim và bỏ sót các video viral chưa ghim.
    - Nếu gặp Action Sheet báo `"Bỏ ghim"`, script phải lập tức bấm Back, đánh dấu video đó đã ghim và quét tiếp các ứng viên khác trên lưới mới.
- **Video ngoài viewport (Deep Scroll & Invariant Quét Toàn Kênh):**
  * **Bẫy Viewport Cố Hữu:** Màn hình đầu tiên chỉ hiển thị 9 – 12 video mới nhất (thường chỉ 200 – 1.900 view). Các video nổ view đề xuất thật sự (10K, 21K, 50K+) thường là video cũ nằm sâu ở các fold dưới.
  * **Kỷ luật điều phối:** Khi user yêu cầu 'ghim video nhiều view / pin top video', CẤM TUYỆT ĐỐI chỉ quét màn hình đầu rồi vội vàng ghim clip 1.9K hay clip đầu tiên. BẮT BUỘC chạy với `--scrolls 4` (hoặc cao hơn) để cuộn tích lũy danh sách video toàn kênh, sắp xếp giảm dần và ghim đúng top clip viral thật sự.
  * **Tái định vị viewport:** Sau khi quét cuộn sâu, tọa độ clip mục tiêu có thể bị trôi ra khỏi màn hình. BẮT BUỘC định vị lại và đưa clip vào viewport trước khi tap.

## 6. Invariant: Database `tiktok_tracker.db` KHÔNG Lưu View Từng Video
- **Bản chất Schema:** Bảng `snapshots` trong `tiktok_tracker.db` chỉ lưu các trường: `timestamp`, `username`, `uid`, `follower`, `following`, `heart` (tổng tim toàn kênh), `video` (tổng số clip), `status`, `avatar_thumb`, `has_avatar`, `created_at`.
- **Hệ quả vận hành:**
  * **CẤM TUYỆT ĐỐI** lên kế hoạch hay thiết kế cron tự động đọc `tiktok_tracker.db` để lọc video nhiều view vì trường view video KHÔNG TỒN TẠI trong database.
  * Việc ghim video nổ view là tác vụ theo đợt (on-demand): chỉ kích hoạt khi người dùng chỉ định nick/máy có clip viral, hoặc chạy batch quét trực tiếp UI Profile vào khung giờ máy rảnh (cuối tuần / sau chu kỳ nuôi 4 ngày), tránh tranh chấp Device Lock với ca nuôi và ca upload.

## 7. Chẩn Đoán Khi XiaoWei Báo Online Nhưng ADB Báo `device not found`
- **Hiện tượng:** Màn hình XiaoWei / JiWei vẫn hiển thị ô máy bình thường hoặc máy trên giàn sáng đèn, nhưng `adb devices` và `inspect_machine.py` báo `device '<serial>' not found`.
- **Nguyên nhân cốt lõi phần cứng (Cáp Micro-USB chập chờn Data):**
  * Cáp Micro-USB có 4 đường: 2 đường nguồn (VCC 5V, GND) và 2 đường dữ liệu (D-, D+).
  * Khi chân D+/D- bị lỏng hoặc bám bụi, máy vẫn ăn điện sạc (sáng màn hình, XiaoWei có thể giữ frame stream cũ nếu pipe chưa timeout), nhưng máy tính mất hoàn toàn kết nối ADB Command Shell.
- **Kỷ luật kiểm chứng O(1) chống cãi / chống văn vẻ:**
  * Bắn socket TCP trực tiếp kiểm tra daemon ADB: gửi `000Chost:devices` tới `127.0.0.1:5037` để đếm chính xác số thiết bị nhận diện thực tế trên ADB daemon.
  * Nếu socket không có serial đó $\implies$ Khẳng định 100% rớt kết nối USB/ADB tại cổng hoặc cáp của máy đó, không phán đoán mò hay sửa script automation.

## 8. Quy Chuẩn Reboot Host Cứu ADB & Tự Động Resume Session Sau Boot
- **Kiểm tra Device Lock trước khi Reboot (Tuyệt đối không làm gãy ca nuôi):**
  * Quét `~/.codex/device-locks/*.json`: Nếu `active locks > 0` (thường là ca nuôi 80 máy trưa/sáng đang chạy), BẮT BUỘC cảnh báo và chờ ca hoàn tất (`active locks == 0`), tuyệt đối không reboot ngang làm gãy dở tiến trình.
- **Bảo toàn và Tự Động Resume Session (Zero-Chat Auto-Resume):**
  * Gọi hàm `preserve_in_flight_sessions` trong `farm_preflight_daily_reset.py` để đóng dấu `resume_pending = True` cho topic Telegram hiện tại trong `SessionDB` và xóa bỏ `.clean_shutdown`.
  * Sau khi host PC hoàn tất reboot và AutoAdminLogon nạp Hermes Gateway, bot sẽ tự động được đánh thức trong chính topic đó, kiểm tra lại trạng thái kết nối thiết bị và tiếp tục thực thi task ghim video mà không cần người dùng phải gõ lại tin nhắn nhắc việc.

## 9. Kỷ Luật Thực Thi Lệnh Reboot & Chống Đóng Băng Chờ Xác Nhận (Anti-Passivity)
- **Bối cảnh vi phạm:** Khi User đã phát lệnh rõ ràng dứt khoát (*"Reboot kibe r thử lại cho t. Khi reboot có thể tự động resume session này k"*), Coordinator kiểm tra an toàn xong lại dừng lại hỏi xin phép: *"Tôi phát lệnh reboot ngay bây giờ nhé? Chỉ cần bạn gõ ok/reboot..."* $\to$ khiến User bỏ đi ngủ 2 tiếng dậy vẫn kẹt nguyên hiện trường, gây bức xúc tột cùng.
- **Quy tắc dứt điểm:** Khi User đã yêu cầu Reboot:
  1. Kiểm tra nhanh điều kiện an toàn (`active locks == 0` và không có trận game TFT 3D).
  2. Gọi `preserve_in_flight_sessions()` đóng dấu session auto-resume.
  3. Kích hoạt lệnh reboot ngay lập tức (`farm_preflight_daily_reset.py` hoặc `shutdown /r /t 5`).
  4. TUYỆT ĐỐI CẤM hỏi lại hay chờ User confirm lần 2. Mọi quyền thực thi L0–L2 đã được cấp sẵn!

## 10. Bẫy Khởi Động TikTok từ Trạng Thái Tắt/Nền (Monkey vs am start)
- **Hiện tượng:** Khi máy vừa khởi động lại hoặc vừa chạy xong tác vụ khác (như reg Gmail), lệnh `am start -n com.ss.android.ugc.trill/.MainActivity` thường không kéo được TikTok lên foreground mà bị kẹt tại Launcher hoặc màn hình Splash rỗng.
- **Giải pháp dứt điểm:** BẮT BUỘC dùng lệnh `monkey` để launch intent launcher chuẩn:
  ```bash
  adb -s <serial> shell monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1
  ```
- Chờ 3.5 giây cho app cold start xong $\to$ dump XML hoặc tap tab Hồ sơ (`bounds=[864,1794][1080,1920]`, tâm `(972, 1857)`).

## 11. Chống Nói Mõm / Chống Hứa Hẹn Khi Có Tiến Trình Nền Giữ Lock (Anti-Talking-Without-Acting)
- **Nguyên tắc hành động:** Khi phát hiện thiết bị đang có tiến trình khác giữ Device Lock (như `gmail_reg_v10.py`), CẤM TUYỆT ĐỐI hứa hẹn suông với User theo kiểu *"khoảng 1-2 phút nữa khi tiến trình xong tôi sẽ ghim..."* rồi đứng im không làm gì (khiến User bực bội: *"Là mày cài watchdog canh rồi hay mày nói mõm cho vui?"*).
- **Kỷ luật xử lý:**
  1. Kiểm tra trạng thái PID (`psutil.pid_exists(pid)`).
  2. Nếu PID vừa thoát / lock vừa nhả: BẮT BUỘC thực thi hành động ngay trong cùng lượt, không giải thích dông dài.
  3. Nếu tiến trình còn đang chạy thật: Bắt buộc đăng ký watchdog hoặc terminal background kiểm tra, không phát ngôn hứa hẹn khi chưa có cơ chế đánh thức tự động.

## 12. Đổi Avatar TikTok Trực Tiếp Qua Long-Press (Khi Không Có Nút "Sửa Hồ Sơ")
- **Hiện tượng trên TikTok v47+:** Màn hình Profile cá nhân chỉ có các nút "Thêm tiểu sử" và tab Video, không có nút "Sửa hồ sơ" hay icon bút chì. Tap nhanh vào avatar thì bị vướng popup "Tạo một Nhật ký" (Story).
- **Quy trình bypass dứt điểm:**
  1. Giữ lâu (Long-press ~1.000ms) vào avatar tại toạ độ `(800, 350)` (element `com.ss.android.ugc.trill:id/bnr`).
  2. Menu bottom sheet hiện lên: chọn `com.ss.android.ugc.trill:id/dwc` ("Thay đổi ảnh") tại `(540, 1248)`.
  3. Thư viện mở ra: chọn ảnh mới nhất tại `(135, 355)` và bấm "Tiếp (1)" (`(924, 1842)`).
  4. Màn hình Cắt ảnh ("Cắt"): **BẮT BUỘC bỏ tick** "Đăng ảnh này lên Nhật ký" (`com.ss.android.ugc.trill:id/sre` tại `(100, 1590)`), sau đó bấm "Lưu" (`com.ss.android.ugc.trill:id/tv_confirm` tại `(792, 1794)`).
  5. Bấm `KEYCODE_BACK` đóng popup chia sẻ. Avatar cập nhật thành công 100% không cần màn hình Sửa hồ sơ.

## 13. Cơ Chế Dồn Thứ Tự Ghim (Push Reorder) Để Top 1 Luôn Nằm Bên Trái
- **Bản chất TikTok:** Mỗi khi ghim 1 video, TikTok đưa video đó vào slot đầu tiên bên trái `[0, 0]` và đẩy các video đã ghim trước đó sang phải.
- **Thứ tự ghim chuẩn khi bắt đầu ghim từ đầu:** Để video view cao nhất (Top 1) nằm ở vị trí đầu tiên bên trái, BẮT BUỘC ghim theo thứ tự **Top 3 -> Top 2 -> Top 1**:
  - Ghim Top 3 (ví dụ 1.4K) $\to$ Chiếm slot 1.
  - Ghim Top 2 (ví dụ 2.3K) $\to$ Chiếm slot 1, đẩy Top 3 sang slot 2.
  - Ghim Top 1 (ví dụ 31.3K) $\to$ Chiếm slot 1, đẩy Top 2 sang slot 2, Top 3 sang slot 3.
- Sau khi ghim đủ 3 video, hàng đầu tiên hiển thị đẹp mắt theo đúng thứ tự: `[Top 1] [Top 2] [Top 3]`.
- **Mẹo Tối Ưu O(1) Khi Đã Ghim Đủ 3 Video (Single Unpin-Repin Shortcut) & Bẫy Rơi Timeline:**
  - Nếu kênh đã ghim đủ 3/3 video nhưng clip Top 1 (nhiều view nhất, ví dụ 31.3K) đang nằm ở Cột 2 (giữa) hoặc Cột 3 (bên phải):
  - Tuyệt đối KHÔNG cần phải bỏ ghim toàn bộ cả 3 clip rồi ghim lại từ đầu (tốn 6 thao tác).
  - Quy trình 2 bước:
    1. Bỏ ghim (Unpin) đúng video Top 1 qua Action Sheet.
    2. Ghim lại (Pin) ngay video Top 1 đó để cơ chế LIFO của TikTok bốc nó đưa lên chiếm vị trí số 1 ngoài cùng bên trái `[0, 0]`.
  - **BẪY RƠI TIMELINE KHI UNPIN (CRITICAL PITFALL):**
    * Khi vừa bấm "Bỏ ghim", video Top 1 **KHÔNG còn ở hàng 1**. Nếu video đó đã đăng cách đây nhiều ngày/tuần (ví dụ clip 31.3K đăng ngày 29/08 trong khi clip mới là tháng 10), nó sẽ **lập tức thụt lùi về đúng vị trí thời gian gốc (chronological order) sâu dưới timeline**, nhường chỗ ở hàng 1 cho clip mới hơn!
    * Hậu quả nếu không biết: Agent nhìn vào hàng 1 thấy clip 31.3K biến mất sẽ tưởng bị xóa hoặc tap nhầm clip khác để ghim đè.
    * **Cách xử lý chuẩn xác:**
      + Cách 1 (Qua Video Player — Khuyên dùng): Tap vào bất kỳ video tile nào trên Profile để mở player toàn màn hình, vuốt lướt theo luồng video (swipe up) tới đúng clip Top 1 theo ngày đăng / số view / caption. Tại video đó, tap nút Chia sẻ `(999, 1556)` $\to$ Action Sheet hiện ra $\to$ Tap "Ghim" `(831, 1776)` $\to$ Bấm Back về Profile.
      + Cách 2 (Scroll Profile Grid): Cuộn sâu lưới Profile tìm đúng tile của clip đó để mở Action Sheet ghim.
    * Sau khi ghim lại từ Video Player, TikTok sẽ kéo video đó từ đáy timeline nhảy vọt lên **vị trí số 1 ngoài cùng bên trái [0, 0]** trên trang cá nhân!

## 14. Quy Trình Sửa Bio Chọn Lọc Cho Kênh Hot Qua Dòng Tiểu Sử (ADB Flow)
- **Kỷ luật Farm**: CẤM đổi bio hàng loạt trên toàn farm bằng script tự động (tránh behavioral burst làm tụt trust score kênh mới dẫn đến 0-view). CHỈ tối ưu bio cho các kênh HOT đã có video viral / cắn đề xuất (>10K view, >500 follower).
- **Thao tác UI qua ADB khi không có nút "Sửa hồ sơ"**:
  1. **Nhánh mở màn hình chỉnh sửa Bio:**
     - *Trường hợp nick đã có bio cũ:* Tap trực tiếp vào dòng chữ Bio cũ tại `(200, 660)` hoặc icon bút chì sửa hồ sơ bên cạnh tên hiển thị `(849, 558)` $\to$ Mở `ProfileEditActivity` $\to$ Tap dòng "Tiểu sử" (`com.ss.android.ugc.trill:id/tvLabel` tại `[84, 1284][414, 1380]`, tâm `(540, 1340)`).
     - *Trường hợp nick chưa có bio hoặc vừa xóa trắng ("No bio yet" / hiện nút "+ Thêm tiểu sử"):* Nút `+ Thêm tiểu sử` (`+ Thém tidU sd`) nằm ở trung tâm dưới follower, bounds `[383, 845, 685, 882]`, tâm `(534, 864)`. Tap thẳng vào `(534, 864)` sẽ mở trực tiếp màn hình `EditText` nhập bio mà không cần qua Sửa hồ sơ.
  2. **BẪY STORY POPUP TRÊN PROFILE ("Bạn có tin vui?"):**
     - Khi tài khoản có gợi ý Story (`Bạn có tin vui?` / `Thì thầm to nhỏ`), vô tình tap vào vùng trên đỉnh (Y ≈ 100-250) sẽ làm bật popup "Tạo một Nhật ký" với thông báo *"Hiển thị với follower trong 24 giờ"*.
     - Popup này kích hoạt bàn phím ảo che nửa dưới màn hình và chặn toàn bộ các nút điều hướng.
     - **Cách giải phóng:** Tap nút `x` đóng popup tại `(996, 270)` hoặc gửi `input keyevent 4` (Back), sau đó mới tap lại tab Hồ sơ `(972, 1882)`. Tuyệt đối không thao tác đổi tài khoản hay ghim video khi popup Story đang mở vì sẽ tap nhầm vào form story.
  3. **Clear & Type Tiếng Việt CÓ DẤU CHUẨN (BẮT BUỘC AdbKeyboard Base64):**
     - **CẤM TUYỆT ĐỐI dùng `adb shell input text`:** Lệnh này chỉ hỗ trợ ASCII và sẽ làm rụng hoặc vỡ toàn bộ dấu tiếng Việt (vi phạm trực tiếp yêu cầu user).
     - **BẮT BUỘC quy trình gõ Tiếng Việt có dấu:**
       1. Kích hoạt & set bàn phím:
          `adb shell ime enable com.github.uiautomator/.AdbKeyboard`
          `adb shell ime set com.github.uiautomator/.AdbKeyboard`
       2. Focus vào `EditText` tại `(536, 650)`.
       3. Xóa text cũ:
          `adb shell am broadcast -a ADB_CLEAR_TEXT`
          (Gửi thêm `input keyevent 123` rồi gửi chuỗi `input keyevent 67` x50 để đảm bảo sạch ký tự).
       4. Bơm text UTF-8 mã hóa Base64:
          `b64_msg = base64.b64encode(bio_text.encode('utf-8')).decode('ascii')`
          `adb shell am broadcast -a ADB_INPUT_B64 --es msg <b64_msg>`
          *(hoặc broadcast `ADB_KEYBOARD_INPUT_TEXT --es text <b64_msg>` tùy phiên bản AdbKeyboard).*
       5. Quan sát bộ đếm ký tự góc dưới: `x/80` hoặc `x/160` (bounds `[899, 1036, 1028, 1069]`) để đảm bảo text đã vào form.
  4. **Checkpoint 1 (Pre-submit)**: Screencap kiểm tra text hiển thị đúng trong `EditText` và nút "Lưu" tại top-right `(980, 140)` / `(991, 150)` sáng khả dụng.
  5. **Submit & Refresh**: Tap "Lưu" tại `(980, 140)` $\to$ `sleep 2.5` $\to$ Bấm `KEYCODE_BACK (4)` hoặc tap tab Hồ sơ `(972, 1882)` để quay lại Profile grid.
  6. **Checkpoint 2 (Post-submit)**: Screencap Profile mới, verify WinRT OCR hiển thị đầy đủ dòng bio mới dưới tên và đối soát đúng định danh tài khoản (`media_verify.py`).

## 15. Tiêu Chuẩn Soạn Bio Tự Nhiên Theo Ngách Nội Dung (Niche-Specific Persona)
- **Tránh bẫy văn phong bot chung chung:** CẤM viết các câu sáo rỗng vô thưởng vô phạt như `"Chào mừng đến với kênh của tôi"`, `"Kênh chia sẻ video hay"`, `"Theo dõi tôi nhé"`.
- **Phương pháp bóc tách Persona từ Thumbnail & Text Overlay:**
  * **Ngách Gym / Healthy / Nữ:** Soi text trên video (`Đi tập với tuii`, `Gymer ăn gì`, `Độ mông`) $\implies$ Bắt buộc đồng bộ đại từ xưng hô `"Tui"` (tự nhiên, thân mật kiểu Gen Z), kết hợp 2 trụ cột nội dung: tập luyện + ăn uống eat clean, kèm CTA follow nhẹ nhàng (VD: `Đi tập cùng tui & làm đồ ăn healthy mỗi ngày 💪🥗`).
  * **Ngách Tiểu phẩm Gia đình / Parody / Đời thường:** Soi tuyến nhân vật và bối cảnh (cha con, tiệm tạp hóa, học sinh nghịch ngợm) $\implies$ Đưa chi tiết nhân vật/bối cảnh vào bio tạo nét riêng biệt và tò mò (VD: `Tiểu phẩm cha con và tiệm tạp hóa bất ổn 😂 Bấm follow để cùng cười nha!`).
- **Độ dài và biểu tượng:** Dưới 80 ký tự, tối đa 1-2 emoji phù hợp ngữ cảnh, câu từ súc tích hiển thị trọn vẹn trong 1-2 dòng không bị nút "...Thêm" che khuất.

## 16. Pitfall Màn Hình Ngủ Khi Chụp Ảnh Nghiệm Thu (Black Screen ~12KB Khi Dozing)
- **Hiện tượng:** Chụp màn hình bằng `screencap -p` tạo file ảnh chỉ ~12KB, WinRT OCR không đọc được text hoặc báo `handle_not_found`.
- **Nguyên nhân:** Thiết bị Samsung S7 rơi vào trạng thái ngủ / dozing (`Màn hình: OFF`), GPU buffer không render frame mới.
- **Xử lý:**
  1. Luôn đánh thức thiết bị trước khi chụp: `input keyevent 224` (WAKEUP) và `input keyevent 82` (UNLOCK).
  2. Đảm bảo app TikTok đang ở foreground (`dumpsys window windows | grep mCurrentFocus`).
  3. Chờ tối thiểu 1.5 – 2.0s cho giao diện vẽ xong frame rồi mới kéo ảnh về máy để verify.





