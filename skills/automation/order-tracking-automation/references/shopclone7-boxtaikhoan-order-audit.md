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

### 3. Host Chrome Session Expiration & Google OAuth Iframe
- BoxTaiKhoan requires an authenticated session for `/product-orders`, `/client/logs`, `/document-api`.
- When accessing via user's Chrome (`Profile 4`), expired cookies trigger a 302 redirect to `/client/login`.
- The Google Sign-In button is rendered inside a cross-origin iframe (`Sign In - Google Accounts`). Synthetic background clicks or coordinates will not pass browser security to trigger Google SSO.
- **Action:** Notify the user cleanly that the session expired on their open tab so they can complete the single login click, then resume automated scraping.
