# BoxTaiKhoan Hotmail Procurement & Auto-Fill for TikTok Reg

## 1. BoxTaiKhoan API Purchase Contract

Endpoint: `POST https://boxtaikhoan.com/ajaxs/client/product.php`
Headers:
- `Content-Type: application/x-www-form-urlencoded`
- `X-Requested-With: XMLHttpRequest`
- `User-Agent: Mozilla/5.0 ...`

Parameters:
- `action`: `buyProduct`
- `id`: `60` (Tài Khoản Hotmail Trust - OAuth2 [IMAP/POP3/GRAPH] Live 12-36 Months - Zin 100% - Còn Skip 7 Ngày)
- `variant_id`: `0`
- `amount`: `<number_of_accounts>`
- `coupon`: `""`
- `api_key`: `<API_KEY>`
- `user_input`: `"{}"`

Output shape:
```json
{
  "status": "success",
  "msg": "Tạo đơn hàng thành công!",
  "trans_id": "...",
  "data": [
    "email@hotmail.com|password|refresh_token|client_id"
  ]
}
```

## 2. Token Verification & Exchange
- Token from BoxTaiKhoan is full MSA format (`M.C5...`, length ~450–525 chars).
- Do NOT buy from providers truncating token to ~100 chars (fails `AADSTS70000`).
- Test token validity before writing to sheets:
  `exchange_refresh_token(token, client_id)` -> must return valid access token (length > 1000).

## 3. Storage & Safe Sync Workflow
1. Append raw string to `D:\Taadaa\Hotmail\hotmail_all_60_bought.txt`.
2. Format row for `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`:
   `[stt, email, password, None, None, None, None, 'YYYY-MM-DD', refresh_token, client_id, None]`
   - STT: integer, centered
   - Dates/Codes (col 6, 7, 8, 11): centered
   - Email/Pass/Token/ClientID (col 2, 3, 4, 5, 9, 10): left-aligned
3. Run `_detect_clean.py` to verify target eligibility and check for `TARGET_INVENTORY_CONFLICT`.
4. Run `_run_all_targets.py` with `--max-workers`.
5. Apply deferred JSON results with `scripts/apply_deferred_tracking_results.py`.
6. Run `sync-safe-workbook.py` to refresh `taikhoan_run_safe.xlsx`.
