# RULE 3 BƯỚC FIX LỖI UI (user chốt 2026-08-10)

## Ladder chuẩn
- B1: ATX-kill (uiautomator recovery)
- B2: force-stop + relaunch app — TỐI ĐA 1 lần
- B3: reboot máy (soft reboot) — TỐI ĐA 1 lần
- Sau B3 cạn → coordinate fallback có evidence → fail thì MANUAL_REVIEW

## Budget theo máy trong turn
- Mỗi máy được đúng **1 relaunch + 1 reboot** toàn bộ turn chạy của nó.
- Mọi lần lỗi lặp lại SAU ĐÓ: chỉ ATX-kill + coordinate fallback — KHÔNG relaunch/reboot nữa.
- Lỗi cùng chỗ sau đủ budget = thất bại. Lỗi KHÁC chỗ (state/signature khác) được chạy lại chuỗi, vẫn nằm trong budget tổng.
- Handler đặc thù fail vì UI/dump phải route vào ladder, KHÔNG dừng sớm MANUAL_REVIEW.

## Splash-stuck
- Wait feed (90s) hết mà TikTok foreground không vào feed → đóng Recent + relaunch (không tính B2), budget riêng 2 lần.

## Pitfall: kwarg core API phải đúng tên
- automation-core `reboot_and_restore` dùng `wait_for_proxy_ready_after_reboot=...`
- KHÔNG dùng `wait_for_proxy_ready_before_post_reboot` (lỗi TypeError cũ, máy không reboot).
- Trước khi gọi hàm core mới: kiểm tra `inspect.signature()` thay vì đoán tên tham số.