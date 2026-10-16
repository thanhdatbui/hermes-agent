# Kỷ Luật Dispatch Worker Khi Coordinator Hết Budget T1 & Đối Soát Lệch Niche Động Vật Hoạt Hình 3D (16/10/2026 — @vophuc1749 Máy 54 Tik 6)

## 1. Hiện Tượng & Đối Soát Ground Truth
- **Hiện tượng**: User gửi ảnh chụp màn hình TikTok yêu cầu *"Chuẩn hoá acc này"*.
- **Reverse Profile Lookup O(1)**:
  * Username: `@vophuc1749`, Tên hiển thị: *Võ Hữu Quỳnh*, metrics: 1 Following / 4 Followers / 8 Likes.
  * Đối soát SQLite `tiktok_tracker.db` & `taikhoan_run_safe_combined.xlsx`: Xác định chính xác **Máy 54**, **Tik 6** (Cụm Kibe 1..80).
  * Công thức Kibe: $F_{vid} = (54 - 1) \times 8 + 6 = 430$. Kênh đã đăng đúng 5 video khớp với lưới video trên ảnh.
- **Phát hiện Lệch Avatar Nghiêm Trọng (Avatar Drift)**:
  * Toàn bộ 5 video đã đăng trên TikTok đều là **hoạt hình 3D động vật nhân hóa / meme hài hước** lấy từ kho render `D:/TIKTOK-videonuoinick/430/`:
    1. Chú ếch xanh mặc vest đen lấp lánh, đội mũ chóp cao (top hat) — 113 views.
    2. Chú mèo con màu cam đeo kính râm đen và dây chuyền vàng bản to — 122 views.
    3. Cận cảnh mèo mướp vàng há to miệng gào thét — 334 views.
    4. Chú ếch xanh mặc leotard đỏ-trắng đu xà đơn thể dục dụng cụ.
    5. Chú mèo 3D màu vàng đội mũ fedora đen, mặc vest bạc cầm micro hát (7 tim, 4 lưu).
  * Trong khi đó, avatar hiện tại trên TikTok lại là ảnh bạn nữ áo len hồng ngồi ghế sofa chơi bài trong phòng khách (kèm bong bóng Story *"Bạn có tin vui?"*).
  * **Nguyên nhân gốc rễ**: File `D:/video goc/430/1.mp4` là video crawl cũ ("Có thể hướng nội hết phần đời còn lại"), tool crop trước đây đã lấy frame từ `video goc` thay vì kho render thực tế `TIKTOK-videonuoinick/430/`, dẫn tới avatar hoàn toàn lệch với nội dung 5 video trên kênh.

## 2. Tiêu Chí 3 Món Chuẩn Hoá Farm (@vophuc1749)
1. **Ghim Video (Pin Rule $\ge 1.000$ view)**:
   * Toàn bộ 5 clip đều $< 1.000$ views (cao nhất là clip 3 đạt 334 views).
   * **Phán quyết**: GIỮ NGUYÊN, KHÔNG GHIM.
2. **Niche & Hashtag**:
   * Niche thực tế: `haihuoc` / `thucung` (Meme động vật 3D).
   * Tạo marker `.manual_hashtag_locked` tại Folder 430 chống sync đè.
3. **Avatar mới**:
   * Trích xuất trực tiếp từ video thực tế của kênh:
     - *Phương án 1*: Chú ếch xanh quý tộc (top hat & vest đen lấp lánh) trích từ clip H1C1 (`5.mp4` frame 30).
     - *Phương án 2*: Chú mèo con Rapper ngầu (kính râm đen & dây chuyền vàng) trích từ clip H1C2 (`4.mp4` frame 30).
   * Cả 2 phương án đều crop chuẩn Center-based $512 \times 512$, bo viền tròn xanh kiểm tra headroom và chin clearance an toàn, không bị lẹm chi tiết.

## 3. Cạm Bẫy Hết Budget Ghi T1 Của Coordinator & Chuẩn Dispatch Worker
- **Bẫy Guard chặn ghi**:
  * Khi Coordinator tạo/sửa quá 5 files hoặc > 200 dòng, Guard kích hoạt chặn vô điều kiện:
    `[COORDINATOR WRITE DENIED]: Hết ngân sách T1 (tối đa 5 files, <= 200 dòng). BẮT BUỘC DISPATCH WORKER!`
- **Bẫy Vi Phạm Contract Dispatch (`delegate_task`)**:
  * Nếu context trong `delegate_task` không khai báo đúng cấu trúc chuẩn của Guard, lệnh dispatch sẽ bị từ chối ngay lập tức:
    `[COORDINATOR GUARD - CONTRACT VIOLATION]: MISSING_TASK_KIND: Bắt buộc khai báo 'TASK_KIND: EDIT' hoặc 'TASK_KIND: INVESTIGATE' trong context (SCOPE LOCK MISSING TARGET FILE)`.
- **Cấu Trúc Dispatch Chuẩn Bắt Buộc**:
  ```text
  TASK_KIND: EDIT
  FILE: D:/Taadaa/reports/<script_name>.py
  FOCUSED_TEST: python -m pytest D:/Taadaa/reports/<script_name>.py::<test_func> -q

  Môi trường: Windows 10, repo whitelist: D:/Taadaa
  Scope lock: CHỈ tạo và sửa đúng 1 file D:/Taadaa/reports/<script_name>.py
  Lệnh verify bắt buộc: python -m pytest D:/Taadaa/reports/<script_name>.py::<test_func> -q
  Ngân sách: <= 5 iterations, hoàn thành nhanh < 2 phút.

  FAIL_FAST: Nếu trong <= 3 iterations đầu thấy scope bất khả thi với budget 15 calls thì DỪNG NGAY (ABORT)...
  ```
- **Pattern Self-Contained Test Trong File Script**:
  * Worker nhúng hàm `test_*` ngay cuối script để tự chạy pytest focused thỏa mãn Single-File Scope Lock mà không cần tạo thêm file test phụ:
    ```python
    def test_generate_and_verify_avatars():
        main()
        for fname in ["avatar_opt1.jpg", "preview_opt1.jpg", "avatar_opt2.jpg", "preview_opt2.jpg"]:
            p = os.path.join("D:/Taadaa", fname)
            assert os.path.exists(p) and os.path.getsize(p) > 1000
    ```
