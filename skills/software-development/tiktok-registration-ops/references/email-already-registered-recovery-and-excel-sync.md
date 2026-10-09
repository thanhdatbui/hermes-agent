# Báo Lỗi [07] "Email Đã Có TK TikTok" & Khắc Phục Lệch Sổ Cái

> **QUY TẮC BẤT BIẾN (USER PHẠT NẶNG 2026-09-29):**
> **Bên bán KHÔNG BAO GIỜ bán Hotmail đã reg TikTok.** Khi nhận thông báo `[07] Tất cả email đã có TK TikTok`, **CẤM TUYỆT ĐỐI** phán cạn mail, cấm đổ lỗi cho bên bán.
> Căn nguyên 100% là do **Farm đã reg thành công tài khoản đó trong các phiên trước**, nhưng do lỗi ghi nhận dữ liệu (OneDrive lock file `dwShareMode=0`, crash ở bước merge tracking kết phiên) khiến tài khoản chưa được nạp vào sổ cái `taikhoan_dat_v2_updated .xlsx` / `taikhoan_run_safe.xlsx`.

---

## 1. Căn Nguyên Cơ Chế
1. **Quá trình Reg thành công**: Máy farm nhận email từ `gmail_clean_v2.xlsx`, tạo nick TikTok thành công, sinh file `tracking_result_stt<M>_<email>.json` trong thư mục `runtime/<cluster>/artifacts/runs/...`.
2. **Thất bại ở bước ghi Workbook**: Khi lưu kết quả vào `taikhoan_dat_v2_updated .xlsx`, nếu file đang bị OneDrive lock hoặc Excel mở ngầm, process ghi bị chặn hoặc bị revert.
3. **Phát sinh lỗi [07] ở phiên sau**:
   - Script `_detect_clean.py` đọc `gmail_clean_v2.xlsx` và đối soát với `taikhoan_dat_v2_updated .xlsx`.
   - Do email chưa có trong sổ cái, script coi đó là "email sạch chưa dùng" và cấp lại cho máy để reg.
   - Khi app TikTok mở form đăng ký bằng email đó, máy chủ TikTok trả về: email đã tồn tại -> app văng sang màn hình OTP/Login -> script văng lỗi `[07]`.

---

## 2. Quy Trình 4 Bước Khắc Phục Chuẩn (Audit & Recovery)

### Bước 1: Trích xuất danh sách nick thực tế trên máy qua OCR Dropdown
Khi máy báo lỗi `[07]` hoặc nghi ngờ lệch dữ liệu, kiểm tra ngay ảnh chụp switcher dropdown mới nhất:
```bash
python C:/Users/Kibe/AppData/Local/hermes/skills/productivity/windows-native-ocr/scripts/winrt_ocr.py "D:/Taadaa/Tiktok_Reg/screenshots_social/<M>_03_dropdown_*.png"
```
So sánh danh sách username nhận diện được với các nick đã ghi trong `taikhoan_run_safe.xlsx`. Nick nào có trên màn hình máy nhưng chưa có trong Excel chính là nick bị thất lạc.

### Bước 2: Truy vết file tracking JSON trong lịch sử runs
Tìm file tracking result chứa username hoặc email bị báo lỗi:
```python
import json
from pathlib import Path
p = Path("D:/Taadaa/runtime/admin/artifacts/runs/social-batch-all")
for r in sorted(p.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:30]:
    s_dir = r / "batch_1" / f"stt_{M}"
    if s_dir.is_dir():
        for f in s_dir.glob("tracking_result_*.json"):
            data = json.loads(f.read_text(encoding="utf-8"))
            print(f.name, data.get("tiktok_id"), data.get("email"), data.get("created_date"))
```

### Bước 3: Nạp bù vào Sổ cái `taikhoan_dat_v2_updated .xlsx` & `TikN.xlsx`
Xác định Folder tương ứng theo quy tắc:
- M >= 201: `Base Folder = (M - 201) * 8 + 1`
- M < 201: `Base Folder = (M - 1) * 8 + 1`
- Slot N (1..8) -> Folder = `Base + (N - 1)`.

Ghi trực tiếp thông tin vào row tương ứng trong `taikhoan_dat_v2_updated .xlsx` và file `Tik<N>.xlsx`.

### Bước 4: Đồng bộ an toàn sang `taikhoan_run_safe.xlsx`
Chạy script đồng bộ chuẩn hóa theo host:
```bash
TAADAA_HOST_ID=admin python "D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-safe-workbook.py" \
  --source "D:/OneDrive/TaadaaData/admin/taikhoan_dat_v2_updated .xlsx" \
  --output "D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx" \
  --tik-dir "D:/OneDrive/TaadaaData/admin"
```
Sau khi đồng bộ, `taikhoan_run_safe.xlsx` sẽ nhận diện đủ slot, `_detect_clean.py` sẽ tự động loại trừ email này khỏi danh sách cần reg.

---

## 3. Cảnh Báo Ngộ Nhận `MACHINE_FULL_8_ACCOUNTS` (7 Accs + Add Button Overflow)
- **Hiện tượng**: Máy mới có 7 tài khoản nhưng script báo `MACHINE_FULL_8_ACCOUNTS` và dừng reg.
- **Nguyên nhân**: Trên layout màn hình, 7 tài khoản đã chiếm hết chiều cao bottom-sheet, khiến nút *"Thêm tài khoản"* bị che khuất xuống dưới đáy. Ngoài ra, bộ đếm cũ đếm gộp cả layout container rỗng (`lli`).
- **Giải pháp**:
  - Script phải thực hiện thao tác cuộn: `swipe(device_id, 540, 1500, 540, 800, 400)` để kéo nút lên.
  - Bộ đếm tài khoản chỉ đếm các node có text thực tế và loại trừ các nút nhãn: `Thêm tài khoản`, `Chuyển đổi tài khoản`, `Add account`, `Switch account`.
