# Quy chuẩn định dạng báo cáo Watchdog & Cronjob Farm (User chốt 2026-10-02)

## 1. Tối giản tối đa & Chống thuật ngữ gây lú lẫn
- **Bối cảnh**: User phản ánh gay gắt về thuật ngữ *"Lũy kế hôm nay"* và việc báo cáo song song hai dòng:
  ```text
  • Đã dọn đợt này: 125 máy
  • Lũy kế hôm nay: 125 máy
  ```
  hoặc khi chạy lại đợt retry:
  ```text
  • Đã dọn đợt này: 0 máy
  • Lũy kế hôm nay: 74 máy
  ```
  gây hiểu lầm, rườm rà và khó chịu.
- **Quy tắc bắt buộc**:
  * CẤM dùng các thuật ngữ hành chính/kế toán như *"Lũy kế"*, *"Đợt này/Lần này"* trong báo cáo tổng kết thường nhật.
  * Chỉ dùng các nhãn mộc mạc, rõ ràng:
    - **• Đã hoàn tất**: `<N> máy`
    - **• Lỗi (<M>)**: `<danh_sách_máy_lỗi>` (thay vì dùng tiếng Anh `Fail`)
  * Tinh thần xuyên suốt: **"Ghi đơn giản v thôi"** — chỉ cần biết tổng số máy đã xong và danh sách máy lỗi kèm nguyên nhân ngắn gọn.

## 2. Reviewer Rubric cho các bản vá Watchdog / Cron Launcher
- Khi sửa đổi script cron chạy dưới `pythonw.exe` trên Windows:
  * Việc chuyển đổi `sys.executable` sang `CHILD_PYTHON` (chọn `python.exe` để tránh hiện cửa sổ console adb) bắt buộc phải có unit test mô phỏng `sys.executable` dạng `pythonw.exe`.
  * Bắt buộc có structured telemetry ghi nhận vào `sys.stderr` (ví dụ: `[TELEMETRY] launcher=... is_pythonw=...`) để đáp ứng rubric Observability & Telemetry của Sol Reviewer (>= 85/100).
  * Tránh gộp các file uncommitted ngoài phạm vi deliverable vào candidate commit của Closeout Gate.
