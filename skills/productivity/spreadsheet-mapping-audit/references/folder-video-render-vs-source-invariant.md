# Phân Định Bất Biến Giữa Folder Video (Render Đích) và Video Gốc (Nguồn Cào)

## 🛑 BẪY TỬ HUYỆT (ĐÃ PHÁ TAIKHOAN_RUN_SAFE NHIỀU LẦN)
Các AI agent ở nhiều phiên trước liên tục mắc lỗi nghiêm trọng:
Khi nhận lệnh "đổi nguồn video", "sửa folder video" hoặc "đổi avatar", agent nhìn thấy Cột 4 tên là `Folder Video` nên lập tức ghi đè ID nguồn cào (ví dụ 242, 291) vào Cột 4!
Hậu quả:
- Làm sai lệch công thức phần cứng của Cột 4.
- `excel_preflight_validator.py` Rule 3 chặn đứng (`[FAIL] Sai công thức Folder Video`).
- Cronjob `hermes_taikhoan_sync_cron.py` bị ngắt, hủy toàn bộ bước sync runtime `taikhoan_run_safe.xlsx`.

---

## 📐 CÔNG THỨC TOÁN HỌC BẤT BIẾN (INVARIANT RULES)

### 1. Cột 4: `Folder Video (Render Dich)` — THƯ MỤC RENDER TRÊN ĐIỆN THOẠI
- **Bản chất:** Là thư mục trên host chứa video ĐÍCH đã render gắn cố định với từng slot phần cứng của máy.
- **Công thức:**
  - **Cụm Kibe (Máy 1..80):** `(Máy - 1) * 8 + Slot`  (dải giá trị 1..640)
  - **Cụm Admin (Máy 201..280):** `((Máy - 200) - 1) * 8 + Slot`  (dải giá trị 1..640)
- **CẤM TUYỆT ĐỐI:** Cột 4 là giá trị toán học thuần túy, KHÔNG BAO GIỜ ĐƯỢC PHÉP THAY ĐỔI khi đổi nguồn cào, đổi ngách hay đổi avatar. Mọi hành vi gán số nguồn cào vào Cột 4 đều bị coi là phá hoại dữ liệu.

### 2. Cột 5: `Video Goc (Nguon Cao)` — NGUỒN CÀO TỪ DOUYIN VỀ
- **Bản chất:** Là thư mục chứa video gốc thô cào từ Douyin/TikTok về phân bổ cho ca đăng video.
- **Công thức:**
  - **Cụm Kibe (Máy 1..80):** `(Slot - 1) * 80 + Máy`  (dải giá trị 1..640)
  - **Cụm Admin (Máy 201..280):** `(Slot - 1) * 80 + (Máy - 200)`  (dải giá trị 1..640)
- Khi có nghiệp vụ đổi nguồn video hay swap folder, CHỈ ĐƯỢC PHÉP cập nhật Cột 5 này.

---

## 🛡️ DANH SÁCH SCRIPT ĐỘC HẠI ĐÃ VÔ HIỆU HÓA (CẤM TÁI TẠO LẠI)
1. `D:/Taadaa/tools/fix_tik4_folder_video.py`: Script tạm từng gán nhầm 242 và 291 vào Cột 4 của Tik4.xlsx.
2. `D:/Taadaa/Hermes/deploy/hermes-home/scripts/step1_sync_formula.py`: Script cũ chạy lệnh `UPDATE avatar_replace_queue SET video_goc = folder_video` và `row[4].value = folder_int`, làm ô nhiễm toàn bộ database queue và 16 file Tik.

---

## ✅ CHECKLIST KIỂM CHỨNG BẮT BUỘC SAU MỌI THAO TÁC EXCEL
Trước khi kết thúc bất kỳ lượt xử lý Excel nào, bắt buộc chạy kiểm chứng 2 lệnh sau:
```bash
python D:/Taadaa/tools/excel_preflight_validator.py --excel-dir D:/OneDrive/TaadaaData/kibe
python D:/Taadaa/tools/excel_preflight_validator.py --excel-dir D:/OneDrive/TaadaaData/admin
```
Bắt buộc đạt **PASS 100% (0 lỗi, 0 cảnh báo)** mới được coi là hợp lệ.
Sau đó kiểm chứng luồng sync:
```bash
python "D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_taikhoan_sync_cron.py"
```
Kết quả phải exit 0 và log `taikhoan_sync completed successfully`.
