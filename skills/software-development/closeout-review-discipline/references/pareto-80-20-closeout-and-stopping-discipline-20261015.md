# Kỷ luật Đóng phiên & Báo cáo theo Nguyên tắc 80/20 (Taadaa Phone Farm)

> Ngày ghi nhận: 15/10/2026  
> Chỉ thị Operator: "Trả lời theo 80/20 đi. Từ h t muốn mọi công việc đều xử lý theo nguyên tắc 80/20."  
> Ngữ cảnh: Phiên sửa lỗi Cron Watchdog (`feed_session_watchdog.py`), đối soát Invariant Rules `Tik4.xlsx` và vòng thẩm định Closeout Gate.

---

## 1. Bản chất Nguyên tắc 80/20 trong Vận hành Phone Farm

Trong hệ thống tự động hóa phân tán (80+ máy thật, hàng chục tiến trình cron ngầm):
- **20% cốt lõi mang lại 80% giá trị**:
  1. Liveness & cron status xanh sạch (`last_status: ok`).
  2. Báo cáo ca đối soát chính xác số liệu thật (Khớp lượt feed, follow hook, upload hook).
  3. Tính toàn vẹn Invariant Rules của dữ liệu Excel (không sai công thức Folder Video, không trùng lặp slot/máy).
  4. Giải phóng sạch sẽ device locks sau khi hoàn thành.
- **80% lãng phí / Bẫy Over-engineering cần triệt tiêu**:
  1. Tiếp tục chẻ nhỏ module (modularize) khi code đã chạy ổn định và đạt chuẩn architecture gate.
  2. Tối ưu hóa vi mô (micro-optimizations, formatting, docstring styling) không mang lại tính năng mới hay tăng độ ổn định thực tế.
  3. Tường thuật dài dòng quá trình debug nội bộ thay vì đi thẳng vào kết quả.

---

## 2. Kỷ luật Điều phối & Dừng công việc (Stop Gate 80/20)

1. **Biết điểm dừng khi đã đạt mục tiêu cốt lõi (Stop Condition)**:
   - Khi một sự cố được khắc phục (ví dụ: vá xong `ImportError` runtime khiến cron watchdog crash, sửa ô sai công thức trong `Tik4.xlsx` khiến validator fail), toàn bộ test suite pass và cron job đã chạy test thành công:
   - **BẮT BUỘC DỪNG LẠI NGAY.** Cấm tự ý đề xuất refactor thêm các phần code không bị lỗi.
   - Khi Operator hỏi "Xong hết chưa còn gì nữa không": Đối soát nhanh liveness của 4 trụ cột (Cron jobs, Excel Invariants, Device Locks, Test Suites). Nếu toàn bộ xanh -> Báo "Hết, toàn bộ hệ thống đã sạch 100%", tuyệt đối không bới lông tìm vết để kéo dài phiên.

2. **Tập trung vào 1 đòn bẩy duy nhất (Highest-Leverage Bottleneck)**:
   - Nếu phát hiện nhiều cảnh báo, luôn chọn xử lý **1 điểm nghẽn duy nhất** có sức ảnh hưởng toàn diện (ví dụ: sửa đúng 1 ô Folder Video bị gõ sai trong `Tik4.xlsx` để giải phóng toàn bộ cron sync tự động `taikhoan-run-safe-sync`).
   - Không dàn trải thời gian vào các chỉnh sửa hình thức (whitespace, docstrings, variable renaming) khi điểm nghẽn cốt lõi chưa thông.

---

## 3. Kỷ luật Giao tiếp & Báo cáo Telegram 80/20

1. **Format báo cáo 3 khối cực ngắn**:
   - **Trạng thái cốt lõi (Bottom Line)**: Xong hay Chưa xong (Trạng thái Xanh/Đỏ).
   - **Bằng chứng thực tế (Hard Evidence)**: Số liệu kiểm chứng cụ thể (ví dụ: PASS 100%, 0 lỗi, exit code 0).
   - **Hành động tiếp theo (Next Action)**: Nếu đã xong thì dừng; nếu còn nghẽn thì nêu đúng 1 điểm nghẽn và giải pháp trong 1 câu.
2. **Cấm tuyệt đối**:
   - Cấm tường thuật dòng suy nghĩ, lẩm bẩm debug ra chat.
   - Cấm văng nguyên khối log/traceback dài vào Telegram (chỉ trích xuất đúng 1-2 dòng lỗi then chốt).
