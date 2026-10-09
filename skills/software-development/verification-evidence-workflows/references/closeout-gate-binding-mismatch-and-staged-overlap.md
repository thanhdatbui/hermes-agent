# Pitfall: Closeout Gate "Binding Mismatch: Staged/Working-Tree Candidate Overlaps Committed HEAD" & Tier Invariant Testing (03/10/2026)

## 1. Hiện Trường & Triệu Chứng
Khi chạy Closeout Gate:
```bash
python D:/Taadaa/tools/closeout_gate.py --repo "D:/Taadaa/tools" --base origin/main --json-output
```
Quy trình dừng ở Step 2 với lỗi:
```text
STEP 2: EXTRACT CANDIDATE DIFF
· Không có staged diff, thử git diff HEAD...
· Extracted diff: 3 file(s), 3893 chars
✔ Extracted valid diff: 3 file(s), 3893 chars
✘ binding mismatch: staged/working-tree candidate overlaps committed HEAD
```
Lệnh thoát ngay với exit code 1 trước khi chạy test suite hoặc gọi reviewer chấm điểm.

## 2. Nguyên Nhân Gốc Rễ
- `closeout_gate.py` có cơ chế kiểm tra tính toàn vẹn chữ ký byte (staged diff byte sha256 binding).
- Khi repository không có staged diff (`git diff --cached` rỗng), gate trích xuất dự phòng diff từ working tree (`git diff HEAD`).
- Gate so sánh danh sách các file trong candidate diff với commit vừa tạo ở `HEAD`.
- **Nếu commit ở `HEAD` vừa sửa các file X, Y, Z, và working tree TIẾP TỤC CÓ UNSTAGED DIFF trên chính các file X, Y, Z đó**, gate phát hiện sự chồng lấn (**binding mismatch**): candidate unstaged diff đè lên phạm vi vừa commit của `HEAD`.
- Mục đích: Chống tình trạng "commit dở dang", bỏ sót hunk hoặc lẫn lộn giữa code đã commit ở HEAD và code mới sửa thêm ở working tree.

## 3. Cách Khắc Phục Chuẩn Xác
1. **Stage tường minh các file thay đổi (Khuyến nghị số 1)**:
   Nếu các thay đổi trên working tree là mã nguồn của lượt chỉnh sửa mới chuẩn bị commit:
   ```bash
   git add <target_files>
   ```
   Khi có staged diff, `closeout_gate.py` sẽ trích xuất trực tiếp `git diff --cached` với chữ ký byte SHA256 rõ ràng, vượt qua kiểm tra chồng lấn unstaged của HEAD.
2. **Nếu đã commit ở HEAD nhưng working tree còn sót dirt không mong muốn**:
   Kiểm tra `git diff` xem có phải các file thừa/rác chưa revert không. Revert dirt thừa để working tree hoàn toàn clean:
   ```bash
   git checkout -- <file_thua>
   ```
   Khi working tree clean, Closeout Gate so sánh `HEAD~1` hoặc `origin/main` sẽ pass 100%.
3. **Cấu hình tham số `--base` chính xác**:
   - Nếu commit đã tạo ở `HEAD` và working tree đã clean: chạy `--base HEAD~1` để review đúng commit vừa tạo.
   - Nếu chưa commit và đang có staged diff: chạy `--base HEAD` để review đúng staged changeset.

## 4. Kiểm Thử Bất Biến Phân Bậc (Hierarchical Tier Mutual Exclusivity Testing)
- **Vấn đề thực tế**: Khi phân loại tài khoản/sản phẩm theo các bậc tăng dần (ví dụ `🔥 ĐỀ XUẤT` vs `🚀 TIỀM NĂNG`), nếu các cờ boolean dùng các ngưỡng số chia sẻ (như `delta_heart >= 50` và `delta_heart >= 30`), đối tượng đạt bậc cao sẽ tự động thỏa mãn bậc thấp, gây lỗi hiển thị trùng cả hai badge đồng thời.
- **Giải pháp code**: Bậc cao hơn phải loại trừ bậc thấp:
  ```python
  is_potential = not is_trending and ((h_val >= 50 and f_val <= 30) or (delta_h >= 30))
  ```
- **Kiểm thử bất biến bắt buộc**: Test suite phải có assertion bất biến bao phủ toàn bộ tập item:
  ```python
  def test_exclusive_trending_and_potential(temp_db):
      result = get_farm_data(temp_db)
      for item in result["items"]:
          assert not (item["is_trending"] and item["is_potential"]), f"{item['username']} bị trùng cả 2 cờ trending và potential"
  ```
