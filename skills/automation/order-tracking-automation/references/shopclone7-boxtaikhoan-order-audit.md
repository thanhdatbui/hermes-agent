# ShopClone7 & BoxTaiKhoan Order Audit & Traceability

## Overview

When tracing account purchase sources, batch origins, or looking up transaction logs on MMO account shops built on ShopClone7 / CMSNT (e.g. `boxtaikhoan.com`):

## Key Invariants & Pitfalls

### 1. Anti-Premature Deletion Trap (User Rule)
- **UI Disclaimer:** ShopClone7 displays a prominent warning banner:
  > *"Lịch sử đơn hàng trên hệ thống chỉ được lưu trong 3 ngày kể từ thời điểm mua. Sau thời gian này, đơn hàng dữ liệu có thể bị xóa và không thể khôi phục."*
- **Reality:** This is a boilerplate UI disclaimer meant to limit support liability for old purchases. The underlying backend MySQL tables (`product_order`, `product_sold`, `logs`) keep records indefinitely unless the shop owner manually purges them.
- **Rule:** Never tell the user that orders or accounts "đã bị xóa vĩnh viễn theo chính sách 3 ngày" based solely on reading the disclaimer. Always check the actual order list (`/product-orders`), paginate back (`?page=N`), or inspect `/client/logs` / `/client/transactions`.

### 2. ShopClone7 API 404 Error Behavior
- Endpoint `GET /api/order.php?api_key=<KEY>&order=<TRANS_ID>`:
  - If `<TRANS_ID>` does not match any record for the user, `api/order.php` invokes `http_response_code(404); die(json_encode(['status' => 'error', 'msg' => 'Đơn hàng không tồn tại']));`.
  - When hosted behind Cloudflare or custom Apache `.htaccess` error handling, the HTTP 404 status triggers the site's full HTML 404 error page (`<title>404 — Không tìm thấy trang</title>`).
  - **Do not misinterpret this as a missing API file**: the API script exists and executes; the 404 simply denotes record not found for that specific query.

### 3. Host Chrome Profile Disambiguation & Session Expiration
- **Profile Disambiguation:**
  - `Profile 3` (Username: đạt, Email: `thanhdatbui1995@gmail.com`): Contains saved credentials and Google OAuth for `boxtaikhoan.com` (account `thanhdatbui1995`).
  - `Profile 4` (Username: Kal, Email: `jinrakal@gmail.com`): Personal profile.
  - To open or inspect BoxTaiKhoan via Chrome, always explicitly target `--profile-directory="Profile 3"`.
- **Session Expiration & Google OAuth Iframe:**
  - BoxTaiKhoan requires an authenticated session for `/product-orders`, `/client/logs`, `/document-api`.
  - When accessing via Chrome, expired cookies trigger a 302 redirect to `/client/login`.
  - The Google Sign-In button on the web page is rendered inside a cross-origin iframe (`Sign In - Google Accounts`). Synthetic background events cannot penetrate the cross-origin iframe sandbox.
  - **Resolution:** Launching `chrome.exe --profile-directory="Profile 3" https://boxtaikhoan.com/product-orders` opens the Google Account Chooser popup, where clicking the top account (`thanhdatbui1995@gmail.com`) automatically restores the session.
