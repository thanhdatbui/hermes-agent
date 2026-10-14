# TikTok Video Pinning Automation (In-Video Share Sheet & Profile Grid Navigation)

## 1. Cơ chế UI Ghim Video Thực Chiến (Đã kiểm chứng trên Samsung S7 TikTok v47.0.3)
- **Bẫy thao tác đè cảm ứng (Long-press Trap):**
  * Trên các bản TikTok gần đây (như v47.0.3), thao tác đè cảm ứng (long-press 1000ms) trên lưới Profile KHÔNG mở Action Sheet mà sẽ trực tiếp mở video player hoặc không có phản hồi.
  * **Luồng ghim chuẩn xác 100%:**
    1. Tap vào giữa ô video mục tiêu (`center X, Y` từ `parse_profile_tiles`) để mở video player.
    2. Tap vào nút **Chia sẻ / Tùy chọn (Share)** ở cột icon bên phải (tọa độ `x=1000, y=1556` hoặc node có content-desc `"Chia sẻ video"`).
    3. Action Sheet (Trang tính dưới cùng) trượt lên: Quét tìm nút **"Ghim"** (text: `"Ghim"`, content-desc: `"Ghim"`, icon kim ghim, bounds `[747, 1656][915, 1896]`, center `(831, 1776)`).
    4. Tap vào nút "Ghim" -> Nhận thông báo "Đã ghim lên đầu hồ sơ".
    5. Gửi phím `KEYCODE_BACK` (code 4) quay về lại Profile để xác nhận nhãn đỏ **"Đã ghim"**.

## 2. Kỷ luật Điều hướng Profile & Chuyển Nick Tự Động (User Invariant)
- **CẤM BẮT USER MỞ TAY / HỎI MÁY NÀO:**
  * Khi nhận lệnh ghim video cho 1 tài khoản/máy: Coordinator CẤM hỏi user "máy nào đang mở" hay bắt user tự mở TikTok vào Profile.
  * **Tích hợp bắt buộc từ `automation-core`:**
    - Sử dụng `open_profile_root` và `select_exact_account` từ `automation_core.tiktok.account_switcher`.
    - Script tự động: Đánh thức màn hình (`KEYCODE_WAKEUP` + key `82`), khởi chạy TikTok (`com.ss.android.ugc.trill`), kiểm tra username Profile hiện tại.
    - Nếu khác target account: Tự động tap vào display name (`(158, 322)`) để mở Switcher và chọn đúng account đích.
    - Nếu gặp overlay/live/ad chiếm màn hình: Tự động swipe nhẹ lên và tap tab "Hồ sơ" (`(970, 1850)`).

## 3. Bản chất Dữ Liệu View & Lý do Không Chạy Auto Ngầm Toàn Farm
- **`tiktok_tracker.db` KHÔNG LƯU VIEW:**
  * Bảng `snapshots` trong DB chỉ lưu các chỉ số cấp kênh: `follower`, `following`, `heart`, `video`, `status`. Tuyệt đối **không lưu lượt xem (view)** của từng video riêng lẻ.
  * Do không có dữ liệu view trên PC để lọc trước, **CẤM cho script chạy tự động càn quét 80-160 máy** (sẽ gây tranh chấp Device Lock với ca nuôi, làm nóng máy và chai pin).
  * **Quy trình vận hành chuẩn:** Chạy theo đợt khi user chỉ định nick nổ view, hoặc chạy theo batch máy rảnh vào cuối tuần/đêm.

## 4. Xử Lý Video Nổ View Rớt Xuống Dưới & Bẫy Đảo Vị Trí Lưới (Grid Reorder Trap)
- **Phân loại vị trí video:**
  * Video nổ view không nhất thiết ở ô đầu tiên: có thể nằm ở Hàng 2 (ví dụ `1.442` view), Hàng 3 (ví dụ `5.008` view), hoặc sâu hơn.
  * `parse_profile_tiles` bóc tách toàn bộ các ô video trên lưới kèm tọa độ tâm (`center X, Y`), lọc bỏ các video đã có nhãn `"Đã ghim"` và video bản nháp (`bản nháp`, `draft`).
  * Sắp xếp video theo số view giảm dần (`cands.sort(key=lambda x: x["views"], reverse=True)`).
  * Lần lượt tap mở và ghim video top cao nhất trước, bất kể nó nằm ở hàng nào.
  * **Khi video nằm ngoài viewport hiện tại:** Vuốt cuộn màn hình (`swipe(540, 1500, 540, 700, 400)`) để đưa ô video vào vùng an toàn trước khi tap.

- **BẪY TỬ HUYỆT: Đảo Vị Trí Lưới Sau Khi Ghim (Grid Reorder Trap):**
  * **Hiện tượng:** Khi ghim thành công 1 video, TikTok ngay lập tức đẩy video đó lên chiếm Cột 1 hoặc Cột 2 của hàng đầu tiên, và dạt các video chưa ghim sang vị trí khác (ví dụ: video 19.5K chưa ghim từ Cột 1 bị dạt sang Cột 3).
  * **Hậu quả nếu dùng tọa độ cũ:** Nếu bot dùng lại tọa độ cũ của Cột 1, bot sẽ tap trúng video vừa ghim xong $\rightarrow$ Action Sheet hiện nút **"Bỏ ghim" (UNPIN)** $\rightarrow$ Bot tưởng lỗi nên bỏ qua, làm sót video chưa ghim!
  * **Quy tắc bắt buộc:** Sau mỗi thao tác ghim 1 video và Back về Profile, BẮT BUỘC gọi `dump_profile_ui_atx` lấy lại cây XML tươi mới để tính lại bounding box và tọa độ tâm của video chưa ghim tiếp theo.
  * **Dynamic Share Button Finder:** Quét XML màn hình xem video tìm node có `content-desc`/`text` chứa `"chia sẻ"` hoặc `"share"` để lấy tọa độ tâm thực tế; chỉ fallback về `(1000, 1556)` khi không tìm thấy node.
  * **Kiểm tra Return Code & Read-Back Verification (`verify_pin_applied`):** Mọi lệnh `input tap` phải kiểm tra `returncode == 0`. Sau khi ghim xong về Profile, dump lại XML và xác nhận số lượng video mang tag "Đã ghim" tăng lên.

## 5. Kỷ Luật Thực Thi Reboot Khi User Yêu Cầu (Anti-Confirmation Paralysis)
- Khi user đã phát lệnh rõ ràng: *"Reboot kibe r thử lại cho t. Khi reboot có thể tự động resume session này k"*:
  1. **Preflight Check O(1):** Quét `~/.codex/device-locks/` (yêu cầu 0 active locks) và kiểm tra `is_tft_match_in_progress() == False`.
  2. **Đóng Dấu Auto-Resume:** Gọi `preserve_in_flight_sessions(lookback_minutes=60)` để ghi `resume_pending = True` vào `SessionDB` và xóa `.clean_shutdown`.
  3. **Thực thi dứt điểm:** Kích hoạt ngay lệnh `shutdown /r /t 5`.
  4. **CẤM TUYỆT ĐỐI:** Cấm hỏi lại *"Tôi phát lệnh reboot ngay bây giờ nhé?"* làm đóng băng phiên suốt nhiều giờ trong khi user đang ngủ/bận việc!

## 6. Vị Trí Đóng Gói Mã Nguồn (Repo Management)
- **Repo quản lý trung tâm:** `taadaa-farm-tools` (`D:/Taadaa/tools`) — remote: `https://github.com/thanhdatbui/taadaa-farm-tools.git`.
- **Tool thực thi:** `D:/Taadaa/tools/pin_top_videos.py`.
- **Unit test offline:** `D:/Taadaa/tools/test_pin_top_videos.py`.
- **Hỗ trợ CLI đầy đủ:** `--machine <N>`, `--account <username>`, `--min-views <INT>`, `--max-pins <INT>`, `--dry-run`.
