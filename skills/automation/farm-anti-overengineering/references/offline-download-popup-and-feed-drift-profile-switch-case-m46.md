# Bài Học Case Máy 46: Popup Ngoại Tuyến Che Home Feed Sau Switch Account & Cấu Trúc Switcher Button TikTok 46.8.3

## 1. Hiện tượng thực tế (Sự cố Máy 46 & Farm Alert)
- **Cảnh báo farm:** `🚨 [FARM ALERT: MÁY 46] DỪNG PHIÊN - Nick: thy.linh.l199 - profile username still mismatched after switch`.
- **Hiện trường kiểm tra thực tế:**
  1. Sau khi script mở Account Switcher và tap vào tài khoản `thy.linh.l199`, TikTok khởi tạo lại session và điều hướng mặc định về **Home Feed (`Trang chủ` / tab `Đề xuất`)**.
  2. Tại Home Feed, giữa màn hình xuất hiện popup dialog thông báo kết nối mạng:
     - Text: `"Không có kết nối. Tự động tải video về qua Wi-Fi để xem ngoại tuyến?"` (`resource-id="com.ss.android.ugc.trill:id/z6g"`).
     - Nút xác nhận: `"OK"` (`resource-id="com.ss.android.ugc.trill:id/dcj"` tại bounds `[408, 1193][672, 1325]`).
  3. Thanh điều hướng đáy (Bottom Navigation): `Trang chủ` (`selected=true`), `Hồ sơ` (`selected=false`).
  4. Popup dialog che toàn bộ màn hình khiến cú tap điều hướng tab Hồ sơ (`[972, 1857]`) bị chặn hoặc nuốt sự kiện, app bị kẹt lại ở Home Feed.
  5. Script recapture màn hình thấy không ở Profile hoặc parse nhầm username dẫn tới dừng phiên `profile username still mismatched after switch`.

---

## 2. Cấu Trúc Accessibility Tree Của Account Switcher Trên TikTok 46.8.3 (Samsung Galaxy S7)

Khảo sát chi tiết cấu trúc XML của Bottom Sheet *"Chuyển đổi tài khoản"* (`id/g0z`) trên TikTok 46.8.3:
- **Row Container (Button duy nhất có `clickable="true"`):**
  - `class="android.widget.Button"`, `resource-id="com.ss.android.ugc.trill:id/lpw"`.
  - `content-desc="thy.linh.l199"`, `bounds="[0, 600][1080, 816]"`, `clickable="true"`.
  - Tâm điểm container: $(X=540, Y=708)$.
- **Child 1 - Username TextView:**
  - `class="android.widget.TextView"`, `resource-id="com.ss.android.ugc.trill:id/nba"`.
  - `text="thy.linh.l199"`, `bounds="[252, 678][542, 738]"`, `clickable="false"`.
  - Tâm điểm text: $(X=397, Y=708)$.
- **Child 2 - Avatar:**
  - **Không tồn tại node riêng** trong accessibility tree (được nhúng dưới dạng compound drawable của Button, không có `ImageView` độc lập).
- **Phân tích Touch Event:**
  - Node duy nhất nhận sự kiện click là `android.widget.Button` (`id/lpw`).
  - Do `TextView` con có `clickable="false"`, lệnh tap vào dải Y `[600, 816]` của row đều được Android dispatch trực tiếp lên `Button` (`id/lpw`).
  - Tuy nhiên, nếu tap trúng dead whitespace ở mép phải $(X > 500)$ hoặc nếu hệ thống bị trễ nhịp do dialog mạng chen vào, switch event có thể bị ngắt.

---

## 3. Các Bài Học & Quy Tắc Cốt Lõi

### A. Nhận diện & Dismiss Popup Ngoại Tuyến (Offline Download Dialog)
- Khi mạng Wi-Fi hoặc Proxy farm bị chập chờn (hoặc khi chuyển tài khoản làm drop kết nối tức thời), TikTok hiển thị popup `"Không có kết nối. Tự động tải video về qua Wi-Fi để xem ngoại tuyến?"`.
- Popup này thuộc nhóm in-app benign popup của TikTok (`com.ss.android.ugc.trill`), KHÔNG PHẢI app ngoài chen vào.
- **Xử lý chuẩn:**
  1. Đăng ký selector trong `benign_popup_registry.py`:
     - Text marker: `"Không có kết nối. Tự động tải video"` / `"Tự động tải video về qua Wi-Fi"`.
     - Resource IDs: `id/z6g` (message text), `id/dcj` (nút OK).
     - Action: Dismiss an toàn bằng cách bấm nút `"OK"` (`id/dcj`) hoặc phím `BACK` (`keyevent 4`).
  2. Bổ sung kiểm tra popup này trong luồng `_navigate_profile_for_preflight` trước khi thực hiện re-tap tab Hồ sơ.

### B. Kỷ luật Coordinator Guard v2.2 Thực Chiến
- Tại session chính, sau khi chạy 1 lệnh inspect O(1) (`inspect_machine.py 46`), PreToolUse Hook của `farm-coordinator-guard` khóa cứng toàn bộ lệnh terminal/file tools tiếp theo ở Phase ALERT.
- Coordinator BẮT BUỘC thực thi Zero-Delay Dispatch: soạn Patch Contract / Directive rõ ràng và chuyển giao cho Worker Subagent qua `delegate_task`.
- Mọi thao tác chụp màn hình, trích xuất log, kiểm tra XML và chạy Canary đều được Worker Subagent thực thi độc lập trong background, bảo vệ session chính không bị block hay tràn context.
