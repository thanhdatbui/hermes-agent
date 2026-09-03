# boxtaikhoan.com — Hotmail 2 tier (2026-08-16)

Shop acc MMO Việt Nam (giá VND "đ"). Contact: `boxtaikhoan.com@gmail.com`, Zalo + Telegram group (t.me/BOXTaiKhoan). WooCommerce-style. curl bị bot-block (http 200 + size 0, exit 23) → dùng browser stack.

## Category page
`https://boxtaikhoan.com/category/hotmail` — "Hotmail 2" sản phẩm (cùng category còn Outlook 1, Gmail 1).
Product URL: `/product/<slug><id>` (vd `.../tai-khoan-hotmail-trusted-graphapi---live-vinh-vien-mail-khoi-phuc-fviainboxes---chua-qua-dich-vu24`). Lấy link thật bằng browser_console DOM: `[...document.querySelectorAll('a')].filter(a=>a.href&&a.href.includes('hotmail')&&!a.href.includes('category')).map(a=>a.href)`.

## Product 1 — 262đ, kho 44.058
"Tài Khoản Hotmail TRUSTED GraphAPI - Live Vĩnh Viễn, Mail Khôi Phục Fviainboxes - Chưa Qua Dịch Vụ"
- Live vĩnh viễn; mail khôi phục = temp mail **fviainboxes**; chưa qua dịch vụ.
- KHÔNG công bố định dạng/token → đọc mail/OTP không được (IMAP basic auth đã chết).
- URL: https://boxtaikhoan.com/product/tai-khoan-hotmail-trusted-graphapi---live-vinh-vien-mail-khoi-phuc-fviainboxes---chua-qua-dich-vu24

## Product 2 — 393đ, kho 118.707
"Tài Khoản Hotmail Trust - OAuth2 [IMAP/POP3/GRAPH] Live 12 đến 36 Months - Zin 100% - Còn Skip 7 Ngày"
- Dòng **"Định dạng : mail|pass|refresh_token|client_id"** → kèm refresh_token + client_id → đọc mail qua **Graph API** không cần password.
- Live 12–36 tháng; Zin 100% (chưa ngâm); còn skip 7 ngày (cửa sổ bảo hành — không đổi thông tin 7 ngày đầu).
- URL: https://boxtaikhoan.com/product/tai-khoan-hotmail-trust---oauth2-imappop3graph-live-12-den-36-months---zin-100---con-skip-7-ngay5113

## Khác biệt ra giá trị
Tier 2 đắt ~1.5× (393/262) nhưng **đáng giá cho bài toán tự động đọc OTP số lượng lớn**: token Graph API bypass được cả (a) IMAP basic auth đã chết của Microsoft lẫn (b) cụm recovery-OTP shared (thanhdatbui1995@gmail.com) của flow Outlook-app hiện tại. Tier 1 chỉ đọc được qua UI-tap (Outlook app) vì không có token.

## Ghi chú scraping
- Tab "Chi tiết sản phẩm" hiện heading + paragraph RỖNG trên snapshot — phần dài dưới là warranty template dùng chung mọi sp clone (24h bảo hành, "4 nguyên nhân kill clone": VPN/proxy bẩn, nhiều clone 1 IP, ngâm acc, login tool auto không ổn định, thay đổi fingerprint...). Đọc thật bằng body.innerText slice từ "Chi tiết sản phẩm" đến "CHÍNH SÁCH".
