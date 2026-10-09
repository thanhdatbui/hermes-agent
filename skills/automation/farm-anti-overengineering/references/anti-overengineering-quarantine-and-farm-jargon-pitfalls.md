# Bẫy Over-Engineering: Phản Biện LLM, Tránh "Quarantine Bất Tử" & Định Nghĩa Chuẩn Thuật Ngữ Farm (25/09/2026)

## 1. Bối cảnh & Hiện tượng "Academic Over-Engineering" của LLM

Trong phiên tham vấn chiến lược ngày 25/09/2026 về tối ưu nhịp đăng video cho nick cắn đề xuất, cả **Claude CLI** và **Sol Auditor** đã rơi vào bẫy "vẽ hươu vẽ vượn" (Academic Over-Engineering) với các đề xuất lý thuyết suông:
- Đề xuất trạng thái `QUARANTINE bất tử`: Khi một video mới đăng bị 0-view hoặc view thấp thì lập tức dừng đăng toàn bộ nick và bắt User/Operator phải đi "kiểm tra tay" (`manual_release`).
- Đề xuất `Khóa 1 chiều khi farm có biến`: Đóng băng chuyển trạng thái toàn farm khi >30% máy có biến động metric.
- Hiểu nhầm nghiêm trọng thuật ngữ farm: Tưởng "Dưỡng sinh" là "cầm máy lướt feed", cho rằng bỏ dưỡng sinh là biến nick thành bot.

User đã lập tức chấn chỉnh thẳng thắn:
> *"Quarantine sửa lại đi, lâu lâu 0 view bth kệ cha nó ai rảnh loz đi kiểm tra tay... Dẹp quarantine bất tử đi. Khoá 1 chiều khi farm có biến là cc gì v... Dưỡng sinh có phải lướt feed đâu. Nó chính xác là thao tác tắt đăng video và follow trong ngày nuôi. Còn nick nào tới ngày nuôi đều lướt feed hết."*

---

## 2. Các Quy Tắc Thực Chiến Bất Biến (Anti-Overengineering Invariants)

### A. CẤM "Quarantine Bất Tử" & CẤM Bắt User "Kiểm Tra Tay"
- **Thực tế thuật toán:** Video mới đăng trên TikTok bị 0 view hoặc vài view trong 12–24h đầu là hiện tượng hoàn toàn bình thường do độ trễ index hệ thống hoặc thuật toán đang xếp hàng test pool.
- **Kỷ luật:** Tuyệt đối KHÔNG ĐƯỢC tự ý tạo các trạng thái cô lập (Quarantine) bắt dừng toàn bộ tiến trình đăng video rồi bắt con người kiểm tra thủ công. Nick flop hoặc 0 view cứ để chạy bình thường theo nhịp mặc định (có ngày dưỡng sinh 1/3), hệ thống tự vận hành 100%.

### B. Định Nghĩa Chuẩn Xác: "Dưỡng Sinh" (Organic Rest)
- **LƯỚT FEED LÀ BẮT BUỘC 100%:** Mọi nick khi đến ca/phiên nuôi **ĐỀU LƯỚT FEED 100%** để duy trì trust score thiết bị và IP proxy sạch. Lướt feed KHÔNG PHẢI là dưỡng sinh.
- **DƯỠNG SINH (ORGANIC REST 1/3):** Chính xác là thao tác **TẮT ĐĂNG VIDEO + TẮT FOLLOW** trong ngày nuôi đó:
  $$\text{Dưỡng sinh} = \text{Lướt feed} + (\mathbf{0\ Follow} + \mathbf{0\ Upload})$$
- **Ứng dụng vào nhịp đăng:**
  - **Nick Thường (`NORMAL`):** Giữ nguyên dưỡng sinh 1/3 $\to$ Nhịp đăng tự nhiên giãn ra **2.5 – 3 ngày / video** (tiết kiệm video cho nick flop).
  - **Nick Đang Cắn Đề Xuất (`BOOST`):** Vẫn lướt feed 100%, nhưng **gỡ cấm upload của ngày dưỡng sinh** $\to$ Đăng đều đặn **nhịp 48h / video (2 ngày 1 lần)** để đón trọn sóng phân phối.
  - Tuyệt đối CẤM tăng lên 1 video/ngày vì gây ra hiện tượng tự triệt tiêu view (Cannibalization) và kích hoạt bot-pattern.

### C. Đọc Config Thật Thay Vì Tin Comment/Docstring Cũ
- Khi tranh luận về budget follow của nick trưởng thành, các mô hình trích dẫn "6–10 follow/phiên" từ docstring cũ trong code.
- **Thực tế:** Toàn bộ config máy thật (`config/machine*.yaml`) đã cài đặt:
  ```yaml
  budget_per_session_min: 10
  budget_per_session_max: 20
  budget_per_session: 20
  ```
- **Kỷ luật:** Mọi thiết kế phải soi vào **config YAML thật sự đang chạy**, cấm suy diễn từ docstring lỗi thời.

### D. Giải Pháp Tối Giản Cho Bẫy Flapping "Hôm Nay Cắn Mai Mất"
- Dashboard chỉ là **Sensor** đo delta 24h, không được dùng làm công tắc đổi lịch trực tiếp.
- Thay vì xây dựng hệ thống phân tích ML phức tạp, giải pháp chuẩn Phone Farm là:
  - Khi nick có đà tăng trưởng tốt (tính theo rolling window 3 ngày) $\to$ Gắn cờ `BOOST` **khóa giữ 5 ngày**.
  - Trong 5 ngày này: gỡ cấm upload, chạy nhịp 48h (đủ để đăng trọn vẹn 2–3 video).
  - Sau 5 ngày nếu hết đà mới tự động hạ về thường. Cực kỳ êm, không giật cục, không over-engineering.
