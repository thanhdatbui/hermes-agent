# Quy Chuẩn Canary Full Flow, Fleet Error Budget & Kỷ Luật "Build Trên Cái Đã Có"

Đúc kết bài học vận hành thực tế ngày 07/09/2026 trên hệ thống Taadaa Phone Farm:

---

## 1. Bãi Bỏ Định Kiến "Canary Chỉ Là Swipe Feed"
- **Sai lầm cũ:** Bất kể sửa lỗi ở flow nào (Reg tài khoản mới qua Hotmail/Outlook, Upload video, 2FA, Login), Coordinator/Worker sau khi sửa code chỉ chạy script feed lướt 2-4 video ngẫu nhiên rồi vội vàng kết luận "Canary Pass".
- **Hậu quả:** Script nghiệp vụ chính (Reg/Upload) vẫn có thể gãy ngay ở bước tiếp theo do code mới chưa hề được thử lửa trên luồng thực tế.
- **Quy Chuẩn Canary MỚI (Bắt buộc hoàn thành 100% Flow Lỗi):**
  - Bug ở flow nào $\rightarrow$ Canary **BẮT BUỘC** chạy lại đúng script của flow đó:
    + Flow Reg $\rightarrow$ Chạy tạo trọn vẹn 1 tài khoản mới từ A đến Z.
    + Flow Upload $\rightarrow$ Chạy đăng 1 video hoàn chỉnh cho đến khi publish thành công.
    + Flow Login / 2FA $\rightarrow$ Chạy đăng nhập và xác thực 2FA trơn tru.
  - **CẤM TUYỆT ĐỐI:** Chỉ swipe feed cho có lệ.

---

## 2. Kỷ Luật "Build Dựa Trên Những Cái Đã Có Rồi Cải Tiến Lại"
- **Anti-Pattern:** Khi nhận bài toán gom lỗi batch hay cải tiến hệ thống, Agent có xu hướng tự viết ra một bộ script/tool mới toanh nằm cô lập ở một thư mục phụ, tạo ra một workflow song song khiến codebase bị phân mảnh.
- **Quy tắc thực thi:**
  - Khảo sát O(1) các artifacts hiện có:
    + `run_tiktok_upload_batch.ps1` đã có file `summary.csv` xuất ra sau mỗi batch.
    + `run-feed-session.ps1` đã có `run_manifest.json` và `summary.txt`.
    + `automation_core` đã có module `alerts.py`.
  - Cải tiến trực tiếp: Viết bộ parser đọc đúng các file schema có sẵn (`summary.csv`, `run_manifest.json`), tích hợp thẳng với module gửi Telegram có sẵn (`automation_core.alerts`), và chỉ cần gắn đúng 1 dòng hook vào cuối batch runner.

---

## 3. Kỷ Luật Điều Phối Tự Động Hóa Đến Cùng (Continuous Autonomous Execution)
- Khi user đã phê duyệt và chỉ đạo (*"Làm xong hết luôn r báo đừng dừng lại báo từng phase nữa"*):
  - Coordinator phải giữ luồng thực thi liên tục qua các phase mà không ngắt quãng:
    1. Code Phase 1 (Device lock release-on-fail) $\rightarrow$ Test.
    2. Review Claude CLI Opus High $\rightarrow$ Sửa theo checklist đến APPROVED.
    3. Code Phase 2 (Batch aggregator & Ngưỡng kép) $\rightarrow$ Test.
    4. Review Claude CLI Opus High $\rightarrow$ APPROVED.
    5. Tích hợp hook vào runner batch $\rightarrow$ Nghiệm thu toàn diện.
  - Tuyệt đối không dừng lại giữa chừng ở từng phase con để xin phép hay báo cáo lặt vặt.
