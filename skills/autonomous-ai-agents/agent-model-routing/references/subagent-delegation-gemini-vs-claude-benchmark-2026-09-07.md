# Subagent Delegation Benchmark: ag-gemini-pool-3 (High vs Medium) vs ag-claude (07/09/2026)

## 1. Kết quả thực nghiệm đo lường qua 2 bài toán Phone Farm (Bugfix & Concurrency Lock)
1. **Gemini High (`ag-gemini-pool-3`, reasoning: `high`):**
   - Vòng 1 (ADB retry bug): 53.58s, 9 calls, test pass 4/4.
   - Vòng 2 (Device lock lease renewal): 89.04s, 14 calls, test pass 5/5.
   - Nhược điểm: Bị tật over-probing và overthinking (tìm file đặc tả không tồn tại, chạy các lệnh probe `stat`/`disasm`), tốn nhiều turns hơn.

2. **Gemini Medium (`ag-gemini-pool-3`, reasoning: `medium`):**
   - Vòng 1 (ADB retry bug): 49.22s, 7 calls, test pass 4/4 -> Thắng vòng 1 (96đ) nhờ defensive edge case handling.
   - Vòng 2 (Device lock lease renewal): 94.76s, 14 calls, test pass 5/5.
   - Ưu điểm: Cắt 50% thời gian tạo thinking token, giảm nghẽn pool 18 accounts trên OmniRoute (:20129). Khuyến nghị dùng làm default cho worker coding nếu user chọn Gemini.

3. **Claude (`ag-claude`):**
   - Vòng 1 (ADB retry bug): 54.88s, 5 calls, test pass 4/4 -> 95đ.
   - Vòng 2 (Device lock lease renewal): 50.30s, 4 calls, test pass 5/5 -> Thắng áp đảo vòng 2 (98đ).
   - Ưu điểm vượt trội: "1-Shot Fix", gom đọc concurrent 2 file ở turn 1, sửa thẳng vào diff, không lượn tìm file, tốn ít API calls nhất (4-5 calls).

## 2. Kỷ luật đường dẫn bắt buộc khi dispatch subagent
- Khi prompt dùng đường dẫn tương đối (vd: "trong thư mục hiện tại"), do session Hermes có CWD mặc định là `C:\Users\Kibe`, Gemini sẽ quét khắp ổ đĩa (`C:/Users/Kibe`, `D:/Taadaa`, session search) dẫn đến cạn sạch budget 15 turns mà không làm được việc.
- BẮT BUỘC cung cấp **đường dẫn tuyệt đối** trong prompt:
  + `File mã nguồn cần sửa: <absolute_path>`
  + `File test kiểm tra: <absolute_path>`
