# Quy Trình Đối Soát & Backfill Slot Trống (Lệch Excel Khi Máy Đã Đủ 8 Acc)

## 1. Dấu Hiệu Nhận Biết
- Alert Preflight Reg bù báo:
  `❌ Thất bại: Máy N: Máy đã đủ 8 acc (Lệch Excel - Cần kiểm tra backfill)`
- Bản chất: Preflight thấy ô Excel (Row/Slot N) bị rỗng (`None`) nên định gọi reg bù. Nhưng khi kiểm tra thiết bị thì app TikTok đã có đủ 8 acc (chạm trần `MACHINE_FULL_8_ACCOUNTS`).

## 2. Các Bước Điều Tra O(1) & Truy Tìm Nguồn Gốc
1. **Kiểm tra Artifacts đăng ký bị kẹt (`FAILED_SYNC_OSError` - Nguyên nhân phổ biến nhất)**:
   - **Gốc rễ sự cố**: Khi `_run_all_targets.py` hoàn thành batch, hàm auto-sync gọi `_acquire_workbook_write_lock` (dùng Win32 `CreateFileW` với `dwShareMode=0` độc quyền tuyệt đối). Nếu OneDrive đang đồng bộ nền hoặc Excel đang mở, tiến trình văng `FAILED_SYNC_OSError`. Script chỉ in warning và thoát, KHÔNG có cơ chế retry hay nạp bù, khiến hàng loạt tài khoản thành công bị kẹt lại dưới dạng JSON.
   - **Cách tra cứu O(1) tìm kết quả kẹt**:
     Quét 15-20 run gần nhất trong `D:/Taadaa/runtime/<cluster>/artifacts/runs/social-batch-all/`:
     Tìm file `batch_*/stt_<N>/tracking_result_*.json` hoặc đọc `all_results.json` lọc `"stt": N, "status": "SUCCESS", "workbook_write": "FAILED_SYNC_OSError"`.
     Khi tìm thấy: Trích xuất ngay `tiktok_id`, `email`, `mail_password`, `created_date`, `serial` để nạp bù vào Excel.
2. **Tra cứu CSDL `D:/Taadaa/data/tiktok_tracker.db`**:
   - `SELECT username, may, tik FROM farm_account_info WHERE may=N ORDER BY tik;`
   - Xác định danh sách 8 tài khoản thực tế đang gán với Máy N (chú ý slot bị trống trên Excel tương ứng với Tik mấy).
3. **Kiểm tra lịch sử bản sao lưu Excel (`archive_history`)**:
   - Thư mục: `D:/OneDrive/TaadaaData/<cluster>/workbook-backups/archive_history/taikhoan_dat_v2_updated*.bak*`
   - Quét tìm thời điểm dòng đó bị xóa hoặc bị di chuyển sang máy khác (do sự cố nick ký sinh bị gán nhầm sang máy khác rồi bị cắt dòng mà chưa hoàn lại).
   - Trích xuất: ID, Mật khẩu TikTok, Email, Mật khẩu mail, Ngày tạo.

## 3. Quy Trình Backfill Đồng Bộ (Bắt Buộc Đủ 3-4 Nơi Chuẩn Theo Cluster)
Khi khôi phục một tài khoản vào máy, PHẢI cập nhật đồng bộ tất cả các file Master theo đúng Cluster của máy:
- **Cluster Kibe (Máy 1 - 80):** Thư mục `D:/OneDrive/TaadaaData/kibe/`
  * Công thức STT Tik/Folder: `(M - 1) * 8 + slot` (slot 1..8)
- **Cluster Admin (Máy 201+):** Thư mục `D:/OneDrive/TaadaaData/admin/`
  * Công thức STT Tik/Folder: `(M - 201) * 8 + slot` (slot 1..8). CẤM NHẦM LẪN nhân thẳng `M * 8` tạo ra số Tik rác (1600-2200) làm bộ lọc restore xóa nhầm!

Các file Master bắt buộc cập nhật:
1. **Master Tracking**: `D:/OneDrive/TaadaaData/<cluster>/taikhoan_dat_v2_updated .xlsx`
   - Sheet: `Tài Khoản`.
   - Vị trí: Dòng tương ứng của Máy N và STT Tik (Folder Video).
   - Điền: Cột C (ID), Cột D (PASS), Cột F (GMAIL), Cột G (PASS MAIL), Cột I (NGÀY TẠO).
2. **Safe Workbook**: `D:/OneDrive/TaadaaData/<cluster>/taikhoan_run_safe.xlsx`
   - Sheet: `Accounts`.
   - Điền: Cột ID và Cột Ngày Tạo tại đúng Slot (1..8) của Máy N.
3. **Tik Slot Workbook**: `D:/OneDrive/TaadaaData/<cluster>/Tik<Slot>.xlsx` (Ví dụ Tik5.xlsx nếu là slot 5)
   - Điền: Cột C (ID) của dòng Máy N.
4. **Đồng bộ CSDL SQLite farm_account_info**:
   - Chạy script chuẩn: `python D:/Taadaa/tools/sync_farm_account_info.py`
   - Đảm bảo mapping (Máy, Tik) trên SQLite `tiktok_tracker.db` được cập nhật đồng nhất 1:1 từ file tổng Master `taikhoan_dat_v2_updated .xlsx` theo công thức $\text{Tik} = ((\text{Folder}-1) \pmod 8) + 1$, giúp Dashboard hiển thị đúng badge `M{may} · T{tik}`.
5. **CẤM GÁN LỆCH MÁY / CHỐNG TÀI KHOẢN KÍ SINH (PARASITE ACCOUNT PREVENTION):**
   - Tài khoản của máy nào (được cấp mail theo STT trong `gmail_clean_v2.xlsx`) BẮT BUỘC KHÔI PHỤC VỀ ĐÚNG MÁY ĐÓ.
   - TUYỆT ĐỐI CẤM đem tài khoản của máy này gán sang máy khác để "chữa cháy" làm máy đủ số lượng. Gán sai máy sẽ dẫn đến lệch proxy, lệch device ID và biến tài khoản thành "kí sinh", gây lỗi nghiêm trọng khi chạy automation video/swipes.
6. **Dọn sạch tàn dư máy cũ (Nếu nick từng bị move nhầm)**:
   - Nếu nick bị di chuyển nhầm sang dòng của máy khác (ví dụ Máy 61), phải xóa trắng thông tin tài khoản ở dòng đó (trả về `None`), chỉ giữ nguyên cột Máy, Folder, Device ID để giải phóng slot cho máy đó.
7. **Bẫy Trùng Lặp Chéo Sau Khi Logout Nick Ký Sinh (Cross-Machine Duplicate Trap)**:
   - **Hiện tượng**: Nick ký sinh (ví dụ `@cyennffqko8`) từng xuất hiện trên Máy A (Máy 76) do lỗi đăng ký/đổi nick cũ. Dù sau đó script đã tap logout nick khỏi máy thật Máy A, nhưng file Master (`taikhoan_dat_v2_updated .xlsx`) và file `Tik<N>.xlsx` của Máy A vẫn còn lưu chuỗi ID cũ.
   - **Hậu quả**: Khi Máy B (Máy 36 - máy chính chủ) được backfill nick này vào, hệ thống tồn tại 2 bản ghi cùng username trên 2 máy khác nhau. Lập tức `excel_preflight_validator.py` kích hoạt chặn toàn bộ cron sync runtime:
     `[FAIL] Trùng lặp tài khoản 'X': xuất hiện tại TikA.xlsx và TikB.xlsx`.
   - **Kỷ luật BẮT BUỘC trước khi backfill (Pre-Backfill Duplicate Scan)**:
     * Trước khi ghi ID vào bất kỳ dòng nào, BẮT BUỘC quét toàn bộ Master Sheet xem ID đó đã từng tồn tại ở dòng nào khác chưa.
     * Nếu tìm thấy ID ở máy cũ: Lập tức CLEAR (set `None` cho ID, Pass, Mail, PassMail, CreatedDate) trên dòng của máy cũ trong Master, Tik*.xlsx và `taikhoan_run_safe.xlsx`.
     * **Quy trình 3 file đồng bộ chuẩn hóa (Atomic 3-File Cleanup)**:
       1. `taikhoan_dat_v2_updated .xlsx` (sheet `Tài Khoản`):
          - Clear cột 3 (ID), 4 (PASS), 5 (2FA), 6 (GMAIL), 7 (PASS MAIL), 8 (DOB), 9 (NGÀY TẠO), 11, 12 (PASS CHATGPT) = `None`.
          - BẢO TOÀN: cột 1 (Máy), cột 2 (Folder Video), cột 10 (device ID).
       2. `Tik<N>.xlsx` (sheet active, N = `((Folder - 1) % 8) + 1`):
          - Set cột 3 (ID) = `None`.
          - Set cột 8 (Video Đã Đăng) = `0`.
          - Set cột 9 (Kiểm Tra Dữ Liệu) = `'MISSING_ID'`.
          - BẢO TOÀN: cột 1 (Máy), cột 2 (device ID), cột 4 (Folder Video), cột 5 (video gốc), cột 6 (Keyword), cột 7 (Hashtags).
       3. `taikhoan_run_safe.xlsx` (sheet `Accounts`):
          - Set cột 3 (ID) = `None`.
          - Set cột 4 (Video Đã Đăng) = `0`.
          - Set cột 5 (Ngày Tạo) = `None`.
          - BẢO TOÀN: cột 1 (May), cột 2 (Device ID).
   - **Kiểm chứng Invariant bắt buộc sau khi Backfill / Cleanup**:
     * Ngay sau khi lưu file Excel, BẮT BUỘC chạy validator:
       `python D:/Taadaa/tools/excel_preflight_validator.py --excel-dir D:/OneDrive/TaadaaData/<cluster> --exit-on-error`
     * Chỉ được coi là hoàn tất khi validator trả về exit code 0 (`0 lỗi FAIL, 0 cảnh báo WARN`).
     * Trigger lại cron sync để xác nhận thoát lỗi: `python "C:/Users/Kibe/AppData/Local/hermes/scripts/taikhoan_sync_cron_launcher.py"`.
8. **Bẫy Dọn Excel Dở Dang Chưa Đăng Xuất Máy Thật (Half-Cleaned Parasite Trap)**:
   - **Hiện tượng**: Operator/Agent phát hiện duplicate chéo (`@cyennffqko8` ở M36 và M76), vội vã clear slot trên Master Excel, `Tik*.xlsx` và `taikhoan_run_safe.xlsx` để validator báo PASS. Tuy nhiên, trên thiết bị vật lý Máy A (M76), nick ký sinh vẫn còn lưu phiên trong app TikTok.
   - **Hậu quả**: Slot trên Excel bị trống (`None`) khiến `ensure_row_accounts.py` lập tức phát hiện máy thiếu nick và điều động reg bù. Khi app mở Switcher, thiết bị vẫn đang kẹt cứng 8 nick vật lý -> ẩn nút *"Thêm tài khoản"* -> văng alert đỏ `[04_add_account] MACHINE_FULL_8_ACCOUNTS: Máy đã đủ 8 acc (Lệch Excel - Cần kiểm tra backfill)`.
   - **Kỷ luật BẮT BUỘC (Physical Logout Before Reg-Bù)**:
     * Khi dọn nick ký sinh khỏi Excel, BẮT BUỘC phải thực hiện ngay quy trình targeted logout trên thiết bị vật lý: mở Switcher -> switch sang nick ký sinh -> vào Cài đặt -> cuộn đáy bấm Đăng xuất -> xác nhận popup.
     * Kiểm chứng 2 lớp (WinRT OCR + atx-agent XML) xác nhận nick ký sinh đã biến mất và nút *"Thêm tài khoản"* đã xuất hiện trở lại tại đáy Switcher (hoặc số nick còn đúng 7).
     * Ghi nhận key `m<N>_<username>: DONE` vào `D:/Taadaa/runtime/<cluster>/cron-state/parasite_reconcile_state.json`.
9. **Bẫy Khẳng Định "Đã Hết Ký Sinh" Khi Chỉ Nhìn Excel PASS & Danh Sách 14 Cặp Nick Reg Trùng Lịch Sử (User Correction 2026-10-02)**:
   - **Bản chất khiến "cứ vài ngày lại lòi ra 1 acc"**:
     * `excel_preflight_validator.py PASS 100%` chỉ chứng minh trong các file Excel không có dòng nào trùng lặp. Nó **hoàn toàn không chứng minh** trên thiết bị thật đã sạch nick ký sinh!
     * Toàn bộ nick ký sinh trên farm bắt nguồn từ một tập hữu hạn: **14 tài khoản bị bốc trùng email Hotmail** trong các batch reg cũ ngày 25–26/08/2026 (`artifacts/runs/social-batch-all/*/tracking_result_*.json`) do chạy đa luồng chưa có khóa phân bổ mail thời gian thực.
     * Khi sửa Excel gán cho 1 máy chính chủ, máy phụ vẫn âm thầm ngậm phiên trên app TikTok. Hàng ngày máy phụ vẫn lướt feed bình thường nên không ai biết. Chỉ đến khi có đợt reg bù mở Switcher chạm trần 8 nick (`MACHINE_FULL_8_ACCOUNTS`) thì lỗi mới phát tác.
   - **Bảng 14 Cặp Nick Bị Reg Trùng Lịch Sử Toàn Farm**:
     1. `@miumiu67971`: Máy chính = M5 (Slot 7), Máy phụ ký sinh = **M3**
     2. `@verdhsclf6f`: Máy chính = M16 (Slot 5), Máy phụ ký sinh = M40 (Đã out)
     3. `@gabruync3o9`: Máy chính = M40 (Slot 6), Máy phụ ký sinh = **M19**
     4. `@rillecoq5ml`: Máy chính = M21 (Slot 7), Máy phụ ký sinh = **M11**
     5. `@jomegbym8n8`: Máy chính = M51 (Slot 6), Máy phụ ký sinh = **M24**
     6. `@yanesbgvmuq`: Máy chính = M26 (Slot 5), Máy phụ ký sinh = **M42**
     7. `@phamnhi1770`: Máy chính = M30 (Slot 7), Máy phụ ký sinh = M75 (Đã out)
     8. `@lebaothao8787`: Máy chính = M33 (Slot 6), Máy phụ ký sinh = **M69**
     9. `@anillpboe98`: Máy chính = M56 (Slot 4), Máy phụ ký sinh = **M34**
     10. `@cyennffqko8`: Máy chính = M36 (Slot 8), Máy phụ ký sinh = M76 (Đã out 02/10)
     11. `@thleyzilkva`: Máy chính = M37 (Slot 5), Máy phụ ký sinh = **M13**
     12. `@annapmfdh0a`: Máy chính = M44 (Slot 6), Máy phụ ký sinh = M28 (Đã out)
     13. `@chichi13853`: Máy chính = M26 (Slot 6), Máy phụ ký sinh = **M53**
     14. `@anggiathinh2905`: Máy chính = M28 (Slot 5), Máy phụ ký sinh = M61 (Đã out)
     *(Kèm 1 nick M32 `@thanhlee372` có máy chính là M37)*.
   - **Bẫy Check Switcher Nông & False "DONE" State**:
     * Trên màn hình Samsung S7 (1080x1920), Switcher ban đầu chỉ hiển thị vừa 7 accounts. Nick thứ 8 (chính là nick ký sinh thường nằm ở cuối) rơi vào tọa độ Y > 1850 hoặc ẩn dưới fold.
     * CẤM TUYỆT ĐỐI chỉ đọc XML tầng đầu rồi kết luận "không thấy nick trong Switcher -> coi như đã xong". BẮT BUỘC phải thực hiện `input swipe 540 1500 540 1000 300` để kéo bottom sheet lên trước khi dump XML / OCR đối soát.
   - **Bẫy Chụp Nhầm Webview Help Center / "Tài Khoản Được Đề Xuất" (User Frustration 2026-10-02)**:
     * **Hiện tượng**: Khi tap mở Switcher trên màn hình Profile, nếu máy đang có banner pop-up "Bạn có tin vui? Đề xuất tài khoản danh bạ...", thao tác tap sai tọa độ sẽ mở văng sang WebView bài viết trợ giúp của TikTok (*"Tài khoản được đề xuất"*).
     * **Sai phạm nghiêm trọng**: Script chụp nhầm trang trợ giúp Help Center và gửi làm ảnh nghiệm thu khiến User bực mình: *"Mày vào trang tài khoản đc đề xuất chi v? Cái t cần là chứng minh ở account switcher chứ"*.
     * **Kỷ luật nghiệm thu bắt buộc (Verification Gate)**:
       1. BẰNG CHỨNG NGHIỆM THU DUY NHẤT HỢP LỆ: Màn hình **Account Switcher (sheet "Chuyển đổi tài khoản")** với danh sách accounts hoặc nút *"Thêm tài khoản"*.
       2. BẮT BUỘC OCR readback xác nhận có chuỗi `"Chuyển đổi tài khoản"` (hoặc `"Switch account"`).
       3. TUYỆT ĐỐI CẤM gửi ảnh nếu OCR phát hiện text webview Help Center: `"Tài khoản được đề xuất"`, `"Trung tâm trợ giúp"`, `"Điều khoản"`.
       4. Nếu văng WebView: Bấm Back (`input keyevent 4`), cuộn profile lên ghim ID (`swipe 540 1100 540 600 250`), rồi tap chính xác vào ID ghim ở đỉnh giữa `(540, 140)` để bung đúng Switcher thật trước khi chụp.
   - **Kỷ luật chạy song song (Parallel ADB Concurrency)**:
     * Khi chạy audit/logout đồng thời nhiều máy bằng `ThreadPoolExecutor`: BẮT BUỘC đặt timeout ADB shell tối thiểu 15s-20s (chống drop do nghẽn USB hub) và giới hạn worker pool <= 6 luồng.
   - **Kỷ Luật Bất Biến**:
     * TUYỆT ĐỐI CẤM khẳng định "farm đã sạch ký sinh" khi chỉ dựa vào Excel/DB mà chưa kiểm tra thực tế và có ảnh Switcher hiện nút "Thêm tài khoản" trên thiết bị.
10. **Bẫy Substring Blacklist Lọc Rác Xóa Nhầm Nick Thật Trong Script Sync (`sync-tik-workbooks.py` Substring Trap)**:
   - **Hiện tượng**: Nick hợp lệ tồn tại đầy đủ trong Master DAT (`taikhoan_dat_v2_updated .xlsx`) và CSDL `tiktok_tracker.db`, nhưng lại bị biến mất bí ẩn khỏi file `Tik<N>.xlsx` (cột ID bị xóa thành `None`, cột Kiểm Tra Dữ Liệu thành `MISSING_ID`). Hậu quả là runner đăng video (`run_tiktok_upload_batch.ps1` -> `validate_row`) bỏ qua máy đó, khiến tài khoản bị "đóng băng", dừng đăng video hàng tuần/hàng tháng mà không có alert crash nào báo động.
   - **Gốc rễ sự cố (Điển hình sự cố 29/08/2026)**:
     * Khi agent xử lý dữ liệu rác chứa link placeholder (như `http://vo.my/...`), thay vì lọc URL chuẩn, agent lại thêm điều kiện substring lỏng lẻo vào hàm `is_valid_tiktok_id` trong script sync:
       `if "vo.my" in s or "ngomai.ly" in s: return False`
     * Substring này vô tình khớp trúng các username thật có chứa tiền tố/họ tên đó: `@vo.my.hanh94` (Máy 69 Slot 1) và `@ngomai.ly` (Máy 22 Slot 1).
     * Mỗi khi cron `taikhoan_sync_cron_launcher.py` chạy qua `sync-tik-workbooks.py`, script sync hiểu nhầm nick thật là rác và xóa trắng ô ID trong `Tik1.xlsx`.
   - **Quy trình điều tra O(1) khi nick bị dừng đăng dài ngày**:
     1. Tra cứu `farm_account_info` trong `D:/Taadaa/data/tiktok_tracker.db` để xác định Máy $M$ và Slot Tik $K$.
     2. Đọc file `Tik<K>.xlsx` tại dòng Máy $M$: kiểm tra xem cột ID có bị `None` hoặc `MISSING_ID` trong khi Master DAT vẫn có ID hay không.
     3. Truy vết thư mục sao lưu `D:/OneDrive/TaadaaData/<cluster>/workbook-backups/archive_history/Tik<K>.xlsx.bak*` để tìm chính xác mốc thời gian và bản backup cuối cùng mà ô ID bị chuyển từ `OK` sang `MISSING_ID`.
     4. Rà soát git commit hoặc chuỗi lọc trong `scripts/sync-tik-workbooks.py` tương ứng với mốc thời gian đó.
   - **Kỷ luật cốt lõi (Anti-Substring Blacklist Invariant)**:
     * CẤM TUYỆT ĐỐI dùng `in` kiểm tra substring lỏng lẻo trên chuỗi ID TikTok để lọc URL rác.
     * BẮT BUỘC lọc theo prefix giao thức (`s.startswith(("http://", "https://"))`), regex định dạng URL (`^https?://`), hoặc tập blacklist khớp chính xác tuyệt đối (`s.lower() in BLACKLIST_EXACT`).
     * Khi sửa bộ lọc trong script sync, bắt buộc chạy test thử nghiệm trên toàn bộ 640 accounts của Master DAT trước khi lưu để đảm bảo không làm giảm số lượng nick hợp lệ (`valid_count`).

## 4. Kỷ Luật Thực Thi
- Luôn tạo file `.bak_before_backfill_...` bằng `shutil.copy2` trước khi ghi file Excel.
- Dùng `load_workbook(data_only=True)` để readback kiểm chứng ngay sau khi lưu.
- **Chuẩn hóa Slot dồn toa (Contiguous Slot Packing Protocol)**:
  Khi máy có $K < 8$ nick thực tế (ví dụ 7 nick), BẮT BUỘC sắp xếp các nick lấp kín liên tục từ **Slot 1 đến Slot $K$** trong `taikhoan_run_safe.xlsx`, toàn bộ ô trống `None` dồn về cuối (Slot $K+1$..8).
  Tuyệt đối CẤM để lỗ hổng mapping ở giữa (ví dụ để trống Slot 4 nhưng Slot 7 lại có nick), vì khi lệnh `ensure_row_accounts.py 7` kiểm tra ô thứ 7, nó thấy có nick nên kết luận sai là "Toàn bộ máy đã đầy đủ tài khoản! Không cần reg" và thoát ngay, gây kẹt reg bù.
- **Tái phân bổ nguồn Hotmail thừa (Zero-Cost Mail Reallocation)**:
  Trước khi báo cạn mail hoặc mua mail mới, BẮT BUỘC quét các dòng có `Machine = None` trong `gmail_clean_v2.xlsx` hoặc các máy có dư 5–7 mail chưa dùng. Gọi `verify_graph_token(refresh_token, client_id)` để đảm bảo token Microsoft Graph live (HTTP 200) rồi gán vào STT máy cần reg.
- **Bằng chứng nghiệm thu reg TikTok bắt buộc (Visual Evidence)**:
  Ảnh nghiệm thu duy nhất chứng minh hoàn tất reg là ảnh chụp màn hình **Tab Hồ sơ (Profile)** (`profile_<stt>_after_ensure.png`) thể hiện rõ username `@<handle>`, 0 Follow/Follower/Like và active tab Hồ sơ. CẤM dùng ảnh DOB picker (chọn ngày sinh) hoặc ảnh feed For You để báo DONE.
