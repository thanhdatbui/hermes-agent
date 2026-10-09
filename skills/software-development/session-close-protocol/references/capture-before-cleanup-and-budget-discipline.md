# Capture-Before-Cleanup & Anti-0-Files-Modified Discipline (20/09/2026)

## 1. Bài học về lỗi gửi ảnh Launcher HOME / Feed thay vì Màn hình Artifact

### Hiện tượng sai phạm
Khi hoàn thành can thiệp UI (như dọn dẹp cache TikTok), Agent có thói quen:
1. Gửi lệnh teardown (`am force-stop` và `input keyevent KEYCODE_HOME`).
2. Sau đó mới gọi `screencap` chụp màn hình và đính kèm `MEDIA:`.
3. Kết quả: Ảnh gửi về Telegram là màn hình chính Launcher Android hoặc màn hình Feed dang dở, hoàn toàn không có bằng chứng chứng minh task đã thành công (không thấy "Bộ nhớ đệm: 0,0MB" hay "Tải về: 0,0MB").

User phản hồi gay gắt:
> *"Này trang feed mà phải home đâu"*
> *"Ý là đáng lẽ lỗi clear cache thì mày phải chụp lúc mày clear cache thành công chứ"*

### Root Cause
- **Sequence Inversion**: Đảo lộn thứ tự giữa Verification Capture (chụp bằng chứng) và Teardown Cleanup (dọn dẹp).
- **Assumption vs Observation**: Giả định gửi lệnh ADB là xong và coi screenshot chỉ là thủ tục, vi phạm nguyên tắc Evidence First.

### Quy chuẩn bắt buộc: CAPTURE-BEFORE-CLEANUP GATE
Thứ tự bất biến:
1. `SCREENCAP` trên màn hình artifact đích.
2. `OCR / Readback` xác nhận đúng màn hình và chỉ số mục tiêu.
3. `REPORT` đính kèm ảnh `MEDIA:`.
4. `TEARDOWN` chỉ được chạy `force-stop` và `HOME` SAU KHI đã hoàn tất bước 1 & 2.

---

## 2. Bài học về Worker Subagent cạn Turn Budget mà '0 files modified'

### Hiện tượng sai phạm
Subagent được giao task patch code và thêm test nhưng sử dụng hết 15 iterations (turn limit) chỉ để đọc file, audit, phân tích kiến trúc mà không kịp ghi file vào disk. Trả về báo cáo phân tích nhưng `0 files modified`.

### Chỉ đạo từ Claude Code CLI
Áp dụng **Budget-Aware Execution Discipline**:
- **Phase PLAN (≤ 20% budget / ≤ 3 calls)**: Chỉ đọc file cần thiết, xác định đúng anchor duy nhất. Nếu sau 3 calls thấy scope bất khả thi -> **ABORT NGAY** để báo Coordinator.
- **Phase EXECUTE (≥ 70% budget)**: Tập trung ghi file / patch / chạy test ngay lập tức. Mỗi call trong phase này phải sinh ra side-effect.
- **Phase VERIFY (≥ 1 call)**: Chạy pytest focused < 30s.
