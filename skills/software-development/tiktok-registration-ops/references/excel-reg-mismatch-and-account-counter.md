# Lệch Excel Reg TikTok, Account Counter Dropdown & Remote ADB Socket Pitfalls

## 1. Căn nguyên lỗi "Máy đã đủ 8 acc (Lệch Excel - Cần kiểm tra backfill)"
- **Hiện tượng**: `ensure_row_accounts.py` hoặc batch reg quét Excel thấy máy còn thiếu account (ví dụ Row 6 trống/None), nhưng khi chạy tới bước `tap_add_account` thì văng lỗi `MACHINE_FULL_8_ACCOUNTS`.
- **Nguyên nhân kép**:
  1. **Nút "Thêm tài khoản" bị che khuất**: Khi app TikTok đã nạp 7 account, danh sách account trong dropdown bottom sheet chiếm trọn màn hình, đẩy nút *"Thêm tài khoản"* xuống dưới mép nhìn thấy. Nếu script không cuộn (`swipe up`), `find_text_tap` sẽ không thấy nút.
  2. **Bộ đếm fallback đếm trùng container layout**: Đoạn fallback đếm account duyệt qua các node chứa resource-id `lli`, `ng8`... nhưng không lọc bỏ các container rỗng (chỉ có con text) và nút điều hướng, khiến 7 acc + container bị đếm thành 14-15 node -> kích hoạt nhầm cảnh báo `MACHINE_FULL_8_ACCOUNTS >= 8`.
  3. **Tài khoản đã reg trước đó nhưng chưa merge/sync safe workbook**: Có những máy thực sự đã đủ 8 acc do các lượt chạy trước (đặc biệt khi chạy batch lớn có defer tracking write hoặc bị OneDrive lock `dwShareMode=0`), file `tracking_result_stt<M>_*.json` đã sinh trong thư mục run artifact nhưng chưa được nạp bù vào sổ cái `taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx` và `Tik<N>.xlsx`.

## 2. Quy trình xử lý chuẩn hóa
1. **Kiểm tra run artifacts trước khi reg mò**:
   - Quét các thư mục `D:/Taadaa/runtime/admin/artifacts/runs/social-batch-all/<run_id>/batch_*/stt_<M>/tracking_result_*.json` gần nhất.
   - Nếu tìm thấy file tracking có `status="SUCCESS"` và `tiktok_id`: Trích xuất username, email, password, folder để nạp bù (backfill) ngay vào workbook thay vì cố reg mới làm văng lỗi.
2. **Cơ chế cuộn tìm nút Add Account**:
   - Trước khi kết luận máy đủ 8 acc, bắt buộc phải cuộn bottom-sheet (`swipe(device_id, 540, 1500, 540, 800, 400)`) tối đa 2 lần để nút *"Thêm tài khoản"* trồi lên.
   - Bộ đếm fallback `_acc_count` bắt buộc dùng tập hợp `set` các username thực tế (có text hoặc content-desc không rỗng, loại trừ các nhãn *"Thêm tài khoản"*, *"Chuyển đổi tài khoản"*).
3. **Đồng bộ đa tầng workbook**:
   - Khi backfill hoặc nạp kết quả mới, phải bảo đảm đồng bộ cả 3 nơi:
     - Sổ cái gốc: `taikhoan_dat_v2_updated .xlsx`
     - File runtime an toàn: `taikhoan_run_safe.xlsx` (chạy script `sync-safe-workbook.py` hoặc merge function của `ensure_row_accounts.py`)
     - File slot tương ứng: `Tik<Row>.xlsx`

## 3. Remote ADB Socket Routing (Admin Cluster vs Kibe)
- **Cạm bẫy**: Khi máy điều phối Kibe chạy script `ensure_row_accounts.py` với host `admin`, nếu không gán biến môi trường `ADB_SERVER_SOCKET="tcp:192.168.110.119:5037"`, các subprocess con sẽ fallback về `localhost:5037` của Kibe. Khi đó, `adb.exe -s <serial>` sẽ báo ngay `device '<serial>' not found` hoặc `TikTok not foreground after clean launch`.
- **Quy tắc**:
  - Khi chạy target máy Admin từ Kibe, bắt buộc export rõ:
    `export ADB_SERVER_SOCKET="tcp:192.168.110.119:5037"` và `TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/admin.yaml"`.
  - Nếu gặp `adb-timeout` khi gọi `shell ime set` hoặc `shell am force-stop`: Dùng lệnh reconnect đích danh từng thiết bị:
    `"C:\Program Files (x86)\xiaowei\tools\adb.exe" -H 192.168.110.119 -P 5037 -s <SERIAL> reconnect`.
    TUYỆT ĐỐI CẤM kill ADB server trên host remote `192.168.110.119`.
