# TikTok Profile Video Pinning & Upload Reconciliation

## 1. Cơ chế Ghim (Pin) Video trên TikTok Profile qua ADB
- **Thao tác tối ưu:** Mở video player rồi bấm nút Share/Options, không đè cảm ứng profile tránh lỗi gesture trên một số phiên bản TikTok.
- **Thao tác qua Video Player (Đã kiểm chứng Canary 100%):**
  1. Từ lưới Profile, tap vào ô video top view (`center` của tile).
  2. Bấm nút Chia sẻ/Khác ở cột action bên phải (`x=1000, y=1556` trên màn 1080x1920).
  3. Bottom sheet hiện ra: Tìm node có text/desc `"Ghim"` / `"Pin"` (bounds chuẩn `[747, 1656][915, 1896]`).
  4. Tap vào nút Ghim $\to$ Bấm `KEYCODE_BACK` quay về Profile.
  5. Kiểm chứng hiện trường: Video xuất hiện nhãn chữ nổi màu đỏ **"Đã ghim"** (Verified qua WinRT OCR: `"Dä ghim"`).
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
- **Video ngoài viewport (Deep Scroll):** Nếu video viral nằm sâu phía dưới (ngoài màn hình hiện tại), thực hiện swipe cuộn lưới lên (`swipe(540, 1500, 540, 700, 400)`) bên trong vùng grid container để nạp các ô video cũ vào viewport trước khi tap.

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

