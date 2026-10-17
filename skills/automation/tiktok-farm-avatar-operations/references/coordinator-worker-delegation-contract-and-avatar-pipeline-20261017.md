# Kỷ Luật Điều Phối Coordinator vs Worker Trong Chuẩn Hoá Kênh & Avatar Farm (17/10/2026)

## 1. Rào Cản Ngân Sách Coordinator T1 & Phân Vai Thực Thi
- **Hiện tượng**:
  - Khi Coordinator thực hiện nhiều thao tác thăm dò hoặc tạo file tạm bằng `write_file`/`patch`, hệ thống sẽ kích hoạt guard:
    `⛔ [COORDINATOR WRITE DENIED]: Hết ngân sách T1 (tối đa 5 files, <= 200 dòng cộng dồn cả session)`.
  - Đồng thời Coordinator terminal bị chặn `python -c` có thao tác ghi file/xóa/subprocess (`COORDINATOR TERMINAL BLOCKED: 'python -c' chỉ dùng để kiểm chứng read-only`).
  - `execute_code` bị vô hiệu hóa cho Coordinator (`COORDINATOR GUARD - EXECUTE_CODE DISABLED`).
- **Phân vai chuẩn xác (Division of Labor)**:
  - **Worker**: Đảm nhận việc viết/vá file script xử lý media (`write_file`/`patch`) dưới Scope Lock của `delegate_task`.
  - **Coordinator**: Đảm nhận việc chạy script (`python D:/Taadaa/reports/<script>.py` qua `terminal` timeout <= 60s), soi mắt kiểm định ảnh qua `browser_vision`, và điều phối runner upload.

---

## 2. Hợp Đồng Delegate Task Chuẩn Hóa Cho Worker Sửa Code (Gate 1 - Gate 5)
Khi cần Worker tạo hoặc vá script xử lý avatar, prompt `delegate_task` BẮT BUỘC tuân thủ nghiêm ngặt 5 yếu tố contract:
1. `TASK_KIND: EDIT` (Tuyệt đối không dùng `INVESTIGATE` khi cần tạo/sửa file, vì `INVESTIGATE` sẽ ép Worker vào chế độ Read-Only cấm ghi file 100%).
2. `FILE: <đường_dẫn_tuyệt_đối>` (Scope Lock bắt buộc, ví dụ `D:/Taadaa/reports/generate_candidate_avatars.py`).
3. `OLD_STRING: <<< ... >>>` và `NEW_STRING: <<< ... >>>`:
   - **Quy tắc Diff Budget O(1)**: Tổng số dòng của `OLD_STRING` + `NEW_STRING` BẮT BUỘC $\le 30$ dòng (theo `git diff --numstat`).
   - *Kỹ thuật tối ưu*: Không thay thế toàn bộ file monolith. Chỉ neo vào 2-3 dòng cuối (ví dụ `print("SUCCESS")\nrun()`), thay thế bằng logic cô đọng, viết one-liner hoặc gom lệnh trong phạm vi $\le 15$ dòng.
4. `FOCUSED_TEST: python -m pytest <path>::<node>` (Ví dụ `python -m pytest D:/Taadaa/tests/test_admin_ssh.py::test_command`).
5. `FAIL_FAST: Nếu trong <= 3 iterations đầu thấy scope bất khả thi với budget 15 calls thì DỪNG NGAY (ABORT) và trả về anchor + proposed contract, cấm đốt hết budget để mò file rồi fail im lặng.`

---

## 3. Quy Trình Chuẩn Hoá Kênh 3 Món (End-to-End Pipeline)
1. **Định vị toạ độ $O(1)$**:
   - Đọc `D:/Tik<N>.xlsx` sheet `TaiKhoan`:
     * Cột 1: `máy`
     * Cột 3: `taiKhoan`
     * Cột 4: `Sttvideo` ($F_{vid}$ - kho render nuôi tại `D:/TIKTOK-videonuoinick/<Sttvideo>`)
     * Cột 6: `video gốc` ($F_{src}$ - kho video gốc tại `D:/video goc/<video_goc>`)
2. **Khám nghiệm Pin Gate & Lưới Video**:
   - Soát view các video trên lưới profile:
     * Nếu video cao nhất $< 1.000$ views $\to$ **CẤM PIN VIDEO** (giữ nguyên lưới tự nhiên).
     * Chỉ pin video khi view $\ge 1.000$ views.
3. **Trích xuất 2 Phương án Avatar $512 \times 512$**:
   - Sử dụng Haar cascade phát hiện khuôn mặt:
     * Căn tâm ngũ quan, scale $\approx 2.2 \times$ kích thước khuôn mặt.
     * Dịch tâm $cy$ hợp lý ($0.52 - 0.55$) để chừa khoảng hở headroom phía trên đỉnh đầu, chống bị chém trán / lẹm cằm khi cắt tròn.
   - Ghép ảnh so sánh `nguyenkhoi1403_avatar_comparison.jpg` gồm 2 phương án đặt cạnh nhau có viền tròn màu xanh lá mô phỏng avatar TikTok và tiêu đề vàng phân biệt.
4. **Invariant Soi Mắt Qua Vision Trước Khi Gửi**:
   - Dùng `browser_navigate` mở `file:///D:/Taadaa/reports/<comparison>.jpg`.
   - Gọi `browser_vision` kiểm tra thực tế: xác nhận đủ 2 phương án, viền tròn không lẹm ngũ quan, không lỗi hiển thị $\to$ gửi ảnh kèm thẻ `MEDIA:` và mô tả ngắn gọn nội dung đã thấy.
5. **Kích hoạt Runner Nạp Avatar Ngay Lập Tức Khi User Chọn**:
   - Đồng bộ file `avatar.jpg` vào các kho liên quan (`video goc/<src>`, `video goc/<vid>`, `TIKTOK-videonuoinick/<vid>`).
   - Tạo marker `.manual_avatar_locked` tại các kho.
   - Cập nhật registry `D:/Taadaa/data/manual_avatar_protected_folders.json`.
   - Cập nhật `avatar_replace_queue` trong `D:/Taadaa/data/tiktok_tracker.db` về trạng thái `PENDING`.
   - Kích hoạt runner chuẩn qua terminal background:
     `python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <tik> --machine <machine>` với `background=True, notify_on_complete=True, timeout=600`.
