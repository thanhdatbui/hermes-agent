# Case Study: Cộng Đồng Antigravity & Toolchain Dựng Video Bằng Agent

## 1. Nguồn Dữ Liệu Thực Tế
Tổng hợp từ thảo luận cộng đồng Antigravity VN (chủ đề: *"Antigravity có tự edit video như Claude không"*):

### Các giải pháp được chia sẻ từ cộng đồng:
1. **Plugin Qwen MMM (Qwen-VL) soi timeline:**
   - Người dùng clone repo/plugin Qwen Multimodal về môi trường local.
   - Cho agent soi chi tiết từng frame video mẫu để trích xuất phong cách dựng, vị trí subtitle và nhịp cắt trước khi yêu cầu agent dựng lại.
2. **Khai thác FFmpeg & Remotion làm engine cốt lõi:**
   - Thay vì để Agent tự mò cách render, người dùng cung cấp repo mã nguồn mẫu của FFmpeg wrapper hoặc Remotion.
   - Agent nhận video mẫu + audio voiceover, sinh kịch bản React/Remotion hoặc lệnh FFmpeg ghép nối.
3. **Kinh nghiệm dựng Talking Head:**
   - Dùng Gemini/Argon (1M context) hoặc Claude để sinh kịch bản talking head.
   - Nhược điểm phản ánh từ cộng đồng: Render talking head trực tiếp thường bị chậm (lâu gấp 3 lần so với các workflow API chuyên biệt) và chất lượng có thể bị lệch nếu không có template căn chỉnh tọa độ mặt (face bounding box).

## 2. Kiến Trúc Khuyến Nghị Cho Taadaa Video Farm
- **Pha 1 (Bóc tách):** Tận dụng Gemini Native Multimodal / Qwen-VL phân tích cấu trúc kịch bản và nhịp cắt của kênh đối thủ.
- **Pha 2 (Kịch bản):** Agent sinh file cấu hình JSON miêu tả từng phân cảnh (Scene 1: 0-3s, text, image asset, zoom effect; Scene 2: 3-8s...).
- **Pha 3 (Thực thi nền):** Chuyển giao file JSON cho script Remotion/FFmpeg dựng offline trên máy chủ/farm có GPU NVIDIA NVENC để đạt tốc độ render tối đa.
- **Pha 4 (Kiểm định):** WinRT OCR và Multimodal tự động duyệt frame đầu ra để phát hiện lỗi lẹm chữ hoặc lệch bố cục trước khi đẩy vào kho video của farm.
