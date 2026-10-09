# Hotmail Purchasing & Workbook Allocation Protocol

## 1. Script & Repository Locations
- Primary script: `D:\Taadaa\tools\buy_hotmail.py`
- Mirrored/synced copy: `D:\Taadaa\AI-Tools\tools\buy_hotmail.py`

## 2. Target Workbooks & Machine Ranges
Taadaa Phone Farm chia làm 2 cụm máy chính:
- **Kibe Pool (Máy 1..80)**:
  - Workbook: `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`
  - Sheet: `Gmail Accounts` (hoặc sheet 0)
  - CLI usage:
    ```bash
    # Mua N accounts và phân bổ tự động vào các máy có ít mail nhất trong dải 1..80
    python D:\Taadaa\tools\buy_hotmail.py --append-kibe 10

    # Mua tài khoản và gán đích danh vào danh sách máy thiếu
    python D:\Taadaa\tools\buy_hotmail.py --append-kibe 3 --target-machines 1,2,5
    ```
- **Admin Pool (Máy 201..280)**:
  - Workbook: `D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx`
  - Sheet: `Gmail Accounts`
  - CLI usage:
    ```bash
    python D:\Taadaa\tools\buy_hotmail.py --append-admin 10
    ```

## 3. Workbook Schema (11 Columns)
Mỗi tài khoản được nạp với định dạng 11 cột khớp hoàn toàn giữa 2 workbook:
1. `số máy` (int, 1..80 hoặc 201..280)
2. `tài khoản gmail` (email hotmail/outlook/gmail)
3. `pass mail`
4. `2fa` (None nếu không có)
5. `mail khôi phục` (recovery_email hoặc None)
6. `ngày tháng năm sinh` (None)
7. `ngày tạo` (Timestamp chuỗi `YYYY-MM-DD HH:MM:SS`)
8. `mã phụ hồi` (None)
9. `token` (refresh_token OAuth2)
10. `client_id` (Microsoft OAuth2 app client id)
11. `trạng thái` (None / LIVE / DIE / CHECKPOINT)

## 4. Purchasing Providers & Fallback
- `boxtaikhoan` (Default ưu tiên, product 129 Hotmail OAuth2)
- `clonefbig` (Fallback tự động khi BoxTaiKhoan hết hàng hoặc lỗi, product 3470)
- Gọi mua tuần tự `amount=1` để lấy thẳng payload phân tách pipe `mail|pass|refresh_token|client_id|recovery_email`.
- Tự động kiểm tra token qua endpoint Microsoft Graph OAuth2 (`https://login.microsoftonline.com/consumers/oauth2/v2.0/token`) trước khi lưu.
