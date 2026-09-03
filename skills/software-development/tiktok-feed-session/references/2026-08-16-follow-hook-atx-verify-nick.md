# 2026-08-16: follow-hook + ATX-primary + verify nick đúng cách

Session debug canary máy 6 — các bài học KHÔNG được lặp lại.

## 1. dumpsys window BÁO SAI activity khi feed đã render (lỗi kẹt splash giả)

Triệu chứng: `dumpsys window` báo `SplashActivity` trong khi ảnh thật là **feed đã render** (TikTok không chuyển activity window nhưng UI vào feed). Code tưởng kẹt splash → baseline fail `detected: unknown` / `capture-invalid`.

Fix (đã commit `1a33a14`): `get_focused_activity` (flows/observe.py) **ATX-primary** — gọi `automation_core.ui.capture_ui_xml(..., provisioning_policy=REQUIRE_PROVISIONED)` trước, lấy package thật từ XML (`package="..."` attr); dumpsys làm fallback.

Quy tắc: **tin screenshot/XML thật hơn dumpsys**. Khi nghi kẹt splash → screencap + nhìn ảnh (hoặc vision) trước khi kết luận.

## 2. Verify nick CHỈ qua profile chính chủ / account switcher

Phân biệt bằng UI:
- **Profile chính chủ**: có nút "Sửa hồ sơ" (bút ✎) + dấu 3 gạch ≡ (Cài đặt & Quyền riêng tư), username hiện ngay dưới display name.
- **Profile người khác**: có nút **"Nhắn tin"** + mũi tên quay lại ← + nút Chia sẻ, gợi ý follow "Tài khoản được đề xuất".

Lỗi đã mắc: tap nhầm vào profile tìm kiếm (`@longtuong10` = nick máy 58) → tưởng máy 6 login sai nick → báo nhầm. **Kết luận sai acc chỉ từ profile người khác = lỗi nghiêm trọng.**

## 3. tiktok-follow search nick lạ = HÀNH VI MODE 1, không phải sai acc

`run_follow.py` mode 1 (search-follow) mở profile của nick đang follow (trong farm) — màn hình sẽ hiện profile người khác + lịch sử tìm kiếm đầy nick. Đây là hành vi BÌNH THƯỜNG. Đừng kết luận "máy đang login nick lạ".

## 4. Reset màn hình sạch TRƯỚC khi verify/follow

Chạy follow khi màn hình còn kẹt ở profile tìm kiếm → `switch_account_and_verify` verify sai → `MANUAL_REVIEW: exact profile identity không khớp` → **kết luận sai "sai nick"**. Thứ tự đúng: về feed sạch (keyevent HOME → monkey launch → chờ) → mới chạy follow/verify.

## 5. Follow hook: mode "1" CHỈ search-follow (chốt 16/08)

- Config `D:\Taadaa\tiktok-follow\follow_runner\config.example.yaml`: `mode: "1"` (bỏ "both") — mode 2 (follow followers) fail `MANUAL_REVIEW: hồ sơ thiếu handle (@uid) — từ chối tap Follower`.
- Follow = follow chéo **trong farm** (UID từ safe workbook, loại trừ nick đang active).
- Hook subprocess: `python -m follow_runner.run_follow --machine N --config ... --account-row-index R` với `cwd=D:\Taadaa\tiktok-follow` (script path trực tiếp fail ModuleNotFoundError — import `follow_runner.core` không resolve). Commit `0fafc57`.
- State: `runs/state/follow_state_<machine>.json` (so với cwd tiktok-follow) — dedupe + budget 30/ngày, session random 5-10.

## 6. Organic follow khi lướt Đề xuất = 6% (sẵn có)

`DEFAULT_FEED_FOLLOW_RATES[FEED_TYPE_FOR_YOU] = 6` (feed_swipe_smoke.py:583) — mỗi video swipe 6% cơ hội follow creator (`_maybe_follow_video`, line ~11396). Đã chốt 5→6. Không cần sửa.

## 7. Popup phân loại (user chỉ đạo 16/08)

- Popup **cấp quyền / gợi ý add số điện thoại** (permission, add-phone) → **automation-core** dismiss (`automation_core/tiktok_popup.py` rules location/contacts/notification_permission, add_phone_number_vi; `automation_core/tiktok/benign_popup.py` detect_add_phone_popup).
- Popup **CTA mua hàng** ("Mua ngay", shop CTA khi lướt feed) → **repo consumer** (feed_swipe_smoke.py `GemPhoneFarmBlindPopupRule` — tên cũ gây hiểu nhầm, thực chất là popup TikTok shop; `shop_cta_close`).
- Lỗi core gặp: popup contacts "Để kết nối với những người bạn biết trên TikTok, hãy cho phép truy cập vào danh bạ..." — text KHÔNG chứa "cho phép tiktok truy cập vào danh bạ" (thiếu "tiktok") → rule `contacts_permission_vi` không match. Cần marker linh hoạt hơn (thêm "cho phép truy cập vào danh bạ" hoặc "kết nối với những người bạn biết").

## 8. Tap nút = dùng ATX bounds (KHÔNG dùng tọa độ ước lượng)

Screencap trả kích thước khác màn hình thật (720×1280 vs 1080×1920) → scale tọa độ sai. Lấy bounds chính xác từ XML: `capture_ui_xml` → regex `text="..."[^>]*bounds="\[...\]\[...\]"` → tap center.

## 9. pm clear = CẤM tuyệt đối (nhắc lại)

`pm clear --cache-only` cũng xóa cache TikTok → app kẹt splash + mất data (máy 4 16/08). Rule đã có trong memory — KHÔNG BAO GIỜ chạy pm clear trên TikTok kể cả --cache-only.

## 10. TikTok bị disabled (enabled=0) trên nhiều máy farm

dumpsys package thấy `enabled=0` → app văng home im lặng. Fix: `pm enable com.ss.android.ugc.trill` + launch bằng `monkey` (`am start` direct bị từ chối). Không phải lỗi code — trạng thái máy.
