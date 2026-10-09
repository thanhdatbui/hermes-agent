# Case 98: Bottom-Nav Geometry Filter & Exact Resource-ID Cho Tap Profile

## 1. Hiện tượng lỗi hiện trường
- Ca 3 Row 5 (13/09/2026): 28/78 máy dính lỗi `ACCOUNT_SWITCHER_FAILED / open_profile_root failed: PROFILE_ROOT_NOT_CONFIRMED`.
- Toàn bộ 28 máy đều có triệu chứng giống hệt máy 10 (`run_988627464e374e3234_20260913_181755`):
  - `OPEN_TIKTOK` thành công, xác nhận feed bằng visual gate.
  - Chuyển sang `ACCOUNT_SWITCHER`: phát hiện overlay video feed, tự động tap Hộp thư `(756, 1857)` để thoát overlay theo commit `a51a1c6`.
  - Màn hình chuyển sang Hộp thư (Inbox) hoặc trang con. Lúc này hàm `tap_profile()` trong `adapter.py` gọi tìm text `"Hồ sơ"`.
  - Hàm `_find_ui_element` dùng `text_contains` duyệt cây XML và nhặt trúng node đầu tiên thỏa mãn substring ở phần trên màn hình (ví dụ avatar/creator `Hồ sơ BEN EAGLE` tại `(941, 641)` hoặc `(573, 1587)`, `(595, 322)`).
  - Tap nhầm làm app mở subpage của creator/inbox → kích hoạt Back recovery 12 lần liên tiếp → thất bại và văng `PROFILE_ROOT_NOT_CONFIRMED`.

## 2. Nguyên nhân cốt lõi (Root Cause)
1. **Lỗi Resource-ID:** Trong `ui_profile.py`, selector `profile_tab` đang khai báo `resource_id="com.ss.android.ugc.trill:id/profile_tab"`. Trong các bản build TikTok hiện đại trên S7, resource-id thật của container tab Hồ sơ là `com.ss.android.ugc.trill:id/oly`. Do lệch ID, script luôn trượt nhánh 1 và rơi xuống nhánh 2 (text-matching).
2. **Thiếu ràng buộc hình học (Geometry Gate):** Nhánh text-matching và content-desc không kiểm tra tọa độ đáy màn hình. Node đầu tiên chứa chữ "hồ sơ" ở bất kỳ vị trí nào trên màn hình đều bị tap mù quáng.

## 3. Giải pháp chuẩn (Case Fix)
Áp dụng vào `scripts/tiktok_workflow/adapter.py` (`tap_profile`) và `scripts/tiktok_workflow/ui_profile.py`:
1. **Cập nhật Resource-ID:** Đổi `profile_tab` thành `com.ss.android.ugc.trill:id/oly`.
2. **Lọc Bottom-Nav bắt buộc (`_is_valid_bottom_nav`):**
   - Lấy kích thước màn hình `screen_width` và `screen_height` từ bounds tối đa trong XML (fallback 1080x1920).
   - Node chỉ hợp lệ khi:
     - `visible-to-user != "false"`
     - `enabled != "false"`
     - Tọa độ trung tâm `center_x >= 0.75 * screen_width` (nằm ở 25% góc phải màn hình)
     - Tọa độ trung tâm `center_y >= 0.80 * screen_height` (nằm ở 20% thanh navigation đáy màn hình)
3. **Thứ tự quét 3 tầng:**
   - Tầng 1: Resource-id `oly` trước, `profile_tab` sau (kèm lọc bottom-nav).
   - Tầng 2: Duyệt toàn bộ các node chứa text `"hồ sơ"` hoặc `"profile"` và chỉ chọn node thỏa bottom-nav (không dừng ở node đầu tiên nếu node đó nằm ngoài bottom-nav).
   - Tầng 3: Content-desc exact-match `node.attrib.get("content-desc", "").strip().lower() in ("hồ sơ", "profile")` (kèm lọc bottom-nav). Xóa bỏ hoàn toàn nhánh partial match `if "hồ sơ" in cd` cũ.

## 4. Verification & Canary Evidence
- Mô phỏng XML trên `popup_before.xml`: Lọc chính xác container `oly` tại `(972, 1857)` (tab Hồ sơ thật), loại bỏ 100% các node `Hồ sơ BEN EAGLE`.
- Live Canary máy 10 (`988627464e374e3234`):
  ```text
  [INFO] adapter: [TAP_PROFILE] Tap profile tab by resource-id: (972, 1857)
  [INFO] state_machine: [ACCOUNT_SWITCHER] Profile root opened via recovered core flow ✓
  [INFO] state_machine: [ACCOUNT_SWITCHER] Target account already selected; skipping switcher ✓
  ```
  Thành công mở profile root và xác nhận nick trong 3 giây.
