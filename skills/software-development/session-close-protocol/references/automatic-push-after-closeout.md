# Quy Định Tự Động Push Khi Chốt Phiên (Automatic Push Policy)

*Cập nhật: 2026-10 (Chỉ thị trực tiếp từ Sếp Kibe)*

## 1. Nguyên Tắc Cốt Lõi (Zero Manual Push Friction)
- Trước đây: Quy trình cũ yêu cầu Coordinator dừng lại sau khi commit, gửi báo cáo và chờ User gõ lệnh xác nhận ("chốt", "ok") mới được phép push lên remote.
- **Quy định mới (BẮT BUỘC):** Khi User phát lệnh kết thúc phiên ("chốt", "chốt phiên", "done", "wrap up"):
  1. Chạy thẩm định độc lập: `python D:/Taadaa/tools/closeout_gate.py --repo <đường_dẫn_repo> --json-output`.
  2. Nếu **REJECTED** (< 85đ): Bắt buộc dispatch worker sửa theo feedback (hoặc Coordinator dùng L2 Surgery nếu đủ điều kiện).
  3. Nếu **APPROVED** (Overall Score >= 85/100):
     - Coordinator tạo commit hợp lệ: `git commit -m "..."`.
     - **TỰ ĐỘNG CHẠY `git push origin <branch>` LÊN REMOTE NGAY LẬP TỨC**.
     - **CẤM TUYỆT ĐỐI** dừng lại bắt User kiểm tra thủ công hoặc xin phép lệnh push riêng.

## 2. Đồng Bộ Hóa Guard Hệ Thống
- File chính sách `farm_policy.py` và plugin `farm-coordinator-guard` được cấu hình để:
  - Khi `closeout_gate.py` trả về `APPROVED >= 85`, cờ `closeout_passed` được bật `True`.
  - Cờ này được giữ nguyên qua bước `git commit` để mở khóa cho lệnh `git push`.
  - Sau khi `git push` thực thi thành công lên remote, cờ `closeout_passed` mới tự động reset về `False` để bảo vệ phiên tiếp theo.

## 3. Cấu Trúc Báo Cáo Nghiệm Thu Cuối Cùng
Gửi đúng 1 tin nhắn tổng kết rõ ràng:
- **Verdict & Điểm số:** `APPROVED (Score: X/100)`
- **Commit SHA & Push:** `[SHA] đã được tự động push lên remote thành công`.
- **Bằng chứng kiểm thử:** Số lượng test passed và Canary screenshot (nếu can thiệp thiết bị farm).
