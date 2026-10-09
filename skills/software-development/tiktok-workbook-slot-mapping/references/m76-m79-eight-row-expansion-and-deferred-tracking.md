# Quy Trình Nới Rộng 8 Hàng Vật Lý Cho Cụm M76..M79 & Đồng Bộ Safe Workbook (2026-09-13)

## 1. Bối cảnh & Hiện trạng
Trước khi nới rộng:
- Toàn bộ master `taikhoan_dat_v2_updated .xlsx` có 633 dòng dữ liệu (tính cả dòng trống đến 637).
- M75 có đủ 8 hàng (Rows 594..601).
- M76..M79 mỗi máy chỉ có 6 hàng:
  - M76: Rows 602..607
  - M77: Rows 608..613
  - M78: Rows 614..619
  - M79: Rows 620..625
- M80 có 8 hàng nhưng bị đẩy lên sớm: Rows 626..633.

Do thiếu 2 hàng vật lý ở Slot 7 & 8 của M76..M79, khi luồng reg bù chạy cho Row 7 (Ca 4 ngày lẻ), kết quả reg thành công của M77 và M78 sinh ra file tracking JSON nhưng không thể merge tự động vào sheet `Tài Khoản`.

---

## 2. Bản đồ dịch chuyển và chèn 8 hàng (+2 hàng / máy)

Mỗi máy chèn thêm 2 hàng vật lý ngay sau hàng thứ 6 của máy đó:

### Máy 76 (thêm sau Row 607):
- **Row 608 (Slot 7)**: Máy=76, Folder=608, Device=`9885b64d56305a3731`, ID/Pass/Mail=None.
- **Row 609 (Slot 8)**: Máy=76, Folder=602, Device=`9885b64d56305a3731`, ID/Pass/Mail=None.

### Máy 77 (dịch chuyển +2, thêm sau Row 615):
- **Row 616 (Slot 7)**: Máy=77, Folder=615, ID=`tunam03041`, PASS=`!ByZWT1L#NbdcDo4`, GMAIL=`exlinvn.0304.eunyy@hotmail.com`, PASS_MAIL=`datRSAmh13Pr`, NGAY_TAO=`2026-09-08`, Device=`ce05160595e7953b04`.
  - `tracking_row = 616, tik = 615`
- **Row 617 (Slot 8)**: Máy=77, Folder=616, Device=`ce05160595e7953b04`, ID/Pass/Mail=None.

### Máy 78 (dịch chuyển +4, thêm sau Row 623):
- **Row 624 (Slot 7)**: Máy=78, Folder=623, ID=`ohongthinh1126`, PASS=`U03!DqsYgMn%O8`, GMAIL=`hm4.ev.1126.jameel@hotmail.com`, PASS_MAIL=`datrc5ibYiHW`, NGAY_TAO=`2026-09-08`, Device=`ce0916090a9d320a01`.
  - `tracking_row = 624, tik = 623`
- **Row 625 (Slot 8)**: Máy=78, Folder=624, Device=`ce0916090a9d320a01`, ID/Pass/Mail=None.

### Máy 79 (dịch chuyển +6, thêm sau Row 631):
- **Row 632 (Slot 7)**: Máy=79, Folder=631, Device=`ce0516059d279f3e03`, ID/Pass/Mail=None.
- **Row 633 (Slot 8)**: Máy=79, Folder=632, Device=`ce0516059d279f3e03`, ID/Pass/Mail=None.

### Máy 80 (dịch chuyển +8 hàng xuống cuối):
- Rows 634..641 (8 hàng nguyên vẹn của M80, tương ứng Folder 633..640).

---

## 3. Cập nhật Tracking JSON Files
Vị trí tracking kết quả reg đêm:
`D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\20260913-000536\batch_1\`
- `stt_77/tracking_result_stt77_exlinvn.0304.eunyy_hotmail.com.json`:
  - `tracking_row`: 616
  - `tik`: 615
- `stt_78/tracking_result_stt78_hm4.ev.1126.jameel_hotmail.com.json`:
  - `tracking_row`: 624
  - `tik`: 623

---

## 4. Lệnh Đồng Bộ An Toàn (Sync Safe Workbook)
Sau khi lưu master workbook:
```bash
export TAADAA_ALLOW_OVERWRITE_TOKEN="taadaa-writer-3c47f89f35e44795a79267e09fbcc72d"
python "D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-safe-workbook.py" \
  --source "D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx" \
  --output "D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx"
```

## 5. Tiêu chuẩn nghiệm thu (Verification Criteria)
1. Đọc `taikhoan_run_safe.xlsx`: Đúng 640 dòng (80 máy x 8 slot).
2. Kiểm tra M76, M77, M78, M79: Mỗi máy có đủ 8 dòng liên tục.
3. Row 7 M77 có ID `tunam03041` (Folder 615).
4. Row 7 M78 có ID `ohongthinh1126` (Folder 623).
5. Máy 80 nằm trọn vẹn từ Row 634 đến 641.
