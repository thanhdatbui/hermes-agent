# Case UI-80: Bẫy Over-Engineering Fail-Closed Trên Dữ Liệu Ngoại Lai (External Noise) & Bài Học "Kệ Mẹ Nick Ngoài"

## 1. Bản chất sự cố (01/10/2026)
- **Triệu chứng:** Toàn bộ 80 máy chạy Ca 1 nuôi acc bị gãy Module 2 (Follow qua Anchor), chỉ đúng 1 lượt chạy được (M48), 52 lượt còn lại bị failover sang Mode 1.
- **Log lỗi:** `mode2_degraded_reasons: ["MANUAL_REVIEW: follower row không có nút follow semantic"]`.
- **Cơ chế dẫn tới lỗi:** Farm vừa bật **Following tự nhiên (Organic Follow)** khi lướt feed (tab Đề xuất, Bạn bè) để làm loãng đồ thị follow chéo. Do đó danh sách *Đang follow* của nick mồi (Tik1/Tik2) có rất nhiều nick người ngoài (idol, gái xinh, shop, bạn bè...).
- **Cái bẫy code cũ:** Hàm kiểm tra `missing_button_rows` quét từng hàng trên màn hình. Nếu có dù chỉ 1 hàng thiếu nút Follow (do nick ngoài hiển thị nút Nhắn tin, 3-chấm, Bạn bè khác ID, hoặc bị cắt viền), code liền coi là giao diện TikTok bị lỗi và dập cầu dao `MANUAL_REVIEW`, dừng toàn bộ phiên Mode 2 của máy.

---

## 2. Giải phẫu tâm lý sai lầm của AI (DeepSeek & Gemini)

### A. DeepSeek (13/08/2026, Commit `ca1a152`): Bảo hoàng hơn vua, Fail-closed cực đoan
- **Sai lầm:** Khi viết hàm quét danh sách, DeepSeek áp dụng triết lý "thấy bất thường là dừng ngay lập tức" (fail-closed) một cách máy móc lên **toàn bộ màn hình**, không phân biệt giữa dữ liệu mục tiêu (nick farm cần follow) và dữ liệu nhiễu (nick người ngoài).
- Khi hệ thống chuyển sang Mode 2' (chỉ follow nick farm `internal_uids`), DeepSeek/Opus chỉ lọc `internal_uids` lúc bấm nút, nhưng **bỏ quên đoạn kiểm tra lỗi `missing_button_rows`**, để lại một quả bom nổ chậm.

### B. Gemini (05/09/2026, Commit `0235c86` - Case UI-51): Over-Engineering chắp vá triệu chứng
- **Sai lầm kinh điển:** Khi Máy 36 bị kẹt bởi nick ngoài `knorrvietnam` cắt viền màn hình thiếu nút, Gemini nhận task sửa nhưng **hoàn toàn không đặt câu hỏi về bản chất**: *"Tại sao mình chỉ đi follow nick của farm mà lại phải quan tâm nick người ngoài có nút hay không?"*.
- Thay vào đó, Gemini đẻ thêm:
  - Hàm tính toán tọa độ cắt viền trên `top_cutoff_y`.
  - Hàm tính toán tọa độ cắt viền dưới `bottom_cutoff_y`.
  - Bộ nhớ đệm `session_external_seen` trong phiên.
  - Hơn 300 dòng unit test và tài liệu Case UI-51 để bao biện cho sự tồn tại của `missing_button_rows`.
- **Hậu quả:** Khi danh sách người ngoài trở nên phong phú (nút tin nhắn, nút 3-chấm, layout mới...), toàn bộ các hàm chắp vá của Gemini vô hiệu, quả bom nổ tung 100% trên cả dàn 80 máy.

---

## 3. Nguyên tắc Anti-Overengineering Cốt Lõi (User Directive 01/10/2026)

> *"Đã có following tự nhiên thì quét trúng nick không phải của farm thì kệ con mẹ nó tự kéo xuống nick tiếp theo, code óc lồn nào sửa cơ chế óc chó v, trc đây làm đéo gì bị"*

1. **Khắc cốt ghi tâm quy tắc phân định Scope (Target vs Noise):**
   - Mọi cơ chế kiểm tra an toàn (Validation / Fail-Closed) **CHỈ ĐƯỢC PHÉP ÁP DỤNG TRÊN DỮ LIỆU MỤC TIÊU (`Target Domain / internal_uids`)**.
   - Dữ liệu ngoại lai (External noise / Stranger accounts / Ads / Third-party items) phải được coi là **vô hại và cho qua 100%**. Tuyệt đối không bao giờ được để dữ liệu ngoại lai kích hoạt cờ lỗi hệ thống (`MANUAL_REVIEW`, `FATAL`, `ABORT`).
2. **Kéo xuống thay vì dừng lại (Scroll Past Noise):**
   - Khi quét một danh sách hỗn hợp: nếu trên màn hình chỉ toàn dữ liệu ngoại lai, hành vi đúng của người thật là **tiếp tục cuộn xuống (Scroll Down)** để tìm dữ liệu mục tiêu ở các trang tiếp theo.
   - Chỉ dừng lại khi đã cuộn hết danh sách (End of list / Idle scrolls threshold) hoặc đạt giới hạn an toàn, và kết thúc phiên ở trạng thái `OK / Exhausted`, không được tự bịa ra lỗi `MANUAL_REVIEW`.
3. **Cấm viết code chắp vá để bảo vệ một logic sai từ gốc:**
   - Khi gặp một lỗi lạ, câu hỏi đầu tiên phải là: *"Đoạn code gây lỗi này có thực sự phục vụ mục tiêu nghiệp vụ không?"*.
   - Nếu logic đó vốn dĩ không thuộc nghiệp vụ (như việc đi kiểm tra nút của nick người ngoài), **XÓA BỎ HOẶC THU HẸP PHẠM VI NGAY TẠI GỐC**, cấm đẻ thêm các hàm wrapper, detector viền, hay cache ngoại lệ xung quanh nó.
