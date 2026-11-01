# Kỷ Luật Đối Soát Niche Video Thật vs Bẫy Cột Keyword Excel & Quy Chuẩn Duyệt Canvas Trước Khi Nạp Avatar

## 1. Cạm Bẫy Cột Keyword Trong Excel vs Mỏ Neo Chân Lý (Ground Truth)
- **Hiện tượng thực tế:** Trong các file quản lý Farm (`Tik<N>.xlsx`, `taikhoan_run_safe.xlsx`), cột `Keyword Video` thường xuyên bị ghi nhầm, copy đè hoặc lệch ngách từ các session cũ (ví dụ: ghi nhãn `Xe` nhưng kho video 100% là `Câu cá`, ghi `Anime` nhưng thực tế là `Vlog Nữ Creator`).
- **Bẫy tâm lý thiên kiến mỏ neo (Anchor Bias):**
  - Khi Coordinator tra cứu toạ độ kênh và thấy cột `Keyword` trong Excel ghi "Xe", mắt Coordinator bị ám thị và tự động suy diễn sai các thumbnail sông nước/hồ câu thành "đường cao tốc, khoang lái xe ô tô".
  - Khi User hỏi vặn: *"Cái video cắn đề xuất thuộc niche nào?"*, Coordinator vẫn ngoan cố cãi theo dữ liệu Excel thay vì kiểm tra tệp video thực tế.
- **KỶ LUẬT BẮT BUỘC (INVARIANT GROUND TRUTH):**
  1. CẤM TUYỆT ĐỐI lấy chữ trong cột `Keyword` Excel để cãi lại User hoặc làm căn cứ phán quyết ngách.
  2. BẮT BUỘC kiểm tra trực tiếp kho video thật trên đĩa vật lý:
     - Kibe Local: `D:/TIKTOK-videonuoinick/<F_vid>` và `D:/video goc/<F_src>`.
     - Admin Remote: `D:/TIKTOK-videonuoinick-admin/<F_vid>` và `D:/video goc may 2/<F_src>`.
  3. Cắt crop từng thumbnail video cắn đề xuất trên ảnh profile kênh gửi về, soi mắt qua `browser_vision` xác định hành động, chủ thể và không gian thực tế (cần câu, hồ nước, con cá, trang phục...).

---

## 2. Invariant Trình Bảng Proposal Canvas Trước Khi Thực Thi (Chống Nạp Vội Vàng)
- **Lỗi phổ biến:** Sau khi trích xuất được một frame đẹp, Coordinator tự ý nạp đè ngay ảnh đó lên profile máy thật mà không trình bảng so sánh.
- **Quy chuẩn 4 Card Proposal Canvas:**
  - BẮT BUỘC kết xuất bảng Canvas 4 phương án tròn viền xanh lá (PA 1, PA 2, PA 3, PA 4) với các góc quay/chủ thể khác nhau.
  - Kiểm tra độ sắc nét bằng phương sai Laplacian (`var() >= 50`).
  - Kiểm tra WinRT OCR text phải rỗng (`''`) đảm bảo 100% sạch chữ, không dính watermark, phụ đề báo chí hay nồng độ cồn.
  - Gửi ảnh Canvas `MEDIA:<path>` kèm receipt vision và HỎI Ý KIẾN User chọn phương án trước khi gọi runner nạp avatar lên điện thoại.

---

## 3. Khóa Cơ Học Kiểm Tra Mạng (Preflight Network Gate) Bắt Buộc Trong Mọi Runner
- **Nguyên nhân sự cố:** Khi thiết bị Android bị rớt proxy (dính cờ `NOT_VALIDATED`, icon Wi-Fi có dấu chấm than `!`), ứng dụng TikTok không kết nối được server, dẫn đến khi lưu Bio hoặc Tên sẽ bị nảy toast lỗi **`Không thể lưu`**.
- **Chốt chặn Fail-Closed O(1):**
  - Tái sử dụng 100% hàm có sẵn trong core:
    ```python
    from automation_core.adb import AdbClient
    from automation_core.preflight import require_android_vpn
    ```
  - Trong mọi runner thao tác UI (`do_rename_canonical_runner.py`, avatar, pin video...), ở đầu hàm thực thi `_execute_...` bắt buộc khởi tạo `AdbClient` và gọi `require_android_vpn(adb_client, required=True, interface="wlan0", verify_live_ip=True)`.
  - Nếu proxy chết hoặc Wi-Fi mất mạng, runner lập tức thoát ngay (`return 2` / Fail-Closed), không bao giờ được phép thao tác UI mù làm tăng rủi ro shadowban tài khoản.
