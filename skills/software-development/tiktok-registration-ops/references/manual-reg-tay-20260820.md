# Manual reg tay + recoveries — session 2026-08-20/21 (máy 2, 23, 31, 34, 42, 77, 78, 79)

## Kết quả session
Batch reg hotmail/gmail đêm 20→21/08/2026: **12/12 nick SUCCESS đều có PASS thật**. Máy 78 được reg TAY hoàn chỉnh vì script kẹt Outlook consent — dùng làm recipe chuẩn cho email chưa có TK.

## Trả lời câu hỏi "TikTok có cho qua k bắt nhập pass k?"
- Reg **NICK MỚI** (email chưa có TK): flow = OTP verify → DOB → **"Tạo mật khẩu"** → nickname. **LUÔN có màn password.**
- "Không có màn password (flow email-only/OTP)" CHỈ xảy ra khi LOGIN tài khoản ĐÃ CÓ.
- ⇒ Trả lời user: không có máy nào qua mà không bắt nhập pass; kèm bằng chứng cột PASS đầy đủ trong tracking.

## Reg tay máy 78 (recipe đầy đủ) — email chưa có TK
1. Login form: tab "Email/tên người dùng" (700,288) → ô email có sẵn → tap "Tiếp tục" (540,1806).
2. TikTok báo **"Tài khoản không tồn tại"** → tap **"Tạo tài khoản mới"** (300,738) → màn Đăng ký (tabs Điện thoại/Email, email giữ nguyên).
3. Tap "Tiếp tục" (540,813) → màn **"Kiểm tra email của bạn"** (countdown 49s; nút "Gửi lại mã" rid=`ktj` bounds [96,858][339,975]).
4. OTP: đọc qua Graph **trực tiếp** `read_tiktok_otp_from_graph_token(device, email, stt=78, timeout=150)` (import từ `hotmail_provider`) → tap ô nhập (540,738) → `input text <code>` → tự nhảy sang DOB.
5. DOB picker ("Ngày sinh của bạn là ngày nào?"):
   - 3 cột: day [120,360] / month [420,660] / year [720,960] tại y 1149-1546; nút Tiếp tục (540,1788).
   - Year column: **swipe CHẬM 300ms (840,1200→840,1560) = −3 năm/lần**; swipe nhanh 100ms LOẠN (quan sát: 1966→2011→2026→1974). Dùng chậm + dump lại sau mỗi 2 lần cho chắc.
   - Sau Tiếp tục → popup "Xem lại ngày sinh của bạn / Bạn đã nhập: ... / OK" → tap **OK (540,1184)** → quay lại DOB đã điền → tap Tiếp tục (540,1788) LẦN NỮA.
6. "Tạo mật khẩu": tap ô (540,486) → `input text` — **`$` bị bash nuốt** (G9\$kP#7qW2 chỉ còn 7 dấu •) → dùng bộ an toàn `# ? ! @` + chữ + số, ≥8 ký tự, đủ 1 chữ/1 số/1 ký tự đặc biệt; **verify số dấu • = độ dài thật** trước khi Tiếp tục (540,933).
7. "Tạo biệt danh" → tap "Bỏ qua" (126,150) → main feed.
8. Chạy lại `python social_reg_v1.py 78 --resume --email <mail> --ss` để fill display name + ghi tracking. Nếu "device lock active" → xóa lock file trước.

## OTP hết hạn loop (máy 2, 42) — luật dừng
- Extractor đọc từ "recent already-open TikTok conversation" trong Gmail → **trả code CŨ (954753 / 740813) hết hạn** lặp vô hạn dù timestamp cập nhật.
- Màn báo "Lỗi mã xác minh email đã hết hạn" / "Mã xác minh email đã hết hạn" → bấm "Gửi lại mã"; NHƯNG mail mới có thể KHÔNG về (nằm tab Promotions/Social, hoặc delay).
- **Luật dừng**: sau 2 lần "Gửi lại mã" không thấy code MỚI → mail-delivery issue → STOP + báo user, CẤM loop vô hạn.
- Máy 42 Gmail onboarding popups chặn mailbox check: "Tuỳ chỉnh thao tác vuốt" → "Không, cảm ơn" (715,1120); popup dưới "Tiếp tục" (300,1700) / "Không, cảm ơn" (650,1700). ⚠️ Bấm nhầm có thể mở màn SOẠN EMAIL → Back liên tục về inbox.

## ViChanger diagnostics (máy 34)
- `dumpsys package vn.vichanger.app` → `enabled=0` (bị disable) → `pm enable vn.vichanger.app`.
- Mở app → dialog **"No LSPosed access !!!"** (LoginActivity; OK (1400,727)) → **root/LSPosed hỏng → KHÔNG fix được qua adb → block máy** (GET_IP vẫn `result=0`).
- Reboot không giúp; notification "Đã kết nối với VPN của Vi Changer" KHÔNG = GET_IP hợp lệ.

## Inapp UnifiedConsent (Outlook) — máy 78
- Landscape 1920x1080 (máy đang xoay ngang!): consent "Ghi chú nhanh về tài khoản Microsoft của bạn" — OK (960,865) tap KHÔNG ăn, Back không thoát, force-stop + relaunch vẫn còn.
- **Đừng chiến đấu với WebView** → force-stop Outlook + đọc OTP qua Graph (mục trên). Không mở lại Outlook trên máy đó trong session.

## Locks & retries
- `DEVICE_LOCK_ENABLED=1`: run bị kill/timeout để lại lock file → lần chạy sau SKIP "device lock active" → xóa `*.lock.json` trong `C:\Users\Kibe\.codex\device-locks\` trước khi re-run.
- User rule (nhắc lại 2026-08-21): **trong batch reg giữ lock tới khi SUCCESS hoặc user ra lệnh mở** — chỉ dọn lock giữa các lần retry chủ động, không mở lock hàng loạt.

## Safe workbook audit (trước batch)
- `_detect_clean.py` báo `DETECTION_BLOCKED: TARGET_INVENTORY_CONFLICT` khi `taikhoan_run_safe.xlsx` cột Device ID (col 2) bị ghi NGÀY (`20/08/2026`) thay vì serial — audit TOÀN BỘ các row (lần này dính máy 1, 25, 30, 31, 39, 42), sửa serial đúng rồi mới chạy detect.