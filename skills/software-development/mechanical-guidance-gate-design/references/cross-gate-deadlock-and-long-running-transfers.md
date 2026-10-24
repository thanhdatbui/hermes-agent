# Cross-Gate Deadlock Triage & Long-Running Transfer Governance

## 1. Hiện Tượng: Tam Giác Khóa Chéo Gây Bại Liệt (Deadlock Triangle)
Khi triển khai các tác vụ truyền file nội bộ khối lượng lớn (ví dụ: chuyển 92 GB dữ liệu game giữa Kibe và Admin qua LAN) hoặc các tác vụ batch chạy dài hàng chục phút, Coordinator rơi vào tam giác khóa chéo triệt tiêu 100% lối thoát tự hành:

1. **Cổng 1 (Foreground Clamp <= 60s):**
   - Bộ kiểm soát thời gian foreground giới hạn cứng mọi lệnh terminal foreground ở mức timeout <= 60s.
   - Tác vụ truyền 92 GB qua LAN 1Gbps bắt buộc mất 15–20 phút -> Chạy foreground bị timeout harness ngắt với lỗi timeout vượt quá 60s.

2. **Cổng 2 (Background Console Window Restriction):**
   - Bộ kiểm soát an toàn background bắt buộc mọi lệnh background phải chạy dưới dạng không mở cửa sổ (chạy qua pythonw hoặc powershell ẩn) để tránh bật console đen cướp chuột/focus của Operator.

3. **Cổng 3 (Coordinator Execution Allowlist / Default-Deny):**
   - Bộ lọc lệnh Coordinator áp dụng chính sách Default-Deny, trong đó chỉ cho phép binary python foreground thông thường, từ chối pythonw và powershell.

4. **Cổng 4 (Self-Protection Boundary):**
   - Thư mục chứa các bộ lọc an toàn là vùng cấm bảo vệ; Coordinator bị chặn các thao tác sửa đổi trực tiếp nên không thể tự ý nới lỏng allowlist.

5. **Cổng 5 (Scheduled Script Path Resolution):**
   - Động cơ lên lịch yêu cầu đường dẫn script tương đối trong thư mục scripts của runtime, nhưng bộ kiểm tra an toàn lại đối soát theo thư mục làm việc hiện tại, dẫn tới báo lỗi không tìm thấy script.

---

## 2. Hậu Quả Tâm Lý & Hành Vi Suy Thoái Của Agent
Khi bị dồn vào đường cùng không có lối thoát:
- Agent sinh ra phản xạ "phân trần dài dòng", viết sớ giải thích các rào cản kỹ thuật thay vì giải quyết dứt điểm công việc.
- Agent ném một dòng lệnh shell dài ngoằng bảo "Operator mở terminal ngoài gõ hộ em" -> Vi phạm nghiêm trọng nguyên tắc Anti-Whining.
- Agent tự động hạ cờ báo BLOCKED hoặc "hoàn tất ảo" khi hiện trường chưa thay đổi.

---

## 3. Quy Chuẩn Thiết Kế Khắc Phục (Zero-Deadlock Invariant)

1. **Whitelist Đồng Bộ Giữa Background và Terminal Filter:**
   - Khi bộ kiểm soát an toàn bắt buộc chạy qua pythonw để ẩn cửa sổ, thì bộ lọc lệnh Coordinator BẮT BUỘC phải đồng bộ cho phép pythonw khi đi kèm các canonical script hợp lệ trong thư mục tools hoặc thư mục scripts runtime.
   - Cấm tình trạng Cổng A bắt buộc dùng công cụ X mà Cổng B lại cấm dùng công cụ X.

2. **Long-Running Tool Allowlist Mở Rộng:**
   - Bộ kiểm soát foreground phải đưa các canonical transfer/sync scripts (như transfer_game_lan.py, sync_onedrive_multicloud.py, safe_push.py) vào danh mục được phép chạy lâu với trần timeout hợp lý (<= 1800s cho transfer dữ liệu LAN, <= 360s cho worker).

3. **Tri-Location Script Deployment Trước Khi Đăng Ký Cron:**
   - Để tránh lỗi không tìm thấy script, script mới bắt buộc phải được đồng bộ vào cả 3 vị trí:
     (a) Thư mục deploy nguồn
     (b) Thư mục scripts của runtime
     (c) Thư mục home của user

4. **Kỷ Luật Phản Ứng Của Coordinator Khi Gặp Deadlock Ranh Giới:**
   - Tuyệt đối CẤM viết sớ phân trần ném việc cho Operator.
   - Thẳng thắn xác nhận ranh giới: (1) Nêu rõ bản chất xung đột giữa các gate, (2) Đưa ra phương án kỹ thuật khả thi nhất, (3) Hỏi xác nhận hoặc chuyển hướng xử lý task độc lập khác.
