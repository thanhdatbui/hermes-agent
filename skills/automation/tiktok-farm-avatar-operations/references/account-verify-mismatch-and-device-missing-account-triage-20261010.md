# Account Verify Mismatch & Device Missing Account Triage (2026-10-10)

## 1. Hiện tượng & Triệu chứng
Khi chạy runner upload avatar đơn máy (`run_tiktok_upload_avatar.ps1 -Tik <N> -ForceAvatarMachineList "<M>"`), quy trình chạy qua các bước:
- `[ACCOUNT_SWITCHER] Profile root opened via recovered core flow ✓`
- `[ACCOUNT_SWITCHER] Switcher opened via core ✓`
- `[ACCOUNT_SWITCHER] Target account selected via core ✓`
Nhưng ngay sau đó văng lỗi ở bước `ACCOUNT_READY`:
```text
[WARNING] Profile account verify pending: ACCOUNT_VERIFY_MISMATCH: Profile did not show the expected account; re-tapping Profile tab...
[ERROR] [ACCOUNT_SWITCHER_FAILED] ACCOUNT_READY verify failed: ACCOUNT_VERIFY_MISMATCH: Profile did not show the expected account. Cần MANUAL_REVIEW: kiểm tra TikTok đã login chưa, dismiss popup/onboarding thủ công rồi retry.
```

## 2. Bản chất Gốc rễ: Nick Chưa Đăng Nhập Trên Thiết Bị (Account Missing On Device)
1. **Lệch giữa Snapshot Web API vs Thực tế trên App:**
   - Trong `tiktok_tracker.db`, bảng `snapshots` vẫn có số liệu follower/like mới nhất trong ngày (ví dụ `@annapmfdh0a` có 35 followers, 259 likes vào 07:04 ngày 10/10/2026).
   - **Bẫy ngộ nhận:** Agent tưởng nick vẫn đang hoạt động bình thường trên điện thoại. Thực tế, bảng `snapshots` do tool scraper cào qua Web HTTP API bên ngoài, hoàn toàn KHÔNG phản ánh phiên đăng nhập trong app TikTok trên thiết bị vật lý.
2. **Hiện tượng trong Switcher Sheet:**
   - Trên TikTok Android, một máy có thể đăng nhập tối đa 8 tài khoản (Tik 1 đến Tik 8).
   - Trong sự cố Máy 44: Switcher sheet chỉ có 7 tài khoản (`maralbbct24`, `v.th.thoooo`, `ngongan1906`, `kellybxm52j`, `olinasbnetu`, `miumiu10434`, `oquangduong7604`).
   - Tài khoản mục tiêu Tik 6 (`@annapmfdh0a`) **hoàn toàn vắng mặt / chưa đăng nhập** trong ứng dụng TikTok.
3. **Tại sao `select_exact_account` vẫn báo success?**
   - Hàm `select_exact_account` có fallback scroll tìm account. Nếu không khớp hoặc tap trượt, switcher đóng lại và profile vẫn giữ nguyên nick cũ (ví dụ `@maralbbct24`).
   - Bước `ACCOUNT_READY` kiểm tra text profile và phát hiện không phải nick mong đợi $\to$ ném `ACCOUNT_VERIFY_MISMATCH`.

## 3. Quy trình Triage Chuẩn O(1)
1. **Kiểm tra danh sách nick trong Switcher:**
   - Dùng script an toàn bọc `with_device_lock.py`:
     ```python
     from automation_core.tiktok.account_switcher import open_switcher, list_accounts, _back
     xml = open_switcher(adapter)
     accounts = list_accounts(xml)
     print("Accounts in switcher:", accounts)
     _back(adapter)
     ```
2. **Phân loại kết quả:**
   - Nếu nick đích **CÓ** trong `accounts`: Lỗi do click trượt hoặc layout header (chuyển sang triage layout/scroll).
   - Nếu nick đích **KHÔNG CÓ** trong `accounts`: Xác định chính xác lỗi **`ACCOUNT_MISSING_ON_DEVICE`**.

## 4. Kỷ luật Báo cáo & Xử lý (Chống Báo Xong Ảo & Chống Chữa Lợn Lành Thành Lợn Què)
- **CẤM BÁO XONG HOẶC GỠ PENDING:** Giữ nguyên trạng thái `PENDING` trong `avatar_replace_queue` (`tiktok_tracker.db`) và cột Avatar trong `Tik<N>.xlsx`.
- **Báo cáo BLOCKED hợp lệ:** Báo cáo trạng thái `BLOCKED (ACCOUNT_MISSING_ON_DEVICE)` kèm bằng chứng:
  * Full screenshot Profile hiện tại (`account-switcher-profile.png`) cho thấy nick đang hiển thị trên máy.
  * Danh sách các tài khoản đang thực tế có trong Switcher (để Operator thấy rõ nick bị thiếu).
  * Thông tin credentials từ `taikhoan_dat_v2_updated .xlsx` (ID, Hotmail, Pass) để chuyển giao sang luồng login (`reconcile_tiktok_accounts.py`).
- **Đã hoàn tất tầng nguồn:** Xác nhận rõ tầng file đĩa (`avatar.jpg` 2 đầu kho) và tầng metadata (`Keyword Video`, `Hashtag Pool`, `video gốc = Folder Video`) đã được chuẩn hoá 100%, sẵn sàng tự động nạp ngay khi nick được đăng nhập lại vào máy.
