# Multi-File Batch Rollback and Baseline Drift Audit Architecture (October 2026)

## 1. Context & Bối Cảnh Lỗi
Trong quá trình hoàn thiện `unified_patch_pipeline.py` (nối xích tự động từ Gate 1 đến Gate 6):
1. **Lỗ hổng dirty baseline lén lút (P0):**
   - Trước đây chỉ dùng `set(current_changed) - set(baseline_changed) - scope`.
   - Nếu một file đã dirty từ trước ở S0 (ngoài scope), sau đó worker ở S2 sửa tiếp nội dung file này thì file đó vẫn nằm trong `baseline_changed`.
   - Kết quả: phép trừ tập hợp loại bỏ file đó, làm Gate 5 bị "mù" trước hành vi sửa lén file dirty ngoài scope!
2. **Lỗ hổng rollback chắp vá (P0):**
   - Khi task sửa nhiều file (multi-file patch), nếu file 1 sửa thành công nhưng file 2 thất bại (exit != 0 hoặc timeout): code cũ chỉ fail mà không rollback sạch sẽ, để lại repo ở trạng thái nửa vá (dirty working tree).
   - Khi chạy S3 (unit test fail) hoặc S4 (canary fail): code cũ không rollback hoặc chỉ rollback file trong scope, bỏ sót các file rác sinh ra ngoài scope.

## 2. Kiến Trúc Khắc Phục Cơ Giới Hoá

### A. Snapshot SHA256 & Bắt Drift Nội Dung Baseline (`detect_baseline_content_drift`)
- Tại **S0 (Precheck):**
  - Quét `baseline_changed = get_git_changed_files(repo)`.
  - Với mọi file `f` thuộc `baseline_changed - scope`: đọc raw bytes và lưu `baseline_file_hashes[f] = sha256(bytes)`. Nếu file bị xóa trước đó, lưu sentinel `<missing>`.
- Tại **S2, S3, S4 và cả khi Confirm Rebaseline:**
  - Chạy hàm `detect_baseline_content_drift(repo, baseline_file_hashes)`: so sánh lại SHA256 trên đĩa với snapshot tại S0.
  - Bất kỳ file nào ngoài scope bị đổi content (SHA256 khác S0) đều lập tức bị bắt bài và coi là **Scope Gate Violation**.

### B. Hàm Khôi Phục Toàn Diện (`full_rollback`)
Thống nhất một hàm rollback duy nhất dùng chung cho toàn bộ các chặng S2 (Patch), S3 (Test), S4 (Canary):
1. **Khôi phục File trong Scope:** Ghi đè lại nguyên trạng raw bytes từ `pre_bytes` chụp tại S0.
2. **Khôi phục File ngoài Scope:**
   - Quét lại `get_git_changed_files(repo)` để tìm `out_of_scope = (current - baseline) - scope`.
   - File có trong Git HEAD: chạy `git checkout HEAD -- <path>`.
   - File untracked mới sinh ra: xóa thẳng tay khỏi đĩa (`unlink`).
3. **Khôi phục Drift Baseline:** Với các file dirty baseline bị sửa lén, ghi trả lại bytes ban đầu lúc S0.
4. **Hậu kiểm sau Rollback:** Quét lại git status một lần nữa để xác nhận `residual_dirty == []`. Nếu còn sót file bẩn, ghi cảnh báo vào state audit.

### C. Hậu Kiểm Thay Thế Tuyệt Đối (`count == 1`)
- Trong hậu kiểm độc lập S2: trước khi mô phỏng `replace(old_string, new_string, 1)`, bắt buộc kiểm tra `current_text.count(old_string) == 1`.
- Nếu `count == 0` (không tìm thấy) hoặc `count > 1` (anchor không duy nhất): lập tức từ chối và kích hoạt `full_rollback`, ngăn chặn việc thay thế nhầm vị trí.

## 3. Quy Tắc Bất Biến Vận Hành
1. Mọi chặng trong pipeline (S2, S3, S4) khi gặp lỗi hoặc timeout BẮT BUỘC phải gọi `full_rollback` trước khi thoát.
2. Cấm chỉ dựa vào tên file để khóa scope; bắt buộc phải khóa bằng cả SHA256 hash của baseline và git diff name-only.
3. Không bao giờ để lại repo ở trạng thái bẩn sau một run thất bại.
