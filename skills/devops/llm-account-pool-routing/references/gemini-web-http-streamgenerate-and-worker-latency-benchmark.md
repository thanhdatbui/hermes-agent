# Gemini Web HTTP StreamGenerate & Worker Execution Benchmark

## 1. Kiến trúc Gemini Web HTTP StreamGenerate (OmniRoute Native)
- **Bỏ Playwright:** Executor `gemini-web.ts` chuyển hoàn toàn sang HTTP POST trực tiếp vào `https://gemini.google.com/_/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate`.
- **Luồng xác thực 2 bước:**
  1. `GET https://gemini.google.com/app` với Cookie (`__Secure-1PSID`, `__Secure-1PSIDTS`): trích xuất token `SNlM0e` và `cfb2h` (build label) qua regex biên giới hạn.
  2. `POST BardFrontendService/StreamGenerate`: form payload `f.req=[null, JSON.stringify(innerArray)]` và `at=<SNlM0e>`.
- **Cấu trúc mảng 80-slot (Protobuf-like):**
  - Slot `[0]`: `[prompt, 0, null, null, null, null, 0]`
  - Slot `[1]`: `["en"]`
  - Slot `[17]`: `[[thinkMode]]` (Điều khiển mức độ suy luận)
    * `[[0]]`: Deep thinking (suy luận sâu nhất)
    * `[[2]]`: Medium / Standard thinking (cân bằng, khuyên dùng cho Worker)
    * `[[4]]`: Low thinking (suy luận tối thiểu)
    * `null`: Fast mode (tắt hẳn suy nghĩ)
  - Slot `[79]`: `modelCategory` (Enum phân loại model: Flash, Pro, Thinking).

## 2. Kỷ luật Reasoning Effort cho Worker: Tránh bẫy Over-Engineering
- **Rủi ro Deepest Thinking (`[[0]]`):**
  - Mô hình suy nghĩ quá sâu sẽ sinh ra khuynh hướng phức tạp hóa vấn đề, tự vẽ thêm Class, Pattern, thay đổi cấu trúc khi chỉ cần vá 1-2 dòng `if/else` $O(1)$.
  - Tăng thời gian phản hồi (TTFT) lên 8-12 giây.
- **Khuyến nghị cho Worker:** Mặc định nên chạy ở mức **`Medium / Standard`** để đảm bảo tốc độ phản hồi nhanh (~3-5s), giữ code ngắn gọn và tuân thủ tuyệt đối hợp đồng $O(1)$ của Farm.

## 3. Benchmark Thực Chiến: Native CLI (AGY CLI) vs Proxy Pool (OmniRoute)
So sánh đối đầu trực tiếp trên cùng model `Gemini 3.8 Flash Medium`:

| Tiêu chí | AGY CLI (Google Native Headless) | OmniRoute Pool (:20129) |
|---|---|---|
| **Độ trễ trung bình** | **3.2s – 5.2s** (Siêu tốc) | **13.5s – 23.8s** (Chậm hơn 4-5 lần) |
| **Kênh kết nối** | Trực tiếp gRPC/quic nội bộ | Client → Next.js Router → Proxy 4G Mobi → Upstream → Transform |
| **Chất lượng logic/code** | 9.5 – 9.8 / 10 | 9.0 – 9.5 / 10 |
| **Bảo vệ Edge-Case** | Tốt hơn (bắt tọa độ âm, format 4 khúc) | Súc tích, đôi khi tối giản quá mức |
| **Phân vai tối ưu** | **Worker thi công trực tiếp** (fix code, targeted test, debug cần nhanh) | **Batch processing & background jobs** (cày số lượng lớn, xoay tua nhiều accs, 0đ quota) |
