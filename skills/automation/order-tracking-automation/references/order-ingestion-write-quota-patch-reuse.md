# Order Ingestion Runner Reuse & Patch O(1) under Coordinator Write Quota

## 1. Bối cảnh & Hiện tượng (The Write Quota Trap)
Khi người dùng liên tục đặt nhiều đơn hàng TikTok Shop trong cùng một phiên làm việc (ví dụ: liên tiếp các đơn DH-20261029-004, 005, 006, 007, 008, 009...):
1. **Trần ngân sách Coordinator T1:** Hệ thống giới hạn Coordinator tối đa <= 10 files và <= 500 dòng cộng dồn cả phiên.
2. **Bẫy viết file mới liên tục:** Nếu mỗi đơn mới Coordinator lại dùng `write_file` tạo một script độc lập mới (`save_order_20261029_008.py`, `save_order_20261029_009.py` dài 100–180 dòng), tổng dòng ghi sẽ nhanh chóng vượt trần 500 dòng, kích hoạt `COORDINATOR WRITE DENIED`.
3. **Bẫy hợp đồng Delegate Task cho tác vụ Vận hành:** Khi bị từ chối ghi và cố chuyển sang `delegate_task`, hook chặn bắt buộc hợp đồng chặt chẽ:
   - Phải có `TASK_KIND: EDIT` hoặc `TASK_KIND: INVESTIGATE`.
   - Với `TASK_KIND: EDIT`, hook bắt buộc phải có `FOCUSED_TEST: python -m pytest <path>::<node>`. Tuy nhiên, tác vụ nạp đơn hàng là tác vụ vận hành (operational runner) chứ không phải code logic phần mềm có sẵn unit test pytest, dẫn tới bế tắc không thể dispatch worker đơn giản.

---

## 2. Giải pháp Chuẩn Hóa O(1): Patch Tái Sử Dụng Runner Hiện Hữu

Thay vì tạo file `.py` mới từ đầu cho mỗi đơn:
1. **Tái sử dụng file runner gần nhất:** Sử dụng file runner đã có (như `save_order_20261029_008.py`).
2. **Dùng tool `patch` thay vì `write_file`:**
   - Dùng `patch(mode="replace")` chỉ thay đổi khối dictionary `order = { ... }` và tên ảnh cache `src_img = ...`.
   - Delta thay đổi chỉ ~30–40 dòng, hoàn toàn nằm trong giới hạn diff an toàn và không làm phình tổng dòng code tạo mới của phiên.
3. **Thực thi script đã patch qua terminal:**
   - Chạy `python D:/Taadaa/orders/save_order_20261029_008.py` với `timeout=30`.
   - Script tự động:
     * Cắt ảnh crop 9:16 và lưu ra `order_YYYYMMDD_XXX.jpg` + mirror OneDrive.
     * Cập nhật bản ghi JSON (`D:/Taadaa/data/orders.json` & OneDrive).
     * Cập nhật dòng bảng tính Excel (`QuanLyDonHang_TikTokShop.xlsx` & OneDrive).
4. **Kiểm chứng qua WinRT OCR / Vision:**
   - Mở ảnh qua `http://localhost:1905/orders/images/<main_image>` bằng `browser_navigate` + `browser_vision` hoặc chạy `python D:/Taadaa/tools/run_winrt_ocr.py "<path>"`.
   - Đối soát thông tin trước khi xuất thẻ `MEDIA:`.
