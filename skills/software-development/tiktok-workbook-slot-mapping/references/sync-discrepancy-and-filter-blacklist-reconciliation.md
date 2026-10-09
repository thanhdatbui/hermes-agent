# Quy Trình Điều Tra & Phòng Chống Bẫy Lọc Rác Làm Trống ID Đồng Bộ (Sync Discrepancy & Blacklist Collision)

## 1. Dấu Hiệu Sự Cố
- Tài khoản trên app TikTok thật vẫn sống (LIVE), trên file Master DAT (`taikhoan_dat_v2_updated .xlsx`) vẫn có username, nhưng trên các file upload (`Tik1.xlsx` .. `Tik8.xlsx`) cột ID bị trống (`None`) và cột Kiểm Tra Dữ Liệu hiển thị `MISSING_ID`.
- Hệ quả thực tế: Nick bị "đóng băng" đăng video suốt thời gian dài (hàng tuần đến hàng tháng) vì module kiểm tra upload (`account_source.py` / `validate_row`) yêu cầu bắt buộc có ID TikTok.

## 2. Bản Chất Lỗi Kỹ Thuật (Root Cause)
- **Bẫy Hardcode Substring Blacklist (`"..." in s`)**: Khi phát hiện dữ liệu rác hoặc URL lạ lọt vào bảng tính (ví dụ link `http://vo.my/...`), kỹ sư/agent vội vã thêm điều kiện chặn bằng toán tử kiểm tra chuỗi con bừa bãi:
  ```python
  # CẤM TUYỆT ĐỐI PATTERN NÀY:
  if "vo.my" in s or "ngomai.ly" in s or "phng.th" in s:
      return False
  ```
- Chuỗi con này vô tình trùng khớp với các username hợp lệ có chứa dấu chấm hoặc tiền tố tương tự (`vo.my.hanh94`, `ngomai.ly`).
- Mỗi lần cron đồng bộ chạy (`sync-tik-workbooks.py`), hàm lọc rác coi username hợp lệ là rác và xóa trắng ô ID trên các file `TikN.xlsx`.

## 3. Quy Tắc Lọc ID TikTok Chuẩn Hóa (Anti-Garbage Invariant)
Hàm kiểm tra hợp lệ `is_valid_tiktok_id` BẮT BUỘC tuân theo cấu trúc regex và URL filter rõ ràng, TUYỆT ĐỐI CẤM lọc substring tùy tiện:
```python
NICK_REGEX = re.compile(r"^[a-zA-Z0-9_.]{2,24}$")

def is_valid_tiktok_id(val: object) -> bool:
    if val is None:
        return False
    s = str(val).strip().lstrip("@")
    if not s or s.lower() in {"none", "null", "ghjfghj", "chua_co", "chưa có"}:
        return False
    # Chặn URL, domain hoặc đường dẫn:
    if s.startswith("http://") or s.startswith("https://") or "/" in s or ":" in s:
        return False
    if s.isdigit():
        return False
    return bool(NICK_REGEX.match(s))
```

## 4. Script Kiểm Tra Đối Soát Toàn Farm (Audit O(1) Cho Toàn Bộ 8 File Tik)
Khi nghi ngờ có nick bị mất hoặc không đăng video, chạy ngay kiểm tra đối chiếu giữa Master DAT và toàn bộ `Tik1..Tik8.xlsx` cho cả 2 cluster (Kibe & Admin):

```python
import openpyxl, os

for cluster in ['kibe', 'admin']:
    dat_path = f'D:/OneDrive/TaadaaData/{cluster}/taikhoan_dat_v2_updated .xlsx'
    wb_dat = openpyxl.load_workbook(dat_path, data_only=True)
    ws_dat = wb_dat['Tài Khoản'] if 'Tài Khoản' in wb_dat.sheetnames else wb_dat.active
    dat_map = {}
    for r in range(2, ws_dat.max_row + 1):
        m, folder, uid = ws_dat.cell(r, 1).value, ws_dat.cell(r, 2).value, ws_dat.cell(r, 3).value
        if m and folder and uid:
            try:
                slot = ((int(folder) - 1) % 8) + 1
                dat_map[(int(m), slot)] = str(uid).strip()
            except Exception: pass

    for slot in range(1, 9):
        tik_name = f"Tik{slot}.xlsx" if slot != 3 else "tik3.xlsx"
        tik_path = f'D:/OneDrive/TaadaaData/{cluster}/{tik_name}'
        if not os.path.exists(tik_path): continue
        wb_tik = openpyxl.load_workbook(tik_path, data_only=True)
        ws_tik = wb_tik['TaiKhoan'] if 'TaiKhoan' in wb_tik.sheetnames else wb_tik.active
        for r in range(2, ws_tik.max_row + 1):
            m = ws_tik.cell(r, 1).value
            if not m: continue
            tik_id = str(ws_tik.cell(r, 3).value or '').strip()
            expected_id = dat_map.get((int(m), slot), '')
            if expected_id and (not tik_id or tik_id.lower() == 'none'):
                print(f"[{cluster}] DISCREPANCY {tik_name} M{m} S{slot}: DAT='{expected_id}', Tik=None")
```

## 5. Các Bước Khôi Phục & Đồng Bộ Lại An Toàn
1. Backup file `TikN.xlsx` cần sửa: `cp TikN.xlsx TikN.xlsx.bak_before_fix_<timestamp>`.
2. Chạy đồng bộ lại từ Master:
   `python "D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-tik-workbooks.py" --source "D:/OneDrive/TaadaaData/<cluster>/taikhoan_dat_v2_updated .xlsx" --tik-dir "D:/OneDrive/TaadaaData/<cluster>"`
3. Chạy validator kiểm tra toàn diện:
   `python D:/Taadaa/tools/excel_preflight_validator.py --excel-dir D:/OneDrive/TaadaaData/<cluster> --exit-on-error`
4. Trigger lại launcher đồng bộ nền:
   `python "C:/Users/Kibe/AppData/Local/hermes/scripts/taikhoan_sync_cron_launcher.py"`
5. Cập nhật lại CSDL `tiktok_tracker.db`:
   `python D:/Taadaa/tools/sync_farm_account_info.py`
