# Máy 5 + máy 19 row-5 feed/follow debug (2026-08-17)

Chi tiết live-debug 2 máy row 5 sau canary 6-máy (5,19,21,33,34,35): máy 5 = vượt 2 chỗ kẹt
(popup add-phone bottom-sheet + notification shade sau switcher), máy 19 = follow báo
`OPEN_TIKTOK_FAILED` DƯƠNG TÍNH GIẢ dù máy thật đang lướt feed. Cả 2 đều là lỗi chẩn đoán
UI-gate, không phải lỗi máy.

## Popup "Thêm số điện thoại" = BOTTOM SHEET → close X nằm giữa màn hình, core `_close_candidate` loại (máy 5)

- TikTok farm render popup add-phone dạng bottom-sheet ("Trang tính dưới cùng"): title
  "Thêm số điện thoại" + phone input + "+84" + nút "Tiếp tục" + close X (content-desc "Đóng")
  nằm ở **góc phải CỦA SHEET** (y ~804-936) chứ NOT góc phải trên màn (top ≤ 350).
- Core `automation_core.tiktok.benign_popup._close_candidate` CHỈ nhận close X với
  `left >= 800 AND top <= 350` → close None → core detect trả None → classifier ra
  `for-you` (0.89) dù XML có ĐỦ 5 markers → popup không dismiss → keyboard xwkeyboard dưới
  sheet → keyboard cleanup BACK không đóng → "TikTok focus lost" → manual-needed.
- **Fix (consumer `python_runner/core/benign_popup.py::detect_add_phone_popup`)**: sau khi core
  trả None, nếu ĐỦ 4 content markers (`add_phone_title_or_body`, `vn_phone_prefix`,
  `phone_input_marker`, `continue_button_marker`) → fallback `_bottom_sheet_close_candidate`
  chấp nhận node close-label (`đóng/close/dismiss/×/x`) BẤT KỲ vị trí nào, ưu tiên top-most
  rồi right-most. Verify bằng XML thật: `detect_add_phone_popup` → match close center
  (996,870), classifier → `manual-needed:add-phone` 0.98 (trước: for-you).
- Chẩn đoán nhanh 1 máy: `screencap` thấy bottom-sheet + `grep` XML thật có 4 markers nhưng
  classifier ra for-you = đúng bug này. Test: `test_classifier.py` + `test_account_switcher.py`
  (71 passed) + `test_feed_session_smoke.py` (169 passed).

## Notification shade của Vi Changer mở ĐÈ sau khi tap account-switcher → "TikTok focus lost" (máy 5)

- Sau khi tap đúng nick trong switcher (tap_expected_account SUCCESS), TikTok reload account →
  Vi Changer bật lại VPN → notification "VPN Connected" → **notification shade mở** →
  `focused_package: com.android.systemui` → safety_check "TikTok focus lost" → manual-needed.
- Triệu chứng: log `profile_preflight_switch_1/tap_expected_account success` rồi ngay sau đó
  `verify_tiktok_focus failed (TikTok focus lost)`; XML verify chứa systemui nodes (battery,
  clock, "Thông báo của Vi Changer: VPN Connected").
- **Fix (consumer `python_runner/flows/feed_swipe_smoke.py::_dismiss_notification_shade_if_open`)**
  gọi đầu `_navigate_profile_for_preflight`: nếu `get_focused_activity` = systemui → swipe up
  (540,1800→540,300,250ms) hoặc keyevent BACK → chờ 1.2s → retry; wrapper try/except toàn bộ
  (mock/offline context trả False để giữ fail-closed cũ). Test smoke 169 passed — helper phải
  exception-safe vì `get_focused_activity` trên FakeAdapter trả Mock.

## Empty-row → config-error không chạy live (user rule 17/08)

- User: "đến lịch row nào gọi máy có acc row đó, máy không có acc thì bỏ qua". Implement trong
  `feed_session_workbook.py::select_feed_session_accounts`: row chọn mà `expected_username` rỗng
  → config-error `"account row {row_index} is empty (no username) for machine {machine}, skipping"`
  → KHÔNG chạy live. Máy vẫn xuất hiện trong summary với `final_status: config-error`,
  `account_source: current-device`, swipes 0 (KHÔNG xóa khỏi summary — fail-closed ghi rõ lý do).
- Bin `execute_multi_machine_feed_session`: khi MỌI máy config-error (accounts rỗng) →
  `launch_evidence` chưa định nghĩa → **UnboundLocalError** → khởi tạo
  `launch_evidence = None` trước `if accounts:`. 4 test cũ "empty username → current-device
  fallback" phải đảo semantics thành config-error skip (test_multi_machine_feed_session.py).

## Chạy run-feed-session từ Hermes background/terminal → PYTHONPATH leak (cả feed lẫn mọi repo)

- Triệu chứng: `ImportError: cannot import name '_imaging' from 'PIL'` resolve về
  `hermes-agent\venv\Lib\site-packages\PIL` khi chạy `run-feed-session.ps1` qua terminal tool.
- Root cause: Hermes session env có PYTHONPATH → child python (automation venv) resolve PIL từ
  hermes venv (không có `_imaging` native lib). `live_entrypoint._spawn_subprocess` đã
  `env.pop("PYTHONPATH")`, nhưng khi chạy ps1 TRỰC TIẾP từ Hermes → leak.
- **Fix đã verify**: prefix lệnh `PYTHONPATH="" PYTHONTZPATH='D:/Taadaa/Hermes/.venv/Lib/site-packages/tzdata/zoneinfo'`
  (cần cả 2 — thiếu TZDATA → `ZoneInfoNotFoundError: Asia/Ho_Chi_Minh`). Lần đầu chạy
  background KHÔNG có prefix → fail `_imaging`; chạy lại có prefix → success.
- Nhớ: `tail` nuốt exit code — kiểm tra RC bằng `echo "RC=$?"` SAU pipe hoặc đọc stdout thật.

## Máy 19 (row 5): follow báo OPEN_TIKTOK_FAILED nhưng máy THẬT đang lướt feed (dương tính giả)

- Feed success ✓ rồi follow hook trả `MANUAL_REVIEW: OPEN_TIKTOK_FAILED — TikTok không load
  feed sau retry`. Kiểm tra thật: screencap 21:44 = TikTok ở tab "Đề xuất", video đang phát
  (kênh "Bóc Tách Phim Hay"), KHÔNG kẹt splash.
- ĐÚNG skill cảnh báo: `dumpsys window mCurrentFocus` báo `SplashActivity` dù feed đã render;
  thêm nữa `uiautomator dump` fail `uiautomator_idle_state_error` khi video đang animation
  (UI không idle) — NHƯNG CẢ HAI ĐỀU LÀ FALLBACK/NHẦM. **Screencap = ground truth** — đừng kết
  luận "kẹt splash" từ dumpsys khi ảnh cho thấy feed chạy. Nếu follow-side `open_tiktok()`
  dùng dumpsys/activity gate mà máy thực đang feed → fail giả (giống máy 7 nhưng bên follow;
  xem pitfall tiktok-follow-automation).
- Follow máy 19 state: `follow_state_19.json` có `followed` từ đêm trước (6 nick) — không phải
  lỗi code, chỉ là verify-gate sai nguồn. Quy tắc: gặp OPEN_TIKTOK_FAILED → screencap trước,
  nếu ảnh = feed đang chạy thì báo user "dương tính giả" chứ đừng đổ lỗi máy/nick/script.