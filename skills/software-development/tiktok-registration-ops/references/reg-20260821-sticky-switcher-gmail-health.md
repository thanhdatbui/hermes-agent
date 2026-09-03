# Reg session 2026-08-21: Sticky switcher + gmail-health + OTP rescue

Kết quả session: 12 nick SUCCESS (máy 1, 23, 25, 30, 31x2, 38, 42, 76, 77, 78, 79). Mọi nick đều bị bắt tạo
mật khẩu — KHÔNG có nick nào TikTok cho qua bỏ bước pass (trả lời chính xác câu "có máy nào cho qua k bắt
nhập pass k" = KHÔNG; log "không có màn password" chỉ là script bỏ qua bước, pass vẫn được set).

## Sticky switcher bar — mở account dropdown trên profile (TikTok UI mới)
- Profile screen: handle `com.ss.android.ugc.trill:id/scn` (text `@...`, 540,616) — BẤM thẳng KHÔNG bung
  bottom sheet (rv5) trên bản mới. Kẹt vĩnh viễn nếu chỉ tap handle.
- PHẢI vuốt lên ~400px (540,1000 → 540,600, dur 400) để header dính lên top → xuất hiện sticky top bar
  rid `p7w` (y1≤350, clickable) → TAP bar đó mới mở sheet "Chuyển đổi tài khoản".
- Pass 0 selector sticky: rid chứa `pcs|p01|p1j|qx0|qzr|p7w|pmh` + y1≤350 (bounds `[406,72][675,228]` là p7w).
- Retry (attempt 1-2): `dismiss_profile_overlays()` trước → swipe 400px → sleep 1.5 → re-dump. Restart app 1 lần
  nếu vẫn fail, rồi STOP GATE.
- PITFALL #1: selector display-name (txt dài ≥220px, y2≤610) CÓ THỂ match "Thêm tiểu sử" → tap mở edit
  profile / dialog bàn phím → kẹt. Đã fix: loại `"tiểu sử"` khỏi match text.
- PITFALL #2: sau khi vuốt lên, handle `scn` chuyển y từ 616 → 228 — nhận diện lại mỗi attempt, đừng hardcode y.

## "Chọn bàn phím" (Choose keyboard) dialog
- Khi tap field trên vài máy (vd 77, 78), dialog/notification "Chọn bàn phím" bung → chặn mọi dump/click.
- Fix đã encode vào `dismiss_profile_overlays`: match flat "chon ban phim" / "select input method" /
  "choose keyboard" → keyevent Back.
- Nếu dai: `ime set com.sec.android.inputmethod/.SamsungKeypad` (kiểm tra `ime list -a` — AdbKeyboard KHÔNG có
  trên máy này; `ime set com.android.adbkeyboard/.AdbIME` sẽ lỗi "Unknown id").

## gmail-health: bug `len(v)<=50` — health check CHƯA BAO GIỜ chạy thật (đã fix 2026-08-21)
- `node_has_target()` có guard `(len(v) <= 50 and t_norm in v)` → resource-id dài >50 ký tự (vd
  `com.google.android.gm:id/selected_account_disc_gmail` = 52) KHÔNG BAO GIỜ match → health check luôn thoát
  `gmail_avatar_not_found` sau 2-3s, health NEVER kiểm tra được account.
- FIX: bỏ guard độ dài → `if t_norm and (t_norm == v or t_norm in v)`.
- SAU fix, chạy thật cho tanglam2811200242@gmail.com (máy 42):
  - `google_signin_stalled` → màn "Xác minh danh tính của bạn" / "Để bảo mật tài khoản của bạn, Google cần xác
    minh danh tính. Vui lòng đăng nhập lại" → `relogin_required=True, captcha_detected=False`.
  - = Google forced re-login (OAuth session bị vô hiệu), KHÔNG phải mail chết (notification "Gmail: 7 thư mới"
    vẫn về). Script fail-closed đúng: không tự nhập pass Google → dừng `[google_account_relogin_not_captcha]`.
  - Cần re-auth Gmail thủ công trên máy → chạy lại reg.

## OTP old-code loop (máy 2, 42) — PITFALL còn mở
- Script đọc "Code from recent already-open TikTok conversation: <code cũ>" từ conversation Gmail đang mở sẵn
  → nhập code cũ → TikTok báo "Mã xác minh email đã hết hạn" → script type lại code cũ vô hạn → PENDING.
- gmail-health KHÔNG trigger vì `code` không None (nhánh health chỉ chạy khi KHÔNG tìm được OTP nào).
- Cần implement: detect "đã hết hạn" trên màn TikTok → đóng conversation cũ + pull-refresh inbox → chỉ khi vẫn
  không có code mới mới fallback health check. (CHƯA có 2026-08-21.)
- Workaround thủ công: force-stop Gmail (`am force-stop com.google.android.gm`) để vào inbox sạch, rồi gọi
  health check trực tiếp.

## OTP rescue khi Outlook consent kẹt (máy 78)
- Outlook dính "Inapp UnifiedConsent" ("Ghi chú nhanh về tài khoản Microsoft", nút OK bottom bar landscape
  ~(960,865)) — tap ATX/coordinate không qua được; force-stop + reopen vẫn quay lại consent.
- RESCUE: bỏ qua Outlook app — gọi thẳng
  `read_tiktok_otp_from_graph_token(device_id, email, stt=stt, timeout=150)` từ `hotmail_provider` (import
  trực tiếp, signature `(device, email, *, token, client_id, token_file, client_id_file, stt, artifact_dir, timeout)`).
  Máy 78 trả OTP "448323" ngay. → nhập tay: tap field → `input text <code>` → Enter (không có nút Xác nhận).

## DOB picker TikTok (ngày sinh) — calibration
- 3 wheel: day x≈240, month x≈540, year x≈840 (y 1149-1546; nút Tiếp tục (540,1788)).
- PITFALL: swipe nhanh (dur 100-120ms) overshoot khủng (2026→1974 sau 22 lần vuốt), không kiểm soát được.
- CHUẨN: swipe chậm dur 300ms ≈ 3 năm/lần. Vuốt `840,1200→840,1560` GIẢM năm; `840,1500→840,1250` TĂNG năm.
- Sau Tiếp tục: popup "Xem lại ngày sinh của bạn" → OK (540,1184) → màn "Tạo mật khẩu" → "Tạo biệt danh"
  (Bỏ qua (126,150) hoặc nhập tên → popup "Đặt biệt danh?" → Xác nhận (750,1175)).
- Màn Tạo mật khẩu: field (540,486), yêu cầu 8-20 ký tự + chữ + số + ký tự đặc biệt; Tiếp tục (540,933);
  lưu ý `input text` có thể rớt ký tự `$` (escape shell) → dùng ký tự khác hoặc nhập từng phần.

## "Đăng nhập bằng mật khẩu" fallback (máy 2)
- Màn OTP hết hạn có link "Đăng nhập bằng mật khẩu" (390,1177) → nhập pass source.
- Kết quả "Mật khẩu sai" ⇒ email ĐÃ CÓ TikTok (nick cũ, pass khác) — KHÔNG đoán pass (rủi ro khóa nick),
  báo user quyết định. Đây là dấu hiệu source bị lẫn email cũ đã reg → rà tracking cũ theo mail.

## Safe workbook date-in-serial corruption
- `_detect_clean.py` trả `DETECTION_BLOCKED: TARGET_INVENTORY_CONFLICT: machine N` khi cột serial (col 2)
  của `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx` bị ghi NGÀY THÁNG thay vì serial (bug write tracking).
- Scan fix: `if val and ('/' in str(val) or '-' in str(val)) and len(str(val)) <= 12:` → restore serial thật.
- Đã gặp: máy 1 (row 6), 25 (150), 30 (180), 31 (184), 39 (232), 42 (251).

## Batch wrapper timeout
- subprocess timeout 450s QUÁ NGẮN cho reg flow — máy 23/42 bị kill giữa chừng dù đang tiến triển, kết quả
  lọc dòng output làm mất context trạng thái. Dùng ≥500s + kèm lock cleanup trước mỗi máy; chạy từng máy
  foreground/background riêng để theo dõi được.