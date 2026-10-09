# Kỷ Luật Đồng Bộ Slot Nghiêm Ngặt & Cơ Chế On-Demand Reg Bù

## 1. Thiết Kế Chuẩn Của Cơ Chế On-Demand Reg Bù
- **Đã xóa bỏ hoàn toàn Cron Reg TikTok dồn ban đêm.**
- **Cơ chế hoạt động:** On-demand theo từng ca nuôi (`ensure_row_accounts.py` hook vào `tiktok_runner.py`):
  + Máy nào **đã có nick** ở Row của ca đó: Cứ lướt feed + nuôi bình thường.
  + Máy nào **thiếu nick** ở Row đó: Tự động mua Hotmail OAuth2 (`buy_hotmail.py`) nếu thiếu mail và kích hoạt `Tiktok_Reg` chạy reg bù độc lập song song, **tuyệt đối không ảnh hưởng đến các máy khác**.
- **CẤM TUYỆT ĐỐI NGỤY TẠO LÝ DO:** Cấm agent suy diễn/bịa đặt các "nguyên tắc an toàn" như "reg tốn tài nguyên nên ca nuôi phải bỏ qua không reg" để thoái thác trách nhiệm khi thấy thiếu nick.

---

## 2. Bẫy Silent Slot Drift Trong `sync-safe-workbook.py` (Lỗi Đồng Bộ Nghiêm Trọng)
### Triệu chứng hiện trường:
- Watchdog báo cáo Đăng Video có hàng loạt máy bị bỏ qua với lý do `Khác (28)` hoặc `missing_account_id`.
- Trong khi đó, báo cáo Lướt Feed vẫn ghi `Tổng máy xử lý: 80 máy` và chạy thành công nhiều máy.
- Script preflight `ensure_row_accounts.py` kiểm tra thì báo: `Toàn bộ máy đã đầy đủ tài khoản, không cần reg` (hoặc chỉ báo thiếu 1-2 máy), dù thực tế Master `taikhoan_dat_v2` thiếu hàng chục máy ở slot đó.

### Root Cause:
- Trong `sync-safe-workbook.py`, logic gán slot có dòng fallback nhét bừa:
  ```python
  else:
      slot_idx = next((i for i in range(8) if machine_slots[machine][i] is None), None)
  ```
- Khi một máy trong Master `taikhoan_dat_v2` có 2 nick trùng slot (ví dụ do folder 9 và folder 17 đều thuộc slot 1, hoặc folder 10 và 18 đều thuộc slot 2):
  + Thay vì giữ đúng slot hoặc để slot thiếu là `None`, script lại tự tiện nhặt nick thừa nhét vào **slot trống đầu tiên** (thường là slot 4 hoặc slot 6).
- Hậu quả dây chuyền:
  1. `taikhoan_run_safe.xlsx` bị nhét ảo nick của slot khác vào Slot 4/6 (ví dụ slot 6 có 77/80 máy có chữ).
  2. `ensure_row_accounts.py` đọc `taikhoan_run_safe.xlsx` thấy có nick nên **BỊ MÙ**, tưởng đủ nick và bỏ qua không reg bù!
  3. Khi chạy ca: Feed nuôi nhầm nick slot khác trên ca slot 6.
  4. Khi sang bước Đăng Video: Hook đăng video tra cứu `Tik6.xlsx` (vốn được sync strict theo công thức modulo `(folder - 1) % 8 + 1`) → `Tik6.xlsx` trống trơn → văng lỗi `missing_account_id` hàng loạt!

---

## 3. Kỷ Luật Khắc Phục (Strict Slot Mapping)
1. **Quy tắc Modulo Bắt Buộc:**
   - Slot của một tài khoản được tính duy nhất qua: `slot = (folder_video - 1) % 8 + 1` (1-indexed).
   - Slot 1..8 tương ứng chính xác với Tik1..Tik8 và Row 1..Row 8 trong `taikhoan_run_safe.xlsx`.
2. **CẤM TUYỆT ĐỐI FALLBACK NHÉT BỪA SLOT TRỐNG:**
   - Nếu máy không có nick ở Slot N trong Master `taikhoan_dat_v2`, vị trí Slot N trong `taikhoan_run_safe.xlsx` **BẮT BUỘC PHẢI LÀ `None` / RỖNG**.
   - CẤM mọi dòng code kiểu `next((i for i in range(8) if machine_slots[machine][i] is None), None)`.
3. **Đảm bảo tính nhất quán 1:1:**
   - `taikhoan_run_safe.xlsx` (slot N) và `TikN.xlsx` (cột ID) **bắt buộc phải phản ánh chính xác cùng 1 danh sách nick từ `taikhoan_dat_v2`**.
   - Khi `taikhoan_run_safe.xlsx` để trống đúng thực tế, `ensure_row_accounts.py` sẽ phát hiện chính xác các máy thiếu và tự động kích hoạt mua mail / reg bù đúng thiết kế.
