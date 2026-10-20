# Avatar Semantic Audit & Device Lock Preflight Invariants (2026-10-20)

## 1. Bối cảnh & Cạm bẫy "Verified=True nhưng ảnh sai hoàn toàn"
- Trong quá trình chuẩn hoá kênh (ví dụ: Máy 15 `@ajbecosmby0`, ngách "Mèo vui"):
  - Runner chuẩn `run_upload_avatar.ps1` hoặc `run_upload_avatar.py` kết thúc với `exit=0, verified=True`, log báo `AVATAR_SMOKE_SUCCESS` và `FORCED_REPLACED_VERIFIED`.
  - Tuy nhiên, khi kiểm tra thực tế trên màn hình Profile, avatar hiển thị lại là **mái bạt/vải che** chứ hoàn toàn không phải con mèo.
  - **Nguyên nhân cốt lõi**: File `D:\video goc\335\avatar.jpg` và `D:\TIKTOK-videonuoinick\117\avatar.jpg` lưu sẵn từ trước vốn là một ảnh không đúng ngách (ảnh mái bạt chụp lên trời). Runner chỉ thực hiện đẩy file cơ học, kiểm tra có upload thành công lên máy chủ TikTok hay không, chứ **không thể kiểm tra ngữ nghĩa nội dung ảnh**.
  - **Cạm bẫy nhận thức (Expectation Bias / Hallucination)**: Coordinator khi báo cáo đã chủ quan ghi "Đã soi mắt... xác nhận đúng mèo trắng mắt xanh" theo suy đoán từ tài liệu đề xuất trước đó, mà không thực sự nhìn từng chi tiết trên ảnh chụp màn hình Profile thực tế.

## 2. Invariant: Thẩm định thị giác 2 lớp (Two-Layer Semantic Vision Audit)
1. **Lớp 1: Pre-Upload Audit (Kiểm tra file nguồn TRƯỚC KHI nạp)**:
   - CẤM TUYỆT ĐỐI tin tưởng mù quáng vào tên file `avatar.jpg` trong các kho `F_src` hoặc `F_vid`.
   - Trước khi copy, đồng bộ hoặc cắm marker `.manual_avatar_locked`, Coordinator/Worker BẮT BUỘC phải mở file ảnh nguồn ra xem bằng vision hoặc trích frame video gốc để xác nhận:
     * Đúng đối tượng ngách (niche mascot/subject): Ví dụ kênh mèo thì ảnh phải rõ ràng là mèo; kênh gym/nữ thì phải đúng người.
     * Ảnh không bị lệch, méo, đen góc, hoặc chứa rác ngoại cảnh (mái nhà, phong cảnh vô nghĩa).
2. **Lớp 2: Post-Upload Audit (Kiểm tra Profile SAU KHI nạp)**:
   - Chụp màn hình Profile thật trên thiết bị (`reports/m<N>_<username>_rename_confirmed.png`).
   - Cắt (crop) riêng vùng vòng tròn avatar hoặc zoom vào phần trên trang cá nhân để gọi `browser_vision`.
   - Trong câu hỏi gửi `browser_vision`, mô tả trung thực và yêu cầu AI mô tả chính xác những gì nhìn thấy (màu sắc, hình dạng, chi tiết), tuyệt đối không mớm cung theo kỳ vọng.
   - Nếu avatar thực tế khác với avatar dự kiến: BẮT BUỘC thừa nhận ngay lập tức, đánh dấu trạng thái BLOCKED ở khâu Avatar, không bao giờ báo "xong hết".

## 3. Invariant: Preflight Device Lock trước khi nạp lại
- Khi cần nạp lại avatar sau khi đã thay thế file nguồn chuẩn (`m15_opt2_square.jpg`):
  - BẮT BUỘC kiểm tra thư mục `~/.codex/device-locks/machine_<N>.lock.json`.
  - Nếu lock file tồn tại và PID tương ứng đang chạy (ví dụ ca nuôi nick tối `multi-machine-feed-session` lúc 20:03):
    * CẤM TUYỆT ĐỐI kill tiến trình đang chạy của Farm hoặc xóa file lock để tranh chấp máy.
    * Đưa task về trạng thái **BLOCKED kèm bằng chứng (chờ nhả lock)**. Báo cáo rõ ràng: Nguồn ảnh chuẩn đã sẵn sàng trong cả 2 kho (`F_vid` và `F_src`), chờ máy xong ca nuôi sẽ tự động nạp.
