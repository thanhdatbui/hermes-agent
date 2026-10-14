# Quy trình Đối soát Toàn diện Farm Kibe & Cứu hộ Audit Log 2FA (14/10/2026)

## 1. Bối cảnh & Hiện tượng
Khi nhận câu hỏi từ User như: *"Sao bên kibe chưa đủ"*, *"Sao còn thiếu"*, hoặc khi watchdog báo cáo số lượng hoàn tất thấp hơn chỉ tiêu (ví dụ: `Post-Noon Chain Watchdog: Reg Gmail xong 5/15, TikTok 2FA xong 13/74, lỗi 54 máy`), Coordinator TUYỆT ĐỐI KHÔNG đoán mò hay vội kết luận thiết bị/script hỏng.

Farm Kibe (Máy 1-80) vận hành theo chuỗi liên hoàn gồm 3 trụ cột độc lập. Cần đối soát nhanh theo phương pháp **Triage 3 Tầng Hiện Trường (O(1) Checklist)**:

---

## 2. Quy trình Triage 3 Tầng Hiện Trường

### Tầng 1: Kho Media & Tiến độ Render (`D:\TIKTOK-videonuoinick` vs `D:\video goc`)
* **Tiêu chuẩn đủ:** Toàn bộ 640 folder (80 máy × 8 slot) phải đạt $\ge 30 - 45$ video thành phẩm chuẩn ffprobe.
* **Lệnh kiểm tra nhanh O(1):**
  ```python
  from pathlib import Path
  root_render = Path(r"D:\TIKTOK-videonuoinick")
  root_raw = Path(r"D:\video goc")
  missing_render = []
  for i in range(1, 641):
      render_cnt = len(list((root_render / str(i)).glob("*.mp4")))
      if render_cnt < 30:
          raw_cnt = len(list((root_raw / str(i)).glob("*.mp4")))
          missing_render.append((i, render_cnt, raw_cnt))
  print("Folders chưa đủ render (<30 vids):", missing_render)
  ```
* **Bẫy điển hình:** Folder video gốc đã cào đủ (ví dụ: Folder 441 có 56 clip gốc) nhưng chưa được đưa vào hàng đợi render thành phẩm (`render_cnt = 0`). Chỉ cần dispatch 1 worker đơn luồng chạy render bổ sung cho đúng folder đó.

---

### Tầng 2: Sổ cái Tài khoản (`taikhoan_dat_v2_updated .xlsx` & `taikhoan_run_safe.xlsx`)
* **Tiêu chuẩn đủ:** Đủ 640/640 slot (80 máy × 8 slot = 100%) có ID TikTok.
* **Đối soát 2 đầu:**
  1. Sheet `Tài Khoản`: Đảm bảo 80 máy đều có đúng 8 dòng tài khoản (`counts[m] == 8`).
  2. Sheet `Máy Thiếu Acc`: Kiểm tra danh sách các máy còn thiếu Gmail hoặc có Gmail nhưng chưa đăng ký TikTok để lên lịch chạy `Tiktok_Reg` hoặc `register gmail`.
  3. File `taikhoan_run_safe.xlsx` (Sheet `Accounts`): Đồng bộ đủ 640 tài khoản an toàn cho runner nuôi feed.

---

### Tầng 3: Bảo mật 2FA & Tranh chấp File Lock Excel (Cứu hộ Audit Log)
* **Bẫy "Lỗi hàng loạt giả" (False Batch Failure):**
  Khi chạy batch 2FA song song với `--max-workers 40`, hàng chục worker cùng submit OTP và cố ghi vào file `taikhoan_dat_v2_updated .xlsx` nằm trên OneDrive cùng lúc, dẫn tới nghẽn lock (`WORKBOOK_LOCK_TIMEOUT_SECONDS = 120s`).
* **Hiện trường thực tế:**
  - Thiết bị thật trên app TikTok **ĐÃ BẬT XONG 2FA**, Secret TOTP **ĐÃ ĐƯỢC BẢO TOÀN** trong:
    1. File kiểm toán: `C:\Users\Kibe\AppData\Local\tiktok-add-bao-mat-f2a\logs\2fa_audit.log` với nhãn `[ACCOUNT_RECORD]`.
    2. File journal mã hóa DPAPI: `C:\Users\Kibe\AppData\Local\codex_gmail_debug-tiktok-add-bao-mat-f2a\journals\*.dpapi` ở trạng thái `authenticator_confirmed`.
  - Nhưng do bước `write_workbook` bị timeout lock, tiến trình trả về mã lỗi `failed` và đếm gộp vào mục "Lỗi" của watchdog.
* **Quy trình cứu hộ không can thiệp thiết bị (Zero Touch Backfill):**
  1. CẤM reset 2FA hoặc đè lại app trên máy thật (sẽ gây lệch secret và khóa nick).
  2. Đọc secret từ `2fa_audit.log` hoặc gọi resume journal tuần tự:
     `python python_runner/run_batch_live_2fa.py --workbook-path "..." --rows <row_list> --max-workers 5 --live`
  3. Hoặc chạy script backfill cập nhật trực tiếp cột `2FA` trong Excel từ `2fa_audit.log`.

---

## 3. Checklist Báo cáo User khi được hỏi "Sao chưa đủ"
1. **Phân rã số liệu rõ ràng:** Báo cáo tách biệt giữa (1) Kết quả thực thi của ca vừa chạy, (2) Tổng tài khoản trên toàn dàn 640 slot, và (3) Kho video media.
2. **Làm rõ lỗi ảo vs lỗi thật:** Giải thích rõ các trường hợp thiết bị đã làm xong nhưng kẹt ghi sổ cái do nghẽn file lock, khẳng định dữ liệu bảo mật (Secret 2FA) đã được lưu an toàn.
3. **Đưa ra giải pháp dứt điểm:** Đề xuất ngay 2-3 hành động O(1) cụ thể (Backfill Excel, render nốt folder lẻ, canh ca đêm chạy cuốn chiếu) kèm thời gian dự kiến.
