# Hướng Dẫn Vận Hành Reg Bù Acc On-Demand (`ensure_row_accounts.py`)

## 1. Mục Đích & Phạm Vi
Kịch bản `D:/Taadaa/tools/ensure_row_accounts.py` được sử dụng để reg bổ sung tài khoản TikTok theo từng hàng (Row 1..8) cho các máy còn thiếu.

## 2. Lệnh Thực Thi Chuẩn
Luôn sử dụng Python interpreter chuẩn của Taadaa farm (chứa đầy đủ các dependencies: openpyxl, requests, uiautomator2, adbutils):
```bash
D:\Taadaa\python-envs\automation\Scripts\python.exe D:/Taadaa/tools/ensure_row_accounts.py <row> --machines <list_machines>
```
*Ví dụ cho Máy 80 Row 5:*
```bash
D:\Taadaa\python-envs\automation\Scripts\python.exe D:/Taadaa/tools/ensure_row_accounts.py 5 --machines 80
```

## 3. Quy Trình Tự Động Bên Trong Script
1. **Kiểm tra mail:** Quét `D:/OneDrive/TaadaaData/<host>/gmail_clean_v2.xlsx`. Nếu thiếu, tự gọi `buy_hotmail.py` để mua Hotmail OAuth2 nạp bổ sung.
2. **Kích hoạt batch reg:** Thiết lập `TIKTOK_REG_TARGET_STTS=<machines>` và gọi `_run_all_targets.py` trong thư mục `D:/Taadaa/Tiktok_Reg`.
3. **Merge kết quả & Đồng bộ:**
   - Đọc kết quả `tracking_result` mới nhất từ artifacts.
   - Ghi vào workbook tracking `D:/OneDrive/TaadaaData/<host>/taikhoan_dat_v2_updated .xlsx` đúng vị trí STT và Row.
   - Gọi `sync-safe-workbook.py` để đồng bộ sang `taikhoan_run_safe.xlsx`.

## 4. Hậu Kiểm & Nghiệm Thu
1. **Kiểm tra dữ liệu:**
   - Đối chiếu dòng STT tương ứng trong `taikhoan_dat_v2_updated .xlsx`.
   - Đối chiếu dòng tương ứng trong `taikhoan_run_safe.xlsx`.
2. **Ảnh nghiệm thu (Proof Screenshot):**
   - Đọc trường `proof_screenshot` từ `tracking_result_*.json` trong `D:/Taadaa/runtime/<host>/artifacts/runs/social-batch-all/<run_id>/` hoặc `D:/Taadaa/Tiktok_Reg/artifacts/runs/social-batch-all/<run_id>/`.
   - Trả về đường dẫn ảnh với cú pháp `MEDIA:<path>` trên một dòng riêng.
3. **Giải phóng máy:**
   - Đưa máy về màn hình HOME (`input keyevent 3`).
   - Tắt ứng dụng TikTok (`am force-stop com.zhiliaoapp.musically`).
   - Nhả device lock.

## 5. Invariant An Toàn Merge Tracking (Chống Stale Artifact & Duplicate Ghi Đè - 2026-09-23)
*Bài học Sol Auditor thẩm định sau sự cố ghi đúp Row 7 sang Row 5:*
1. **Chống Stale Artifact (Quét lùi về quá khứ):**
   - Khi chạy batch reg, ghi nhận `batch_start_time = datetime.now()`.
   - `apply_results()` chỉ được đọc các thư mục run sinh ra từ thời điểm batch (`st_mtime >= batch_start_time - 10s`).
   - Nếu batch hiện tại có 0 acc thành công: TUYỆT ĐỐI KHÔNG quét lùi về các run cũ trong quá khứ (tránh bốc nhầm kết quả của các phiên trước đó).
2. **Cấm Slot Override:**
   - Lấy `slot` từ trường `tik` trong JSON kết quả thật của máy: `json_slot = ((raw_tik - 1) % 8) + 1`.
   - TUYỆT ĐỐI KHÔNG ép cứng `slot = row` từ tham số CLI khi JSON slot khác row.
3. **Lookup Dòng Chuẩn Xác & Hỗ Trợ Cụm Admin (Máy >= 201):**
   - Dò đúng dòng `(Machine == m, Tik / Slot == slot)` trong sheet `Tài Khoản`.
   - Đối với máy Admin (`m >= 201`): STT Tik tương ứng là `expected_tik = (m - 201) * 8 + slot`. Đối với máy Kibe (`1 <= m <= 80`): `expected_tik = (m - 1) * 8 + slot`.
   - Nhận diện slot linh hoạt qua modulo: `((int(c2) - 1) % 8) + 1 == slot`.
   - **Tự động append (Dynamic Append):** Với workbook Admin khởi tạo động (không có sẵn lưới 640 dòng cố định như Kibe), nếu không tìm thấy dòng (m, slot), tự động append dòng mới `target_row = ws_trk.max_row + 1` thay vì bỏ qua (`skip`).
   - Cột 2 (STT Tik) khi ghi mới: gán `expected_tik` chuẩn theo dải máy, tránh ghi nhầm công thức `(m - 1) * 8 + slot` làm sai lệch STT Tik của cụm Admin.
4. **Hard Guard Chống Duplicate UID & Email:**
   - Quét toàn bộ workbook trước khi commit: nếu `UID` hoặc `Email` đã tồn tại ở bất kỳ hàng nào khác $\rightarrow$ REJECT ngay lập tức, cấm ghi đúp một acc vào 2 slot/hàng khác nhau.

## 6. Vận Hành Cụm Admin (Máy 201 - 280)
Khi chạy `ensure_row_accounts.py` cho cụm máy Admin hoặc chạy `--apply-only`:
```bash
set TAADAA_HOST_CONFIG=D:\Taadaa\machine-config\admin.yaml && D:\Taadaa\python-envs\automation\Scripts\python.exe D:/Taadaa/tools/ensure_row_accounts.py <row> --apply-only
```
- Script sẽ tự nhận diện `host_id = "admin"`, nạp đúng workbook tracking tại `D:\OneDrive\TaadaaData\admin\taikhoan_dat_v2_updated .xlsx` và đồng bộ an toàn sang `taikhoan_run_safe.xlsx`.
- Kết quả merge được lưu log telemetry tại `D:\Taadaa\runtime\admin\artifacts\last_merge_metrics.json`.

