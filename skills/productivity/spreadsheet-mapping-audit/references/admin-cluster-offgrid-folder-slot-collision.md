# Off-Grid Folder Video Drift & Modulo-8 Slot Collision (Admin Cluster)

## 1. Triệu chứng & Bối cảnh phát sinh sự cố
- **Thông báo lỗi**:
  * Tool preflight reg bù (`ensure_row_accounts.py <row>`) quét thấy các máy cụm Admin (201–280) bị thiếu nick ở Row/Slot tương ứng (`None`).
  * Khi probe probe vào máy thật, TikTok trên máy đã đủ 8 nick hoặc tool reg báo lỗi:
    `[07] Tim email chua dang ky TikTok cho STT <N> -> skip ...: da co TikTok trong tracking`.
  * User bức xúc: *"Bữa cũng bị v mày bảo là chuẩn hoá hết r k còn nick nào đã reg mà k ghi h lại lòi ra"*.

## 2. Căn nguyên gốc rễ (Root Cause)
1. **Lệch công thức Folder Video Admin (Off-Grid Folder Drift)**:
   - Dải chuẩn Folder Video của Admin (80 máy 201–280, mỗi máy 8 slot):
     $$\text{Folder Base}(STT) = (STT - 201) \times 8 + 1$$
     $$\text{Dải hợp lệ cho Máy } STT = [\text{Folder Base} \dots \text{Folder Base} + 7]$$
     Toàn bộ 80 máy phân bổ đúng dải $1 \dots 640$.
   - Khi chạy batch reg tự động cho các slot sau (Row 4..7), tool ghi nhận `Folder Video` bị trôi ra ngoài dải (ví dụ gán $\text{base} + 8 + \text{slot}$ hoặc cộng dồn quá trớn):
     * Ví dụ: Máy 264 có dải chuẩn là $505 \dots 512$, nhưng các nick mới lại bị gán Folder 513, 514.
2. **Hiện tượng va chạm slot qua Modulo 8 (Modulo-8 Slot Collision)**:
   - Trong script tạo file safe (`sync-safe-workbook.py`), target slot được tính toán như sau:
     $$\text{target\_slot} = (\text{Folder Video} - 1) \pmod 8$$
   - Khi Folder bị tràn sang chu kỳ 8 tiếp theo (513, 514):
     $$(513 - 1) \pmod 8 = 0 \implies \text{Slot 1 (Tik1)}$$
     $$(514 - 1) \pmod 8 = 1 \implies \text{Slot 2 (Tik2)}$$
   - Khi đó, nick mới thuộc Slot 5/6 lại bị tính thành Slot 1/2 và va chạm trực tiếp với các nick đã có ở Slot 1/2.
   - Script thấy Slot 1/2 đã có dữ liệu nên bỏ qua nick mới, khiến Slot 5/6 trong `taikhoan_run_safe.xlsx` bị để trống (`None`).

## 3. Quy trình rà soát & khắc phục chuẩn O(1)
1. **Quét tìm các dòng Off-Grid trong master tracking Admin**:
   ```python
   import openpyxl

   wb = openpyxl.load_workbook(
       r"D:\OneDrive\TaadaaData\admin\taikhoan_dat_v2_updated .xlsx",
       read_only=True,
   )
   ws = wb.active
   for i, r in enumerate(ws.iter_rows(values_only=True), 1):
     stt, folder = r[0], r[1]
     if (
         stt
         and str(stt).isdigit()
         and folder
         and str(folder).isdigit()
         and int(stt) >= 201
     ):
       base = (int(stt) - 201) * 8 + 1
       if int(folder) < base or int(folder) > base + 7:
         print(f"Row {i} M{stt} {r[2]}: Folder={folder} out of [{base}..{base+7}]")
```

2. **Chuẩn hóa giá trị Folder Video**:
   - Backup trước khi ghi: `shutil.copy2(src, src + ".bak_off_grid_fix_<timestamp>")`.
   - Gán lại: `Folder Video = base + slot_index - 1`.

3. **Rebuild Safe Workbook cho đúng cụm host**:
   ```bash
   TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/admin.yaml" \
   python "D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-safe-workbook.py" \
     --source "D:/OneDrive/TaadaaData/admin/taikhoan_dat_v2_updated .xlsx" \
     --output "D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx"
   ```

4. **Kiểm tra readback**:
   - Đảm bảo tất cả các máy đã reg có đủ 8/8 accounts hoặc khớp đúng số lượng thực tế trong `taikhoan_run_safe.xlsx`.
   - Chạy `ensure_row_accounts.py <row> --dry-run` để xác nhận không còn máy nào bị quét thiếu giả mạo.
