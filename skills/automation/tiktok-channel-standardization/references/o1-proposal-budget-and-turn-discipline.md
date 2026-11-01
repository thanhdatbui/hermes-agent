# Kỷ Luật Tránh Cháy Budget Điều Phối Khi Chuẩn Hoá Kênh (O(1) Proposal Discipline)

## 1. Bản Chất Vấn Đề (Iteration & Write Budget Exhaustion)
- Trong quy trình chuẩn hoá kênh (`tiktok-channel-standardization`), Coordinator thường xuyên phải đối mặt với hai rào cản kiểm soát nghiêm ngặt:
  1. **Giới hạn số lượt gọi công cụ (Turn Budget Limit):** Nếu lặp lại nhiều vòng lặp nhỏ giọt (thử crop, đo Laplacian, chạy OCR, navigate HTML, chụp ảnh view từng tí một), Coordinator sẽ chạm trần iterations trước khi kịp xuất bản bảng Proposal Canvas cuối cùng.
  2. **Chốt chặn hạn mức ghi T1 (Coordinator Write Limit):** Coordinator bị giới hạn nghiêm ngặt về số file ghi (`<= 10 files`) và tổng số dòng code nghiệp vụ (`<= 500 lines`). Khi viết nhiều file script tạm (`tmp_inspect_*.py`, `tmp_crop_*.py`), Coordinator sẽ kích hoạt báo động `[COORDINATOR WRITE DENIED]`.
  3. **Rào cản Delegate Task Contract:** Việc dispatch worker qua `delegate_task` bị khóa bởi các invariant khắt khe (`TASK_KIND: EDIT`, `OLD_STRING`, `DIFF_BUDGET <= 30 lines`). Cố gắng dùng subagent để viết cả một file script canvas 100+ dòng mới sẽ bị Gate chặn ngay lập tức (`DIFF_BUDGET_EXCEEDED`).

## 2. Kỹ Thuật Đóng Gói Một Lần (One-Shot Standalone Canvas Generation)
Để đưa task về đích trong vòng <= 5 lượt gọi công cụ mà không vi phạm bất kỳ guard nào:
1. **Khảo sát tập trung O(1) trong 1 lượt terminal duy nhất:**
   - Sử dụng thư viện `cv2` và `winrt_ocr_util` trong đúng **1 script duy nhất** hoặc tái sử dụng template có sẵn:
     * Quét nhanh các frame đại diện (`.avatar_work/representative_frames`).
     * Lọc nhanh khuôn mặt qua Haar Cascade + WinRT OCR rỗng (`text == ''`).
     * Đo độ sắc nét Laplacian (`cv2.Laplacian(...).var()`), lấy top 4 khung hình đẹp nhất.
2. **Tận dụng Script / Template Canvas có sẵn:**
   - Thay vì tạo thêm nhiều file script `tmp_*.py` làm cạn kiệt write budget của Coordinator:
     * Tìm các script mẫu canvas gần nhất trong `D:/Taadaa/tools` (ví dụ `build_m274_vyvy_proposal_canvas.py`, `build_m18_hakha_proposal_canvas.py`).
     * Chạy script có nhận tham số CLI hoặc patch đúng các hằng số toạ độ/đường dẫn thay vì tạo file mới từ đầu.
3. **Đăng ký Receipt & Gửi Proposal Dứt Điểm:**
   - Sau khi canvas được xuất bản, mở file bằng browser và gọi `browser_vision` kiểm tra mắt thật.
   - Đăng ký `create_vision_receipt` và gửi thẻ `MEDIA:` kèm bảng đề xuất 5-in-1 ngay trong lượt, không kéo dài sang các vòng lặp kiểm tra phụ.
