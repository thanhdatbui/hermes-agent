# TikTok Email Replacement Pitfalls & Navigation Checkpoints (Session 2026-10-31)

## 1. Bẫy Điều Hướng & Quét Chữ Mù Từ Màn Hình Feed (Comment Modal Trap)
- **Hiện tượng:** Khi app TikTok vừa mở lên ở trang Feed chính, nếu script chạy quét chữ mù (ví dụ tìm `"Email"`, `"Tôi"`, `"Hồ sơ"`) mà không kiểm tra trạng thái màn hình hiện tại:
  - Bot có thể tap trúng khu vực bình luận của video đang phát hoặc icon comment.
  - Khi đó, TikTok bật tấm card `Comment Section Overlay` (ví dụ `227 bình luận`) che 2/3 màn hình.
  - Script không vào được Profile nhưng vẫn chạy ngầm luồng rút OTP và cập nhật database -> Dẫn đến tình trạng báo cáo thành công ảo ("báo cáo bố láo"), trong khi trên app thực tế chưa hề mở form đổi email.
- **Quy chuẩn Checkpoint 5 bước bắt buộc:**
  1. **Bước 1 (Về Profile):** Tap góc dưới cùng bên phải `[972, 1860]` để đảm bảo app đang ở màn hình Profile cá nhân. Xác nhận xuất hiện các nút sửa hồ sơ / username.
  2. **Bước 2 (Mở Menu 3 gạch):** Tap góc trên cùng bên phải `[1005, 150]` để mở menu đáy.
  3. **Bước 3 (Cài đặt & quyền riêng tư):** Định vị node `text="Cài đặt và quyền riêng tư"` qua ATX RPC hoặc OCR và tap tâm bounds (thường tại `[623, 1248]`).
  4. **Bước 4 (Tài khoản):** Định vị node `text="Tài khoản"` (CẤM dùng tọa độ đáy `y >= 1750` kẻo trúng "Hủy kích hoạt hoặc xóa tài khoản").
  5. **Bước 5 (Thông tin tài khoản -> Email -> Thay đổi email):** Chỉ khi nào màn hình xuất hiện đúng form `Thay đổi email` hoặc ô input `Nhập email` mới được phép nhập mail mới.

## 2. Hard Verification Gate Trước Khi Ghi Database (Anti-False Reporting)
- **CẤM TUYỆT ĐỐI** gọi hàm `farm_db.update_tiktok_credentials` chỉ dựa trên việc "rút được OTP từ API".
- **Điều kiện cần và đủ để update DB:**
  1. Phải nhập OTP vào app TikTok và submit thành công.
  2. Màn hình phải điều hướng về trang *Thông tin tài khoản*, dòng Email phải hiển thị đúng email mới (hoặc dạng masked `x***y@hotmail.com`).
  3. Chụp ảnh màn hình nghiệm thu thực tế lưu vào `reports/`. Chỉ khi có ảnh chứng minh mới được phép update SQLite SSOT và Master Excel.

## 3. Bẫy Cảnh Báo "Tài Khoản Hiện Đang Bị Đình Chỉ" (Tainted / Banned Destination Email)
- **Hiện tượng:** Khi điền email mới và bấm *"Tiếp tục"*, TikTok hiện dòng chữ cảnh báo đỏ ngay dưới ô nhập: **`⚠️ Tài khoản hiện đang bị đình chỉ`**.
- **CĂN NGUYÊN THỰC TẾ (User chỉ điểm & Đối soát xác thực 2026-10-31):**
  - **LỖI DO EMAIL ĐÍCH, KHÔNG PHẢI DO NICK TRÊN MÁY:** Cảnh báo này xuất hiện khi email mới nhập vào (`new_email`) đã từng bị đem đi đăng ký tài khoản (ví dụ test reg trên TikTok Lite/app) ở phiên khác và bị TikTok phát lệnh **Ban / Instant-Cấm**.
  - Khi một email đã bị TikTok ghi nhận trong danh sách vi phạm/bị cấm (Banned/Suspended Email), việc cố gắn email này vào bất kỳ nick TikTok nào khác sẽ bị server TikTok từ chối ngay lập tức và bắn lỗi `"Tài khoản hiện đang bị đình chỉ"` (ám chỉ tài khoản ứng với email này đang bị cấm).
  - Tài khoản TikTok đang login trên máy hoàn toàn khỏe mạnh, video và follow vẫn bình thường.
- **Kỷ luật phòng tránh bắt buộc:**
  1. **Tuyệt đối cấm tái sử dụng email đã dính lỗi reg:** Bất kỳ hòm thư Hotmail nào đã từng chạy thử đăng ký tài khoản mà bị lỗi `"Tài khoản của bạn đã bị cấm"` bắt buộc phải bị **XÓA HOÀN TOÀN / QUARANTINE** khỏi kho mail, cấm tuyệt đối việc đưa sang pool đổi email cho nick đang nuôi.
  2. **Quét sạch file script/draft tạm thời (Anti-Zombie-Email Trap):** Xóa trong database thôi là CHƯA ĐỦ. Phải rà soát và xóa sạch chuỗi email bị cấm trong các file script tạm, script test canary (`tools/*.py`, `canary_*.py`), tránh việc session sau vô tình import hoặc dùng lại script cũ có hardcode email rác.
  3. **Kiểm tra lịch sử email trước khi gắn:** Đảm bảo email cấp cho flow đổi email là mail nguyên seal (`virgin mail`), chưa từng gửi request đăng ký hoặc dính gậy trên bất kỳ phiên bản TikTok nào.
## 4. Multi-Account Switcher Drift & Re-Focus Invariant (Bẫy Lạc Nick Đang Đổi)
- **Hiện tượng & Bẫy:** Trên máy farm Android (chứa 8 slot nick), sau khi đổi qua lại giữa các menu, popup cài đặt, hoặc mở lại app, TikTok có thể tự động giữ focus ở nick đang hoạt động gần nhất (ví dụ slot khác như `@juli...` thay vì nick cần đổi `@hatien...`).
  - Nếu chỉ bấm Back hoặc thao tác mù, bot sẽ đi vào menu *Thông tin tài khoản* của NHẦM NICK, dẫn tới nguy cơ đổi nhầm hòm thư cho tài khoản khác hoặc tưởng nhầm nick đã đổi.
- **Kỷ luật bẻ lái Account Switcher chuẩn xác:**
  1. **Tuyệt đối cấm đoán mò:** Sau khi bật app TikTok, BẮT BUỘC tap vào tab Hồ sơ `[972, 1860]` và kiểm tra chuỗi username (`@username`) trên màn hình.
  2. **Bung Switcher trực tiếp từ Profile:**
     - Tap trực tiếp vào khu vực tên hiển thị / username trên đỉnh màn hình `[200, 320]` để bung bottom-sheet *Chuyển đổi tài khoản* (hoặc từ *Cài đặt* -> cuộn xuống dòng *Chuyển đổi tài khoản*).
     - Bắt buộc kiểm tra danh sách tài khoản hiện ra, tap chính xác vào bounds của nick mục tiêu.
  3. **Xác nhận lại sau khi switch:** Phải thấy thông báo *"Đã đổi sang [Tên Nick]"* và kiểm tra lại đúng username trên Profile trước khi đi tiếp vào *Cài đặt* -> *Tài khoản* -> *Thông tin tài khoản*.

