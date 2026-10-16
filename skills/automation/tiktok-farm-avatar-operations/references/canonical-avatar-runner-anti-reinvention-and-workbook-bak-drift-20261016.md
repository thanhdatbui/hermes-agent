# Kỷ Luật Chống Đẻ Script Mới Thay Thế Canonical Runner & Bẫy Workbook .bak Drift (2026-10-16)

## 1. Bối Cảnh Sự Cố & Lời Nhắc Nhở Từ User
- **Sự cố thực tế**:
  - Khi thực hiện đổi avatar cho kênh `@giathu0709` (Máy 65 Tik 4), Coordinator chạy script có sẵn `python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik 4 --machine 65`.
  - Runner canonical báo lỗi: `Workflow target error: Missing required fields: Folder Video`.
  - Thay vì kiểm tra nguyên nhân gốc rễ (file `.bak` fallback hoặc transient lock), Coordinator vội vàng tạo một script wrapper mới tại `D:/Taadaa/tmp/test_runner_65.py` để gọi module `tiktok_workflow`.
  - User phát hiện và chất vấn gay gắt: *"Chưa hiểu vì sao có script upload ava r mà phải đi viết script ms v"*.

---

## 2. Nguyên Tắc Cốt Lõi: REUSE > EXTEND > NEW (CẤM ĐẺ SCRIPT MỚI)
1. **Runner Canonical là Duy Nhất**:
   - Mọi thao tác nạp avatar đơn máy hoặc batch BẮT BUỘC dùng runner canonical chuẩn đã được kiểm chứng của Farm:
     * Standalone launcher: `D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1 -Tik <N> -ForceAvatarMachineList "<M>" -MaxParallel 1`
     * Tool bọc tiện ích: `python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <N> --machine <M>`
   - **CẤM TUYỆT ĐỐI**: Tự viết script tạm `test_runner_*.py`, `upload_m*.py`, `do_upload_avatar_*.py` trong `tmp/` hay `tools/` để chạy thay thế khi script canonical gặp lỗi.
2. **Quy Trình Chẩn Đoán Khi Canonical Runner Báo Lỗi**:
   - Khi runner canonical exit != 0, mục tiêu là tìm ra lý do khiến runner fail (môi trường, lock, workbook) và khắc phục tại gốc, sau đó gọi lại chính runner canonical.

---

## 3. Bẫy Fallback Workbook `.bak` & Lỗi `Missing required fields: Folder Video`
### A. Cơ chế lỗi ngầm
Trong `D:\Taadaa\Tiktok-video\scripts\tiktok_workflow\account_source.py`:
- Khi đọc file workbook chính (ví dụ `Tik4.xlsx`), nếu gặp `read_err` (do OneDrive đang sync, hoặc process khác vừa ghi atomic chưa nhả handle trong 0.1s), `AccountSource` sẽ tự động tìm file dự phòng:
  `bak_path = workbook_path.with_suffix(workbook_path.suffix + ".bak")`
- Nếu file `.bak` này là file backup cũ (thiếu cột `Folder Video (Render Dich)` hoặc format hỏng), `AccountSource` sẽ nạp từ file `.bak` và raise:
  `Workflow target error: Missing required fields: Folder Video`
- Kết quả: File chính `.xlsx` hoàn toàn đầy đủ dữ liệu, nhưng runner vẫn fail liên tục 5 lần vì bị kẹt đọc file `.bak` lỗi!

### B. Giải pháp khắc phục
1. **Kiểm tra và dọn dẹp file `.bak` stale**:
   - Đảm bảo file `.bak` không bị cũ/lệch cấu trúc so với file chính.
   - Nếu phát hiện file `.bak` hỏng, xóa hoặc đồng bộ lại từ file `.xlsx` chính.
2. **Đảm bảo ghi workbook an toàn trước khi chạy runner**:
   - Sử dụng `openpyxl` với đầy đủ `wb.save()` và `wb.close()`.
   - Chờ 1–2 giây sau khi lưu workbook để OneDrive giải phóng file lock hoàn toàn trước khi khởi động runner PowerShell.

---

## 4. Kỹ Thuật Type Safety Trong `manual_avatar_protected_folders.json`
- **Hiện tượng**:
  - Danh sách `protected_folders` trong JSON có thể bị nhiễm các phần tử kiểu chuỗi do các session cũ append dạng string (ví dụ: `[2, 26, ..., '458', '462']`).
  - Khi script thực hiện `data['protected_folders'] = sorted(list(set(data['protected_folders'])))`, Python 3 sẽ crash ngay lập tức:
    `TypeError: '<' not supported between instances of 'str' and 'int'`
- **Quy chuẩn cập nhật an toàn 100%**:
  ```python
  raw_folders = data.get('protected_folders', [])
  int_folders = set()
  for x in raw_folders:
      try:
          int_folders.add(int(x))
      except (ValueError, TypeError):
          pass
  int_folders.add(int(target_folder))
  data['protected_folders'] = sorted(list(int_folders))
  ```

---

## 5. Checklist Bắt Buộc Trước Khi Chạy Standalone Avatar Upload
- [ ] File ảnh avatar mới đã được sao chép vào cả 3 kho: `D:\TIKTOK-videonuoinick\<F_out>\avatar.jpg`, `D:\video goc\<F_src>\avatar.jpg`, `D:\video goc\<F_out>\avatar.jpg`.
- [ ] Đã tạo marker vật lý `.manual_avatar_locked` và `.manual_hashtag_locked` tại các folder trên.
- [ ] Đã thêm folder vào `manual_avatar_protected_folders.json` bằng kỹ thuật type-safe.
- [ ] Đã cập nhật `Avatar = PENDING` trong file `Tik<N>.xlsx` tương ứng và xác nhận workbook đã đóng hoàn toàn.
- [ ] Đã cập nhật `avatar_replace_queue` trong SQLite `D:\Taadaa\data\tiktok_tracker.db` sang `PENDING`.
- [ ] Chạy duy nhất canonical runner: `python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <N> --machine <M>`.
