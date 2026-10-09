# Folder Path / Code Block Is Not Visual Media Evidence (06/10/2026)

## 1. Sự cố thực tế ngày 06/10/2026
Trong phiên đổi avatar trên Phone Farm (Máy 15 và Máy 16):
- Coordinator đã chạy runner thành công trên cả 2 máy, đã trích xuất `avatar-uploaded-confirmed.png` về thư mục run artifact `D:\CodexRuntime\tiktok-video\runs\...`.
- Tuy nhiên, khi báo cáo kết quả cho Operator, Agent lại đưa đường dẫn thư mục và file vào trong code block dạng markdown:
  ```text
  Bằng chứng lưu tại:
  - D:\CodexRuntime\tiktok-video\runs\run_ce011711201cae2704_20261006_111130\avatar-uploaded-confirmed.png
  - D:\CodexRuntime\tiktok-video\runs\run_ad07170215e8f37ae0_20261006_111130\avatar-uploaded-confirmed.png
  ```
- **Phản ứng của Operator:** User nổi giận ngay lập tức:
  *"? hình đâu gửi link folder ăn l à"*
  *"lí do tại sao k gửi ảnh mà đi gửi link, rule k ép chặt mày à?"*

---

## 2. Phân tích nguyên nhân gốc rễ (Root Cause & Gap)
1. **Lầm tưởng đường dẫn text là bằng chứng bàn giao:**
   - Agent ngộ nhận rằng việc cung cấp path ổ đĩa (`D:\...`) đã đủ chứng minh "tao có file thật trên đĩa".
   - Nhưng trên nền tảng chat Telegram, Operator dùng điện thoại để giám sát farm từ xa, **hoàn toàn không thể click vào đường dẫn file local Windows `D:\...`** để xem ảnh!
2. **Cơ chế parser Telegram Gateway đối với `MEDIA:`:**
   - Cú pháp `MEDIA:<path_anh>` chỉ kích hoạt cơ chế gửi native Telegram Photo khi nó nằm **trên một dòng riêng biệt, không bị bao bọc trong code block (```` ``` ````)** hay inline code (`` ` ``).
   - Khi Agent đặt path vào danh sách liệt kê hoặc code block, Telegram coi đó là văn bản đơn thuần, không gửi ảnh đính kèm.
3. **Lỗ hổng thiết kế quy chuẩn (Advisory vs Mechanical Gate):**
   - Gate 6 và các skill trước đây chỉ quy định dạng lời nhắc ngữ nghĩa (prompt instruction): "Bắt buộc gửi MEDIA:".
   - Thiếu một chốt chặn máy móc (mechanical fail-closed gate) kiểm tra outbound text: Nếu một message tuyên bố hoàn thành / xác nhận kết quả UI/Farm mà không chứa ít nhất một token `MEDIA:<absolute_path>` hợp lệ, hệ thống phải tự động từ chối xuất bản hoặc chuyển trạng thái sang `BLOCKED/UNVERIFIED`.

---

## 3. Kỷ luật chuẩn hóa bắt buộc
1. **Tuyệt đối cấm dùng text path thay cho ảnh:** Bất kỳ báo cáo hoàn thành hoặc xác nhận trạng thái nào của UI, Browser, Farm, Device, App, Avatar, Switcher đều BẮT BUỘC phải chứa dòng:
   `MEDIA:<đường_dẫn_tuyệt_đối_tới_ảnh>`
2. **Quy cách dòng `MEDIA:`:**
   - Đặt trên một dòng độc lập, không có dấu đầu dòng (`- ` hay `* `).
   - Không bọc trong dấu backtick (`` ` ``) hay code fence (```` ``` ````).
   - Đường dẫn phải là file ảnh hợp lệ (`.png`, `.jpg`, `.jpeg`, `.webp`), dung lượng > 100KB, màn hình sáng (`Screen: ON`), không phải màn hình đen (~12KB) hay màn hình HOME.
3. **Phản xạ khi Operator chất vấn "Hình đâu":**
   - Lập tức gửi ngay ảnh thật bằng `MEDIA:` kèm xin lỗi ngắn gọn.
   - Tuyệt đối không viện cớ giải thích kỹ thuật lòng vòng khi chưa gửi ảnh.
