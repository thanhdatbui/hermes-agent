# Inbound Vision Fallback Trap & Telegram Banner Viewport SOP

Tài liệu đúc kết sự cố Inbound Vision Fallback ném lỗi `aux_accounting`, bẫy tỷ lệ ảnh ngang trên Telegram Mobile và phương pháp trích xuất avatar thú cưng chuyên nghiệp từ kho video farm.

---

### 1. Sự Cố `aux_accounting` & Fallback Ngầm Tại Gateway

#### Hiện tượng
Khi người dùng gửi ảnh chụp màn hình vào Telegram, Gateway Hermes tự động inject đoạn text lỗi:
```text
[The user attached an image. Here's what it contains:
There was a problem with the request and the image could not be analyzed. Error: No module named 'agent.aux_accounting']
```

#### Nguyên nhân kỹ thuật
1. Tại `gateway/run.py` dòng 10586: Khi Gateway xác định model không nạp được native pixels qua proxy hiện tại (`_img_mode != 'native'`), nó tự động fallback sang `_enrich_message_with_vision` (chạy tool `vision_analyze` up-front).
2. Trong `vision_tools.py`: Tool này cố import module kế toán chi phí `agent.aux_accounting` (module đã bị xóa/đổi tên trong bản build mới).
3. Khi import thất bại, tool văng Exception: `No module named 'agent.aux_accounting'`. Gateway bắt lỗi và nhét nguyên đoạn text lỗi vào prompt của LLM.
4. LLM bị mù ảnh hoàn toàn, không có pixel trong ngữ cảnh và bắt đầu suy đoán mò/ảo giác.

#### Quy tắc xử lý
* Khi nhận tin nhắn có chứa marker lỗi `aux_accounting`, Agent **TUYỆT ĐỐI KHÔNG TIN VÀO TEXT ĐÓ**.
* BẮT BUỘC gọi `copy_user_img.py` kéo ảnh về thư mục reports và dùng `browser_vision` mở ra soi mắt thật trước khi suy luận hay trả lời.

---

### 2. Cạm Bẫy Banner Ngang (Ultra-wide Ratio) Trên Telegram Mobile

#### Hiện tượng
Khi tạo Proposal Canvas chứa 4 ảnh nằm ngang (ví dụ: `1760x600px` - tỷ lệ ~3:1), trên giao diện Telegram Mobile của người dùng chỉ hiển thị một **khối hình chữ nhật đen xì (black box)** thay vì bức ảnh hoàn chỉnh.

#### Nguyên nhân
Telegram Mobile client không thể render thumbnail tử tế cho các bức ảnh có tỷ lệ khung hình quá dài ngang (> 2.5:1) khi gửi qua Bot API với thẻ `MEDIA:`. 

#### Quy tắc định dạng Canvas Proposal
* **CẤM TUYỆT ĐỐI** tạo canvas dạng banner dài ngang (> 2:1).
* **BẮT BUỘC** sử dụng bố cục lưới vuông hoặc dọc tiêu chuẩn:
  * Lưới 2x2: `1060x1200px` hoặc `1200x1200px`.
  * Khung thẻ dọc: Mỗi ô tròn đường kính 400–450px nằm gọn trong card 500px.
  * Tỷ lệ khung hình an toàn cho Telegram Mobile: `1:1` đến `4:5`.

---

### 3. Cạm Bẫy Crop Zoom Kỹ Thuật Số (Micro-Crop Upscaling)

#### Hiện tượng
Ảnh avatar gửi cho người dùng bị vỡ hạt, mờ căm (low-res blur), chỉ thấy một cục lông bầy hầy không rõ mắt mũi.

#### Nguyên nhân
Ảnh gốc trong video hoặc thư mục chỉ có độ phân giải 512x512. Thuật toán crop mù quáng cắt một vùng nhỏ 180x180px ở góc rồi dùng phép nội suy phóng to ngược lên 512x512px, làm vỡ nát pixel.

#### Tiêu chuẩn kỹ thuật khi tạo Avatar Thú Cưng
1. **Sử dụng ảnh Studio có sẵn trong Farm:**
   * Trong kho `D:/video goc`, các folder chuyên đề thú cưng (`334, 353, 385, 399`) đã có sẵn file `avatar.jpg` chuẩn HD 512x512 chụp cận cảnh sắc nét từ studio.
   * Ưu tiên sử dụng trực tiếp các avatar này thay vì cố cắt từ video rung lắc thiếu sáng.
2. **Quy tắc trích xuất từ Video:**
   * Chỉ lấy khung hình từ video chất lượng cao (1080p).
   * Box crop bắt buộc tối thiểu $\ge 600 \times 600\text{px}$ trên frame gốc, sau đó downscale về 512x512 bằng `cv2.INTER_AREA`.
   * CẤM phóng đại kỹ thuật số (upscale) bất kỳ vùng crop nào nhỏ hơn 400x400px.
