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

## 4. Xử Lý Video Nổ View Rớt Xuống Dưới (Hàng 2, Hàng 3 & Vuốt Cuộn)
- **Phân loại vị trí video:**
  * Video nổ view không nhất thiết ở ô đầu tiên: có thể nằm ở Hàng 2 (ví dụ `1.442` view), Hàng 3 (ví dụ `5.008` view), hoặc sâu hơn.
  * `parse_profile_tiles` bóc tách toàn bộ các ô video trên lưới kèm tọa độ tâm (`center X, Y`), lọc bỏ các video đã có nhãn `"Đã ghim"` và video bản nháp (`bản nháp`, `draft`).
  * Sắp xếp video theo số view giảm dần (`cands.sort(key=lambda x: x["views"], reverse=True)`).
  * Lần lượt tap mở và ghim video top cao nhất trước, bất kể nó nằm ở hàng nào.
  * **Khi video nằm ngoài viewport hiện tại:** Vuốt cuộn màn hình (`swipe(540, 1500, 540, 700, 400)`) để đưa ô video vào vùng an toàn trước khi tap.

## 5. Vị Trí Đóng Gói Mã Nguồn (Repo Management)
- **Repo quản lý trung tâm:** `taadaa-farm-tools` (`D:/Taadaa/tools`) — remote: `https://github.com/thanhdatbui/taadaa-farm-tools.git`.
- **Tool thực thi:** `D:/Taadaa/tools/pin_top_videos.py`.
- **Unit test offline:** `D:/Taadaa/tools/test_pin_top_videos.py`.
- **Hỗ trợ CLI đầy đủ:** `--machine <N>`, `--account <username>`, `--min-views <INT>`, `--max-pins <INT>`, `--dry-run`.
