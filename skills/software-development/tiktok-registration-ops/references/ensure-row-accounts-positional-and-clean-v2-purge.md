# Canonical ensure_row_accounts.py & gmail_clean_v2.xlsx Purge Rules (2026-10-04)

## 1. User Directive (Hard Invariant): gmail_clean_v2.xlsx CHỈ LƯU GMAIL LIVE
- File `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx` là kho mail live phục vụ cấp phát.
- Khi một tài khoản Gmail bị DIE (bao gồm checkmail.live báo DIE, hoặc dính Google Phone Challenge `challenge/iap` chặn login):
  * **BẮT BUỘC xóa hoàn toàn dòng đó khỏi `gmail_clean_v2.xlsx`** (`ws.delete_rows(r, 1)`).
  * **CẤM TUYỆT ĐỐI** chỉ ghi chữ "DIE" vào Cột 11 (trạng thái) rồi để lại dòng trong file.
  * Thông tin DIE chỉ được phép lưu vết lịch sử tại `D:\OneDrive\TaadaaData\kibe\gmail_die_tong.txt`.
- Khi tài khoản gắn với slot trên `taikhoan_run_safe.xlsx` bị DIE:
  * Phải xóa trắng slot (`tiktok_id=""`, `video_count=None`, `created_date=None`).
  * CẤM ghi chuỗi `_DIE` vào cột tiktok_id (vì `ensure_row_accounts.py` sẽ không nhận diện là slot rỗng cần reg bù).

## 2. Canonical CLI Syntax: ensure_row_accounts.py
- Script `D:\Taadaa\tools\ensure_row_accounts.py` định nghĩa `row` là **positional argument**:
  ```python
  parser.add_argument("row", type=int, choices=range(1, 9))
  ```
- **Lệnh chuẩn:**
  ```bash
  python D:/Taadaa/tools/ensure_row_accounts.py 8 --machines 3
  ```
- **CẤM:** Truyền `--row 8` vì argparse sẽ báo lỗi unrecognized argument.
- Khi reg bù cho Row N, pipeline tự động bốc Hotmail/Outlook từ `gmail_clean_v2.xlsx` hoặc gọi `buy_hotmail.py` mua gói OAuth2 box tai khoan, tuyệt đối không dùng Gmail.
