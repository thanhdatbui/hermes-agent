# Pitfall: Co Cụm Tuần Tự (Sparse Packing) Trong `sync-safe-workbook.py` Làm Trôi Dạt Slot & Rỗng Row 7/8

## 1. Hiện tượng & Triệu chứng
- Khi đồng bộ `taikhoan_run_safe.xlsx` cho cụm Admin (`D:\OneDrive\TaadaaData\admin\`):
  - Output sinh đủ 640 rows (80 máy × 8 slots).
  - Tuy nhiên, kiểm tra theo Row ca chạy:
    ```text
    Row 5: 49 valid accounts
    Row 6: 5 valid accounts
    Row 7: 0 valid accounts
    Row 8: 0 valid accounts
    ```
  - **Nghịch lý**: Trong file nguồn DAT Admin (`taikhoan_dat_v2_updated .xlsx`), thực tế có tới **133 nick ở Slot 7 và 8** (Slot 7 = 56 nick, Slot 8 = 77 nick). Nhưng khi sync sang `taikhoan_run_safe.xlsx`, toàn bộ Row 7 và Row 8 đều bị xóa trắng (`0 valid accounts`).

---

## 2. Nguyên nhân gốc rễ (Root Cause)
- Trong `sync-safe-workbook.py`:
  ```python
  # Đoạn mã cũ trong _build_safe_workbook:
  for row in source_sheet.iter_rows(min_row=2, values_only=True):
      ...
      machine_entries[machine].append((serial, account_id))

  for machine in sorted(machine_entries):
      entries = machine_entries[machine]
      primary_serial = ...
      while len(entries) < 8:
          entries.append((primary_serial, ""))
      for i, (serial, account_id) in enumerate(entries[:8]):
          ...
          rows.append((machine, entry_serial, account_id, video_count))
  ```
- **Lỗ hổng Sparse Packing (Co cụm tuần tự)**:
  1. Mã nguồn giả định rằng các dòng trong file DAT luôn có đủ 8 dòng vật lý liên tục theo thứ tự Slot 1..8 (giống quy chuẩn của Kibe).
  2. Tại cụm Admin (và các máy thưa nick): Sheet `Tài Khoản` chỉ có 364 dòng (không có 640 dòng cố định), chỉ lưu các slot đã có tài khoản.
  3. Khi một máy chỉ có nick ở Slot 1, Slot 7, Slot 8 (ví dụ Máy 201):
     - `entries` chỉ gom được 3 phần tử: `[nick_slot1, nick_slot7, nick_slot8]`.
     - Vòng lặp `while len(entries) < 8` pad thêm 5 chuỗi rỗng:
       `entries = [nick_slot1, nick_slot7, nick_slot8, "", "", "", "", ""]`.
  4. Khi ghi ra `taikhoan_run_safe.xlsx`:
     - Index 0 (Slot 1): nhận `nick_slot1` (Đúng).
     - Index 1 (Slot 2): nhận nhầm `nick_slot7` (Sai lệch nghiêm trọng!).
     - Index 2 (Slot 3): nhận nhầm `nick_slot8` (Sai lệch nghiêm trọng!).
     - Index 6 (Slot 7): nhận `""` (Bị rỗng!).
     - Index 7 (Slot 8): nhận `""` (Bị rỗng!).
- **Hậu quả vận hành**:
  - Ca nuôi Row 7 hoặc Row 8 (`--account-row-index 7 / 8`) đọc `taikhoan_run_safe.xlsx` thấy rỗng nên bỏ qua toàn bộ 133 nick.
  - Ca nuôi Row 2 hoặc Row 3 (`--account-row-index 2 / 3`) lại bốc nhầm nick của Slot 7/8 để chạy, làm sai lệch phân bổ ca và đối soát avatar/video.

---

## 3. Công thức Slot Bất Biến (Invariant Slot Formula)
- Cho dù ở cụm Kibe hay cụm Admin, số `Folder Video` (Cột B trong DAT) luôn tuân thủ nguyên tắc nhân 8:
  - Cụm Kibe ($m \in 1..80$): $\text{Folder} = (m - 1) \times 8 + \text{slot}$
  - Cụm Admin ($m \in 201..280$): $\text{Folder} = (m - 201) \times 8 + \text{slot}$
- Do đó, **công thức tính Slot 1-based (1..8) duy nhất đúng cho cả 2 cụm là**:
  $$\text{slot} = ((\text{Folder Video} - 1) \pmod 8) + 1$$
- Ví dụ kiểm chứng:
  - Admin M201, Folder 8: $((8 - 1) \pmod 8) + 1 = 7 + 1 = 8$ (Slot 8).
  - Admin M223, Folder 184: $((184 - 1) \pmod 8) + 1 = 183 \pmod 8 + 1 = 7 + 1 = 8$ (Slot 8).
  - Admin M264, Folder 511: $((511 - 1) \pmod 8) + 1 = 510 \pmod 8 + 1 = 6 + 1 = 7$ (Slot 7).

---

## 4. Chuẩn Hóa Logic Fix Cho `sync-safe-workbook.py`
1. Thay vì gom `list.append()`, khởi tạo mảng cố định 8 phần tử cho mỗi máy:
   ```python
   # Khởi tạo 8 slots rỗng: slot 1 -> index 0, ..., slot 8 -> index 7
   machine_slots: dict[int, list[dict]] = {}
   for m in range(min_m, max_m + 1):
       machine_slots[m] = [{"serial": "", "account_id": ""} for _ in range(8)]
   ```
2. Khi duyệt từng dòng trong DAT:
   ```python
   # Đọc machine, folder, account_id, serial
   if folder is not None:
       try:
           slot = ((int(str(folder).strip()) - 1) % 8) + 1
       except (ValueError, TypeError):
           slot = None
   else:
       slot = None

   if slot and 1 <= slot <= 8:
       machine_slots[machine][slot - 1] = {"serial": serial, "account_id": account_id}
   ```
3. Khi xuất ra `rows`:
   - Duyệt tuần tự `slot_idx` từ 0 đến 7 cho từng máy.
   - Gán `primary_serial` cho các slot trống.
   - Tra cứu `video_count` theo `account_id`.
   - Ghi đúng 8 dòng cố định tương ứng Slot 1..8 vào workbook an toàn.
