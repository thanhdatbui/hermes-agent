# Template — prompt nghiên cứu hành vi TikTok cho Gemini (2026-08-16)

Khi user hỏi "tỉ lệ nào hợp lí / bao nhiêu là bất thường / có nên tăng X" mà chưa có
số liệu thật, ĐỪNG tự suy đoán hay bịa "nghiên cứu". Soạn prompt nghiên cứu cho
Gemini theo cấu trúc này (bản đầy đủ đã gửi user 2026-08-16, lưu tại
`C:\Users\Kibe\AppData\Local\hermes\cache\terminal\gemini-tiktok-behavior-research-prompt.txt`).

## Cấu trúc prompt (4 phần bắt buộc)

1. **Bối cảnh** — farm 480 acc, mỗi IP 6 acc, mỗi acc cần 1k follower mở giỏ hàng;
   mô phỏng hành vi người dùng thật để tránh detect, mục tiêu ~60-70 ngày.
2. **Thiết kế hiện tại (cần đánh giá)** — viết CHÍNH XÁC từ code:
   - Số ca/ngày, mỗi ca = mấy acc, mỗi acc mấy phiên (⚠️ 3 ca = 3 acc KHÁC NHAU,
     mỗi acc 2-3 phiên — đừng ghi "6 phiên/acc")
   - Video/phiên (15-30), watch 2-8s, like %, follow organic %
   - Follow chéo/phiên + budget/ngày
   - Tab distribution (Đề xuất 98% / Đã follow 2% / Bạn bè 0%)
   - **Nếu đang cân nhắc thay đổi (VD nâng 2→3 phiên) thì ghi rõ "ĐANG CÂN NHẮC"**
3. **Số liệu đo thật từ log** — ví dụ: "16-17 video ≈ 11 phút (dừng sớm vì lỗi)",
   "30 video ước tính 15-20 phút". Luôn đo từ log thật, không ước lượng.
4. **Câu hỏi 2 phần**:
   - Phần A: số liệu hành vi TikTok thật có nguồn (sessions/ngày, duration/phiên,
     thời gian/ngày, video/phiên, follow/ngày, phân bố giờ peak)
   - Phần B: đánh giá thiết kế dựa trên Phần A (từng hạng mục: phiên, video, follow,
     organic %, cụm giờ cố định, tăng phiên vs tăng budget)
   - **Nêu rõ trần tự đặt**: "budget_per_day: 30 là do tôi TỰ ĐẶT, không có số liệu
     chứng minh — hãy cho số liệu thật follow/ngày + trần an toàn"
5. **Yêu cầu output**: chỉ số liệu thật có nguồn (URL/nghiên cứu/năm); nếu không có
   dữ liệu → nói "không có dữ liệu công khai" đừng bịa; kết luận ngắn gọn từng câu;
   cuối khuyến nghị tổng thể (giữ/đổi gì dựa trên dữ liệu nào).

## Pitfalls
- Google search chặn captcha khi browse từ host này (trang `sorry/index`) — Bing
  cũng trả rác cho query nghiên cứu; đừng mất thời gian tự search, đưa prompt cho
  user dán Gemini.
- User sẽ dán prompt lên Gemini và gửi kết quả về — giữ prompt tự chứa (self-contained),
  không cần context ngoài.
- Sau khi user sửa thiết kế (VD 3 ca = 3 acc), CẬP NHẬT prompt cho khớp — đừng gửi
  prompt cũ với số liệu sai (đã xảy ra 2026-08-16: "6 phiên/acc" sai → user hỏi lại).
