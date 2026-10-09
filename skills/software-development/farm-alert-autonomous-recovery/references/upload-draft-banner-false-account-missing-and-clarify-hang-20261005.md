# Bẫy Cảnh Báo Ảo ACCOUNT_MISSING Do Banner Bản Nháp Upload & Kỷ Luật Chống Treo Phiên Do Clarify (2026-10-05)

## 1. Căn nguyên sự cố

Trong đợt vận hành Farm Alert ngày 05/10/2026:
- Hệ thống bắn cảnh báo: `[P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Phát hiện Máy M7: UploadHook: [ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found. Cần MANUAL_REVIEW: kiểm tra TikTok đã login chưa...`
- Coordinator tiến hành điều tra, nhưng rơi vào 2 sai lầm nghiêm trọng gây bức xúc cho User ("Lồn mẹ mày lí do treo"):
  1. **Treo phiên do lạm dụng tool `clarify`:** Khi nhận thấy sự mâu thuẫn giữa cảnh báo và hiện trường live/artifact, Coordinator tự ý gọi tool `clarify` để hỏi User về cách mapping tài khoản thay vì tự chủ động hành động theo thang L0–L2. Tool `clarify` rơi vào trạng thái orphan recovery / blocking hang, làm toàn bộ tiến trình đóng băng.
  2. **Ảo giác văng tài khoản P0 (False Alarm `ACCOUNT_MISSING`):** Thực chất tài khoản không hề bị văng khỏi máy. Nguyên nhân gốc rễ là do ca upload trước đó bị lỗi tải lên, để lại banner đỏ `UPLOAD_FAILURE_BANNER` ở đỉnh màn hình Profile: *"Không thể tải video lên. Đã lưu bản nháp. Chạm để thử lại"*. Banner này che/lệch tọa độ tap mở Account Switcher khiến Switcher **chưa từng được mở ra**, nhưng runner upload ngộ nhận đã mở và vuốt 3 lần trên màn hình Profile rồi vội vàng raise lỗi `ACCOUNT_MISSING`.

---

## 2. Phân tích kỹ thuật: UPLOAD_FAILURE_BANNER vs ACCOUNT_SWITCHER

### Triệu chứng trong log runner (`execution.log` & `checkpoint.json`):
```text
[INFO] scripts.tiktok_workflow.state_machine: [ACCOUNT_SWITCHER] Switcher opened via core ✓
[INFO] automation_core.tiktok.account_switcher: [ACCOUNT_SWITCHER] Account huehoafi23 not visible in current viewport; attempting scroll
[DEBUG] scripts.tiktok_workflow.adapter: [ADAPTER_SWIPE] Swiping (540, 1536) -> (540, 960) dur=450ms
[INFO] automation_core.tiktok.account_switcher: [ACCOUNT_SWITCHER] Swiped switcher list (attempt 1/3); redumping UI
...
[ERROR] scripts.tiktok_workflow.state_machine: [ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found.
```

### Bằng chứng đối soát thực tế:
- Màn hình `account-switcher-profile.png` lúc runner cố gắng switch tài khoản:
  * Đỉnh màn hình có banner: *"Không thể tải video lên. Đã lưu bản nháp. Chạm để thử lại."*
  * Không có thanh tiêu đề *"Chuyển đổi tài khoản"*, không có danh sách bottom sheet tài khoản.
- Màn hình thực tế trong XML khi switcher mở thật sự (`profile_preflight_switcher_1_guard`):
  * Tài khoản `huehoafi23` cùng toàn bộ danh sách 8 tài khoản vẫn nằm 100% nguyên vẹn trong bottom sheet `RecyclerView`.

---

## 3. Hai Bug Code Tàng Hình Được Khai Quật & Khắc Phục

### Bug 1: Switcher 8 Nick Bị Từ Chối Do Nút "Thêm tài khoản" Trượt Khỏi Màn Hình
- **Cơ chế lỗi:** 
  * Trên các máy chuẩn 8 nick/máy, 8 dòng tài khoản lấp đầy toàn bộ chiều cao `RecyclerView` `[0,252][1080,1920]`. Nút *"Thêm tài khoản"* bị đẩy xuống đáy (off-screen / below the fold).
  * Nếu nick active có khoảng trắng trong display name (ví dụ: `"Diep Lam"`), core `automation_core.tiktok.account_switcher` loại trừ vì quy tắc `_looks_like_account` (`" " not in value` trả về False).
  * Hàm fallback `_is_profile_account_switcher_xml` trong consumer trước đây yêu cầu: `has_title and has_add_account`. Do thiếu nút "Thêm tài khoản", hàm trả về `False`, khiến hệ thống coi Switcher là màn hình lạ/chặn và dừng với mã `manual-needed:account-switcher`.
- **Khắc phục chuẩn hóa:**
  * Sửa `_is_profile_account_switcher_xml`: Chỉ cần có tiêu đề `has_title` VÀ (`has_add_account` HOẶC có danh sách dòng tài khoản `account_rows`) là công nhận Switcher ngay lập tức:
    ```python
    has_title = bool(values.intersection(_ACCOUNT_SWITCHER_TITLES))
    has_add_account = any(_is_add_account_option_text(value) for value in values)
    account_rows = {
        value.lstrip("@")
        for value in values
        if _is_account_like_switcher_text(value)
    }
    if has_title and (has_add_account or account_rows):
        return True
    ```

### Bug 2: Banner Lỗi Upload Đè Profile & Nhận Nhầm "Bản nháp" Làm Display Name
- **Cơ chế lỗi:**
  * Banner upload lỗi `"Không thể tải video lên. Đã lưu bản nháp."` (resource-id `tv_tips`) che toàn bộ đỉnh màn hình Profile `[24,102][1056,357]`.
  * Thanh hiển thị username/display-name anchor bị che mất.
  * Thư mục nháp `"Bản nháp: 1"` (id `tv_draft`) bị hàm `_profile_identity_from_xml` bốc nhầm làm display name người dùng vì chưa nằm trong danh sách `is_profile_placeholder`.
- **Khắc phục chuẩn hóa:**
  * **Tự động dismiss banner:** Khi phát hiện `tv_tips` hoặc *"Không thể tải video lên"*, tự động tìm nút `ImageView` clickable `[960,138][1008,186]` (resource-id kết thúc bằng `:id/ea5`) và tap đóng banner ngay tại bước kiểm tra Profile.
  * **Loại trừ "Bản nháp":** Bổ sung tiền tố `"bản nháp"`, `"draft"` vào `is_profile_placeholder` để không bao giờ nhận vơ tab thư mục nháp làm tên tài khoản.
  * **Hồi vị Profile:** Khi `not identity.get("username")`, re-tap tab "Hồ sơ" và swipe down để kéo màn hình bị cuộn lỡ về lại đỉnh trang.

### Bug 3: Samsung Nuốt Cú Chạm Tâm Hàng Switcher (x=540 vs x=350)
- **Cơ chế lỗi:**
  * Trên các máy Samsung (như Galaxy S7 màn 1080x1920), Button dòng tài khoản trong Switcher (`ls_`) kéo dài toàn bộ chiều ngang `[0, y1][1080, y2]`.
  * Khi runner tính tâm theo bounds của Button: `center = [540, (y1 + y2) // 2]`. Tọa độ `x=540` rơi vào khoảng trống chết (whitespace) bên phải của tên tài khoản (tên chỉ dài đến `x=521`).
  * Hệ thống cảm ứng của Samsung nuốt sự kiện chạm trên vùng trống này, khiến TikTok không chuyển nick nhưng runner tưởng đã tap thành công, dẫn đến lỗi: `profile username still mismatched after switch`.
- **Khắc phục chuẩn hóa:**
  * Giới hạn bề ngang của các hàng tài khoản rộng >= 600px về dải `0..700px`, đưa tâm tap từ `x=540` về `x=350`:
    ```python
    if node.bounds is not None and (node.bounds[2] - node.bounds[0]) >= 600:
        y1, y2 = node.bounds[1], node.bounds[3]
        best_bounds = (node.bounds[0], y1, min(node.bounds[0] + 700, node.bounds[2]), y2)
    ```
  * Tọa độ `x=350` rơi chính xác vào trọng tâm cụm chữ tên tài khoản và icon avatar, kích hoạt chuyển nick 100% ăn.

### Bug 4: Màn Hình Lỗi Mạng / "Thử lại" Bị Bỏ Qua Ở Bước Khởi Động Baseline
- **Cơ chế lỗi:**
  * Khi TikTok vừa khởi động, do proxy hoặc delay mạng thiết bị, màn hình Home có thể hiện: *"Không có kết nối Internet. Hãy nhấn để thử lại."* kèm nút *"Thử lại"* (resource-id `ze3` / `dd9`).
  * Trong `feed_swipe_smoke.py`, logic gọi `find_matching_handler` (để trigger `_dismiss_network_error_retry` bấm nút "Thử lại") bị kẹp cứng trong điều kiện `if require_feed and attempt.get("detected_screen") in NETWORK_RETRY_SCREENS:`.
  * Tuy nhiên, ở bước khởi động `baseline` (`_capture_baseline_with_startup_retry`), `_capture_step` lại được gọi với `require_feed=False, step="baseline"`.
  * Hậu quả: Dù có sẵn handler tự động bấm "Thử lại" trong `benign_popup_registry`, runner vẫn bỏ qua không bấm, coi baseline là `manual-needed:network` và dừng session ngay lập tức.
- **Khắc phục chuẩn hóa:**
  * Mở rộng điều kiện kiểm tra trong `_capture_step`: Cho phép handler bấm "Thử lại" kích hoạt khi `(require_feed or step == "baseline")`.

---

## 4. Quy chuẩn điều phối & Phòng chống lặp lại

### Invariant 1: CẤM TUYỆT ĐỐI dùng `clarify` khi triage Farm Alert
- Khi nhận Farm Alert, Coordinator có toàn quyền tự chủ theo ngân sách L0 (Retry transient), L1 (Re-dispatch Worker), L2 (Emergency Surgery).
- CẤM gọi `clarify` để hỏi: "chọn mapping nào", "có tiếp tục không", "tài khoản nào cần canary".
- Nếu dữ liệu mâu thuẫn hoặc không thể xác định: chuyển thẳng sang **L3 BLOCKED kèm bằng chứng đối soát thực tế**, tiếp tục làm task khác. Tuyệt đối không được gọi `clarify` làm đóng băng phiên làm việc.

### Invariant 2: Phân định rạch ròi Banner che Switcher vs Mất tài khoản thật
- Trước khi xác nhận hoặc báo cáo lỗi `ACCOUNT_MISSING`:
  1. Phải kiểm tra artifact screenshot tại bước mở switcher (`account-switcher-profile.png` hoặc `screen.png`).
  2. Nếu màn hình chứa banner bản nháp / upload lỗi (`UPLOAD_FAILURE_BANNER`), lỗi thực chất là **KẸT GIAO DIỆN / CHE PHỦ BANNER**, KHÔNG PHẢI mất tài khoản.
  3. Bắt buộc xử lý dismiss/đóng banner bản nháp trước khi tap mở Switcher.
