# Profile tab bottom-nav filter — tap sai Hồ sơ trong Inbox (2026-09-13)

## Triệu chứng (Ca 3 Row 5, 28/78 máy)
- `reason: [ACCOUNT_SWITCHER_FAILED] open_profile_root failed: PROFILE_ROOT_NOT_CONFIRMED`, `exit_code: 2`.
- Log máy lỗi: `[TAP_PROFILE] Tap profile tab by text 'Hồ sơ': (573, 1587)` hoặc `(595, 322)`.
- Log máy OK: `[TAP_PROFILE] Tap profile tab by text 'Hồ sơ': (972, 1883)`.
- Quy tắc phân biệt nhanh: center_y ≈ 1883 = đúng; y thấp hơn nhiều = tap nhầm node giữa/trên màn hình.

## Hiện trường XML thật
File: `D:/CodexRuntime/tiktok-video/runs/run_988627464e374e3234_20260913_181755/popup_before.xml`
- Tab thật: text `Hồ sơ` bounds `[864,1864][1080,1903]` → center `(972, 1883)`.
- Container: resource-id `com.ss.android.ugc.trill:id/oly`, content-desc `Hồ sơ`, bounds `[864,1794][1080,1920]` → center `(972, 1857)`, visible/enabled/clickable = true.
- Resource-id cũ `com.ss.android.ugc.trill:id/profile_tab` KHÔNG tồn tại trên build TikTok mới → nhánh resource-id luôn trượt, rớt xuống nhánh text mù quáng.
- Node gây nhiễu: content-desc `Hồ sơ BEN EAGLE` (avatar creator giữa feed/Inbox) — cấm match partial.

## Root cause
Commit `a51a1c6` (12/09): khi phát hiện feed overlay (`Vuốt lên để xem thêm` / `Đọc hoặc viết bình luận` / `Thích video`) thì tap `Hộp thư (756, 1857)` trước rồi `dump_ui()` lại trong Inbox. `_find_ui_element(text_contains='Hồ sơ')` trả node ĐẦU TIÊN match (DFS) — notification `...đã xem hồ sơ của bạn` hoặc title `Cập nhật hồ sơ` — thay vì tab bottom-nav.

## Fix chuẩn trong `tap_profile()` (adapter.py + ui_profile.py)
1. `ui_profile.py`: `profile_tab` resource-id → `com.ss.android.ugc.trill:id/oly` (giữ text Hồ sơ/Profile fallback).
2. Mọi nhánh match BẮT BUỘC lọc bottom-nav: `visible-to-user != false`, `enabled != false`, `center_y >= 0.8*screen_height` (1080x1920 → y ≥ 1536), `center_x >= 0.75*screen_width` (x ≥ 810). Tính screen size từ max bounds trong XML, fallback 1080x1920.
3. Nhánh text: duyệt TẤT CẢ node, node đầu không thỏa thì xét tiếp — cấm dừng ở node đầu.
4. Nhánh content-desc: EXACT match `strip().lower() in ('hồ sơ','profile')` — cấm partial.
5. Thứ tự: oly → profile_tab cũ → text → content-desc. Giữ fallback bottom-nav rightmost hiện có.

## Test focused (<30s, không adb/batch)
Parse `popup_before.xml`, mô phỏng filter mới, assert center == `(972,1883)` ±30px; assert node `Hồ sơ BEN EAGLE` không bị chọn.

## Pitfall kèm theo (watchdog)
Phiên 2 trả `status=skipped, reason=already_uploaded_in_shift` cho 61 máy → watchdog gom vào `Bỏ qua (47)`, che 32 lỗi phiên 1 (`Lỗi script/xác minh (0)` là giả). Khi đọc báo cáo có `already_uploaded_in_shift`, đối soát upload_result.json phiên 1 trước khi kết luận hết lỗi.
