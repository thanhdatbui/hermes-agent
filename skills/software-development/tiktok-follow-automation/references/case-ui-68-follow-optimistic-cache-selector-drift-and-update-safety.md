# Case UI-68: Phân tích Toàn diện Lỗi Follow Giả (Optimistic UI Cache), Selector Drift 46.x/47.x (fm9 vs fmp), Cơ chế Phá Cache và Quy trình Update Đè TikTok

## 1. Bản chất Kỹ thuật của Lỗi Follow Giả (Optimistic UI / Silent Rollback)
- **Cơ chế Client-side Optimistic UI:** Khi người dùng/bot bấm nút Follow (dù trên Video Player, Profile, hay Danh sách Search/Following), TikTok client ngay lập tức đổi trạng thái hiển thị sang "Nhắn tin" / "Đã follow" trong RAM (In-Memory Session Cache) trước khi máy chủ xác nhận.
- **Silent Rate-Limit (Nhả follow ngầm):** Nếu tài khoản bị rate-limit hoặc gắn cờ bot, server âm thầm từ chối request mà không báo lỗi ra UI.
- **Bẫy Cache Đa Tầng:**
  1. *Video Player -> Profile:* Back từ video ra profile, app vẫn cache fragment cũ -> hiện "Nhắn tin" giả.
  2. *Profile -> Search Results:* Back tiếp ra Search results, Activity cha vẫn giữ session cache -> hiện nút xám "Đã follow" giả.
  3. *Chỉ lộ mặt thật khi Re-fetch từ Server:* Chỉ khi thực hiện kéo **Pull-to-refresh** (ép activity reload dữ liệu) HOẶC **Re-entry** (thoát hẳn ra search/feed rồi bấm mở lại card profile mới) thì server mới trả về trạng thái thật -> Nút đỏ "Follow / Follow lại" bật ngược trở lại.

## 2. So sánh Anti-Bot giữa Pull-to-refresh vs Natural Re-entry (Sol Approved)
- **Phương án A — Pull-to-refresh tại chỗ (Primary - 80%):**
  - *Ưu điểm:* Cử chỉ cảm ứng tự nhiên (Touch-down -> Hold -> Drag -> Release -> Wait). Không làm biến dạng đồ thị điều hướng (Session Graph).
  - *Yêu cầu bắt buộc:* Phải có **Jitter tự nhiên** (lệch X +-25px, lệch Y +-30px, duration ngẫu nhiên 500-750ms). Tuyệt đối cấm vuốt tọa độ cứng máy móc.
- **Phương án B — Natural Re-entry (Secondary Fallback - 20%):**
  - *Bản chất:* Back ra Search results -> Bấm vào lại card profile.
  - *Rủi ro nếu lạm dụng:* Dễ tạo pattern Crawler / Navigation Loop nếu lặp lại liên tục trên quy mô lớn.
  - *Khuyến nghị:* Dùng làm phương án bổ trợ 20% để phá vỡ tính lặp lại đơn điệu.

## 3. Selector Drift TikTok 46.9.3 vs 47.0.3 (fm9 vs fmp)
- **TikTok 46.9.3 (ví dụ Máy 38):**
  - Nút Follow đỏ và Nhắn tin xám cùng mang chung resource-id: `id/fm9`.
- **TikTok 47.0.3 (ví dụ Máy 37):**
  - ByteDance đổi resource-id nút Follow đỏ và Nhắn tin xám sang: `id/fmp`.
- **Hậu quả chết người nếu thiếu whitelist:**
  - Nếu thiếu `id/fmp` trong `_ACTION_BUTTON_SUFFIXES`, node Follow đỏ bị coi là `is_action_node = False` (bỏ qua).
  - Nhưng node "Nhắn tin" bên cạnh lại lọt qua nhờ text marker "nhắn tin".
  - -> Kết quả: Màn hình đang có nút Follow đỏ lòm nhưng script đọc thành `followed`, gây ra báo cáo sai (False Positive).
- **Quy tắc Resilient:** Whitelist `_ACTION_BUTTON_SUFFIXES` trong `verify_follow.py` bắt buộc phải chứa đầy đủ cả `:id/fm9`, `id/fm9`, `:id/fmp`, `id/fmp`.

## 4. Hành vi Tương tác Xem Video Ngẫu nhiên (Human Engagement Flow)
- **Cấm cố định video đầu (`video_covers[0]`):** Bắt buộc chọn ngẫu nhiên 1 video từ lưới hiển thị: `random.choice(video_covers[:min(len(video_covers), 6)])`.
- **Phân bổ hành vi tự nhiên (Sol Approved):**
  - **70% số nick có xem video:** Xem video ngẫu nhiên được chọn 6–12s, thả tim ngẫu nhiên 40%, rồi back về.
  - **25% số nick có xem video:** Sau video đầu, vuốt lên xem video thứ 2 từ 4–8s, rồi back về.
  - **5% số nick có xem video:** Vuốt xem tiếp video thứ 3 lướt nhanh rồi back về.

## 5. Kinh nghiệm Vận hành Update Đè APK & Cron Tránh Bẫy
- **Cài đặt đè TikTok qua ADB:** Dùng `adb install-multiple -r -d base.apk split_config.arm64_v8a.apk split_config.vi.apk split_config.xxhdpi.apk`.
- **Bảo toàn dữ liệu tài khoản:** Cài đè split APKs bảo toàn 100% dữ liệu SQLite / SharedPreferences cục bộ. Cả 8 nick trong switcher vẫn nguyên vẹn sau khi lên 47.0.3.
- **Tránh nhầm lẫn với Cron chạy ngầm:** Khi thấy màn hình đòi OTP 2FA Hotmail hoặc NewUserJourney, phải kiểm tra ngay xem có cron job 2FA nào (như `post-noon-chain-watchdog`) đang chiếm quyền thao tác trên tài khoản đó không, tránh phán đoán sai lầm là do update làm văng nick.

## 6. Phân tích Rủi ro Fraud Detection & Anti-Cheat khi Cài Đè APK qua ADB (Sol Approved)
- **Tương quan Rủi ro Thực tế (Risk Hierarchy):**
  ```text
  Behavior Correlation (Timing / Concurrent Follow / IP) = RẤT CAO
  Modified / Re-signed APK (Khác Signature ByteDance)    = CAO
  ADB Installation Method (pm install thô)              = THẤP
  ```
- **Bản chất chữ ký số (Signature Verification):**
  - Khi pull trực tiếp bộ APK từ máy Samsung S7 cài qua Google Play, toàn bộ splits đều mang đúng chứng thư số gốc của ByteDance (`signatures=PackageSignatures{... [2606a464]}`).
  - Android OS từ chối cài đè nếu chữ ký sai lệch. Việc cài đè thành công chứng minh client là bản sạch nguyên bản 100%, không bị biến đổi mã (tampered/modded).
- **Tín hiệu `installerPackageName`:**
  - Máy cài từ CH Play mang cờ `installerPackageName=com.android.vending`.
  - Cài qua lệnh ADB mặc định để lại `installerPackageName=null`.
  - Dù TikTok server không kill acc chỉ vì nguồn cài ADB, nhưng việc 50+ máy đồng loạt mất cờ Play Store trong cùng thời điểm tạo ra tín hiệu bất thường ở cấp độ cả đàn (Fleet-level Anomaly).
  - *Mẹo kỹ thuật bảo toàn cờ CH Play khi cài qua session ADB:*
    `pm install-create -r -d -i com.android.vending -p com.ss.android.ugc.trill` (cờ `-i` chỉ định installer là `com.android.vending`).
- **Chiến lược Tối Thượng Cho Phone Farm:**
  - **Freeze Baseline + Code Resilience:** Không nên update đồng loạt toàn dàn nếu không bắt buộc. Khóa tự động cập nhật ngầm qua `settings put global auto_update_apps 0`.
  - Duy trì code runner kháng đa phiên bản (`_ACTION_BUTTON_SUFFIXES` chứa cả `fm9` của 46.x lẫn `fmp` của 47.x) để máy ở bản nào cũng vận hành chuẩn xác mà không cần cưỡng ép can thiệp phần mềm hàng loạt.
