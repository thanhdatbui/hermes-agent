# TikTok Registration Batch Ops & Vietnam Naming Rules (2026-08-18)

## 1. Batch Concurrency Rule
- Khi user yêu cầu "chạy reg các máy...", kích hoạt chạy song song batch toàn bộ (`_run_all_targets.py --full-scope-takeover`).
- **CẤM** block/pause các máy khác để chờ 1 máy lẻ test xong. Mỗi máy chạy độc lập theo worker riêng.

## 2. Token Graph API vs Outlook App Priority
- Đối với Hotmail/Outlook mailboxes:
  - Nếu có `refresh_token` + `client_id` trong danh sách token: **BẮT BUỘC** ưu tiên đọc OTP từ Microsoft Graph API trên PC (nhanh, song song, không bị app che, không tap nhầm thư cũ hết hạn).
  - **CHỈ** fallback vào mở Outlook app trên thiết bị khi mailbox không có token trong hệ thống.

## 3. Quy tắc Việt hóa Tên hiển thị (Display Name) & Biệt danh (@handle)
- **Tên hiển thị (Display Name):**
  - Rút ngắn prefix từ email và map sang tên Việt gần âm (vd: `Gaye...` → Gia, `Lilyan...` → Linh, `Debi...` → Diệp, `Daunte...` → Đan, `Steven...` → Thịnh).
  - Nếu không có trong map, chọn ngẫu nhiên từ danh sách tên Việt phổ biến (*Minh, Linh, Hà, An, Chi, Lan, Hân, Vy, Khoa, Nam, Tuấn, Dũng, Phong, Huy, Hoàng, Thảo, Trang, Mai, Quỳnh, Hương, Ngọc...*).
- **Biệt danh (@username/handle):**
  - Chế theo tên Việt hóa + số đuôi tự nhiên (dạng `gia4667`, `linh_271`, `dan.2198`...) thay vì bê nguyên chuỗi chữ cái tiếng Anh dài ngoằng.

## 4. Post-Registration Cleanup
- Ngay sau khi reg hoàn tất và ghi nhận tracking (`write_deferred_tracking_result` hoặc `upsert_tracking_account`):
  - `adb shell am force-stop com.ss.android.ugc.trill`
  - `adb shell input keyevent 3` (KEYCODE_HOME)
  - Trả máy về Home screen sạch sẽ.

## 5. UI Safeguards
- **Email Continue button:** Khi tìm nút "Tiếp tục" / "Tiếp theo", bỏ qua các node text điều khoản dịch vụ / chính sách quyền riêng tư (`dieu khoan`, `quyen rieng tu`) để tránh tap nhầm làm bung modal điều khoản.
- **Home Feed vs Profile screen:** Khi kiểm tra `_is_home_feed_xml()`, thêm negative guard nếu có `them tieu su`, `sua ho so`, `anh ho so` để không nhận nhầm màn Profile cá nhân thành Home feed.
