# Triage & Pattern Reference: Thẻ đề xuất Bạn bè "Xóa", Gợi ý tìm kiếm, Profile cuộn & Regression Gate (2026-10-09)

## 1. Phân biệt Lỗi Cáp USB (CM_PROB_PHANTOM) vs Lỗi Proxy ảo
- **Hiện tượng**: Báo cáo Watchdog phân loại máy vào nhóm `Lỗi cấu hình Proxy` (như M10) hoặc `config-error` (như M30) với stop_reason `device offline or ADB/USB disconnected: adb.exe: device '<serial>' not found`.
- **Bản chất**: Khi thiết bị tuột cáp USB hoặc sập nguồn pin trước ca chạy, runner kiểm tra proxy/VPN preflight không kết nối được qua ADB nên gán nhầm cờ proxy.
- **Quy trình kiểm chứng chuẩn**:
  ```powershell
  Get-PnpDevice | Where-Object { $_.InstanceId -like "*<serial>*" } | Select-Object FriendlyName, Status, Present, Problem
  ```
  Nếu kết quả trả về `Present: False` và `Problem: CM_PROB_PHANTOM`, đây là sự cố phần cứng/cáp vật lý trên rack máy. CẤM can thiệp proxy hay sửa script; đánh dấu HARDWARE_OFFLINE để bảo dưỡng cáp/nguồn.

## 2. Thẻ đề xuất Bạn bè: Nút "Xóa" (`id/udr`) bên cạnh "Follow lại" (`id/ubp`)
- **Vị trí**: Feed TikTok xuất hiện danh thiếp gợi ý tài khoản bạn bè (`follow_back_suggestion`).
- **Giao diện mới**:
  - Nút bên phải: `"Follow lại"` (`resource-id="com.ss.android.ugc.trill:id/ubp"`).
  - Nút bên trái: `"Xóa"` (`resource-id="com.ss.android.ugc.trill:id/udr"`), thay vì nhãn cũ `"Không quan tâm"` (`id/cv6`).
- **Xử lý chuẩn**:
  - `GemPhoneFarmBlindPopupRule` cho `follow_back_suggestion` và hàm `_gem_blind_action`:
    Bắt buộc target xpath mở rộng:
    ```xpath
    //node[@text="Không quan tâm" or @content-desc="Không quan tâm" or @text="Xóa" or @content-desc="Xóa" or @resource-id="com.ss.android.ugc.trill:id/cv6" or @resource-id="com.ss.android.ugc.trill:id/udr"]
    ```
  - Tuyệt đối cấm tap `"Follow lại"` để bảo vệ Trust Score của tài khoản.
  - Regression Test: `test_follow_back_suggestion_taps_xoa_dismiss`.

## 3. Trang Gợi ý tìm kiếm (Search Suggestions Landing)
- **Vị trí**: TikTok vô tình mở vào giao diện tìm kiếm đang gõ dở hoặc hiển thị danh sách từ khóa gợi ý.
- **Đặc điểm UI**:
  - Ô nhập liệu: `class="android.widget.EditText"`, `resource-id="...:id/hvg"`.
  - Nút tìm kiếm: `text="Tìm kiếm"`, `resource-id="...:id/tv_search_textview"`.
  - Nút quay lại: `resource-id="...:id/bse"`, `bounds=[18,84][150,216]`.
  - Danh sách gợi ý: Các node chứa `id="...:id/tvl_unified_sug"`.
- **Nhận diện**:
  `detect_search_landing_page` phải bao gồm nhánh:
  `has_search_input and any("sug" in (r or "").lower() for r in rids)`
  để phân loại thành `tiktok_search_landing_page` (generic popup) và tự động bấm nút Back thoát về Feed.
  - Regression Test: `test_search_landing_with_suggestions_detected`.

## 4. Trang Public Profile bị cuộn xuống lưới Video
- **Hiện tượng**: Khi bị nhảy vào profile creator/người khác, màn hình bị vuốt cuộn qua khỏi header (mất `@username`, stats). Màn hình chỉ còn nút `"Follow"` và lưới video với các thẻ `com.ss.android.ugc.trill:id/tv_play_count`.
- **Vấn đề**: `_is_public_profile_screen` cũ đòi hỏi header `@username` đầy đủ nên trả về `unknown`, khiến feed runner dừng lại với lỗi popup allowlist hoặc kẹt 2 lần vuốt.
- **Nhận diện**:
  Nếu không thấy header nhưng có $\ge 3$ node `tv_play_count` kết hợp nút `"Follow"`/`"Đang follow"` và không có thanh điều hướng Home đáy (`has_home_nav == False`):
  Xác nhận là `profile` để runner kích hoạt `KEYEVENT 4` (Back) quay trở lại Feed video.
  - Regression Test: `test_scrolled_public_profile_grid_classified_as_profile`.

## 5. Quy Chuẩn Regression Gate & Xử Lý TRANSIENT Timeout Subagent
- **Regression Gate bắt buộc**: Bỏ ghi chép case docs thủ công; mọi sửa đổi logic UI/popup BẮT BUỘC phải đi kèm unit test regression trong pytest suite.
- **Xử lý Worker TRANSIENT Timeout (L0)**:
  - Khi worker bị treo 600s do nghẽn API/mạng:
    1. Kiểm tra `git status` và `git checkout -- <file>` để đưa working tree về trạng thái sạch sẽ.
    2. Tinh chỉnh prompt: Cấp exact Patch Contract trực tiếp để worker gọi `patch` ngay, không đọc lan man monolith files lớn.
    3. Re-dispatch worker (Retry 1 L0) theo đúng thang điều phối.
