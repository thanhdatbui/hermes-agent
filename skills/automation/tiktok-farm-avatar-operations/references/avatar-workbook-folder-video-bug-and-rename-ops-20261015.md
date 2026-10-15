# Avatar Workbook Folder Video Bug & Nickname Rename Operations (2026-10-15)

## 1. BUG CỘT `Folder Video` TRONG `Tik*.xlsx` GÂY UPLOAD AVATAR NHẦM NGÁCH

### Căn Nguyên
Cột `Folder Video` (Cột 4, index 3) trong `TikN.xlsx` bị ghi sai số folder, khiến runner bốc nhầm `avatar.jpg` từ folder lạc đề. Cả hai cột `Folder Video` (cột 3) và `Video Goc` (cột 4) phải cùng trỏ đến cùng một folder source.

**Ví dụ thực tế gây lỗi (2026-10-15):**
- Máy 2 (`@lieuhoan03`, Niche Tài chính, VideoGoc=242): `Folder Video` ghi nhầm `12` (Gym/xăm trổ) → avatar xăm trổ lưng bị nạp lên nick tài chính
- Máy 51 (`@luutuoi02`, Niche Kỷ yếu/Áo dài, VideoGoc=291): `Folder Video` ghi nhầm `404` (Thú cưng chó lông xù) → avatar chó cưng bị nạp lên nick kỷ yếu

### Triage O(1) — Kiểm Tra Lệch Folder
```python
import openpyxl
wb = openpyxl.load_workbook("D:/OneDrive/TaadaaData/kibe/Tik4.xlsx")
ws = wb.active
for row in ws.iter_rows():
    may, folder_video, video_goc = row[0].value, row[3].value, row[4].value
    if folder_video != video_goc:
        print(f"MAY {may}: Folder={folder_video} nhưng VideoGoc={video_goc} -> sửa Folder thành {video_goc}")
```

### Fix O(1)
```python
import openpyxl
p = "D:/OneDrive/TaadaaData/kibe/Tik4.xlsx"
wb = openpyxl.load_workbook(p)
ws = wb[wb.sheetnames[0]]
for row in ws.iter_rows():
    if row[0].value in (2, 51):  # Target machines
        row[3].value = row[4].value   # Set Folder Video = Video Goc
wb.save(p)
```

**Invariant:** `Folder Video` PHẢI bằng `Video Goc`. Nếu khác nhau → kiểm tra lịch sử import và xác định folder nào chứa video đúng ngách trước khi sửa.

---

## 2. PIPELINE ĐỔI BIỆT DANH RẬP KHUÔN — DO_RENAME_Mxx PATTERN

### Pattern Chuẩn: `cp` + `patch` O(1)
Thay vì viết toàn bộ runner từ đầu (tốn ngân sách L2), dùng quy trình:
```bash
cp D:/Taadaa/tools/do_rename_m76.py D:/Taadaa/tools/do_rename_m{ID}.py
cp D:/Taadaa/tools/tests/test_do_rename_m76.py D:/Taadaa/tools/tests/test_do_rename_m{ID}.py
```
Sau đó patch O(1) các hằng số:
- `MACHINE_ID`, `SERIAL`, `TARGET_USER`, `NEW_NAME`
- Keyword OCR: `"lieuhoan"`, `"lilyan"` → tên mới phù hợp
- `observe()`: tên file report `m{ID}_{slug}_{tag}.png`
- `operator_device_lock(project="do_rename_m{ID}", ...)`
- Confirm popup coordinates: Máy 51 dùng `(748, 1174)` thay vì `(327, 1169)` của Máy 2

Nghiệm thu focused test trước khi trigger thực tế:
```bash
pytest D:/Taadaa/tools/tests/test_do_rename_m{ID}.py -q
```

### Upload Avatar Sau Rename: `run_avatar_batch_3accs.py`
Runner chính thức nhận `-Tik` và `--machine` flag:
```bash
python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik 4 --machine 2
python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik 4 --machine 51
```
File này gọi `run_tiktok_upload_avatar.ps1` với `input=b'RUN\r\n'` và cung cấp `ForceAvatarMachineList`.

Xác nhận thành công: kiểm tra `report.json` trong run folder:
```python
import json, glob, os
runs = sorted([d for d in os.listdir("D:/CodexRuntime/tiktok-video/runs") if d.startswith("run_<SERIAL>")])
data = json.load(open(f"D:/CodexRuntime/tiktok-video/runs/{runs[-1]}/report.json"))
print(data["status"], data.get("avatar_status"))
# OK pattern: status=AVATAR_SMOKE_SUCCESS, avatar_status=FORCED_REPLACED_VERIFIED
```

---

## 3. KHOÁ BẢO VỆ `manual_avatar_protected_folders.json`

Setelah upload xong phải thêm folder vào protected list để batch script không ghi đè:
- File: `D:/Taadaa/Tiktok-video/data/manual_avatar_protected_folders.json`
- Thêm folder_id vào mảng `protected_folders` (duy trì thứ tự tăng dần)

Dispatch Worker với patch contract O(1):
```
OLD_STRING:
    223,
    244,
NEW_STRING:
    223,
    242,
    244,
    291,
```

---

## 4. OCR NOISE `IUUtUOi02` → USERNAME THẬT `luutuoi02`

WinRT OCR đọc `u` và `l` bị nhầm trong một số font rendering trên Samsung S7:
- `l` → `I`, `u` → `U`, `o` → `0` (zero)
- `luutuoi02` → `IUUtUOi02` là pattern OCR noise phổ biến

Trong `classify()` và `is_target_user()`, bắt buộc dùng `difflib.SequenceMatcher + "luutuoi" in compact(t)` thay vì exact string match để xử lý nhiễu OCR này.

---

## 5. BẫY `do_upload_avatar_m{ID}.py` — TAP NHẦM NÚT TÌM BẠN BÈ

Tọa độ `(75, 150)` và `(72, 148)` trên S7 TikTok v47 là nút **Tìm Bạn Bè**, KHÔNG phải nút Sửa Hồ Sơ.
Nút Sửa Hồ Sơ (bút chì) đúng: `(870, 558)` — hoặc `(210, 865)` nếu dùng nút text.

Khi `do_upload_avatar_m2.py` dùng `tap(75, 150)` → máy mở màn "Tìm Bạn Bè" thay vì Edit Profile → OCR đọc `['TikTok']` → script tiếp tục tap `Thay doi anh` và `Tai anh len` ở màn sai → Photo Picker nhảy ra nhưng máy đang ở Feed không phải Profile.

Nhưng sau đó khi dùng `run_avatar_batch_3accs.py` (pipeline chính thức) chạy, avatar vẫn upload thành công vì pipeline chính thức có state-machine OCR đầy đủ.

**Lesson:** Không dùng `do_upload_avatar_m71.py` (script thủ công cũ) làm runner sản xuất. LUÔN dùng `run_avatar_batch_3accs.py` hoặc `run_tiktok_upload_avatar.ps1 -ForceAvatarMachineList`.
