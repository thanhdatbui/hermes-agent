---
name: farm-niche-source-swap-and-purge-discipline
description: "Quy chuẩn tráo nguồn video ngách hot cho kênh flop, kỷ luật dọn sạch kho cũ (purge), và ma trận 6 bể nguồn từ dữ liệu thị trường."
---
# Farm Niche Source Swap & Old Video Purge Discipline

Quy chuẩn này được kích hoạt khi tài khoản trong farm bị flop (tăng trưởng chậm, dính ngách chết như review văn phòng phẩm / catalog tĩnh) cần đổi sang ngách viral để săn đề xuất.

## 1. Kỷ Luật Dọn Sạch Video Rác Cũ (Mandatory Old Video Purge)
- **Tín hiệu từ User:** *"R nạp niche ms thì phải dọn kho video cũ chứ", "mỗi lần t ép đổi niche mày vẫn tự dọn mà"*
- **Bẫy vận hành nguy hiểm:**
  - Khi một tài khoản bị flop do cào nhầm "ngách chết" (như review văn phòng phẩm / sổ tay Klong, catalog sản phẩm tĩnh), nếu Coordinator chỉ nạp video mới mà **không dọn sạch các video chưa đăng của ngách cũ**, rủi ro lớn sẽ xảy ra:
    1. *Ô nhiễm Persona:* Runner tự động tiếp tục quét và đăng nhầm các video cũ còn sót lại trong thư mục render.
    2. *Phình đĩa:* Hàng trăm thư mục ôm hàng chục nghìn file video rác không bao giờ dùng đến làm nghẽn ổ đĩa D.
- **Quy chuẩn tráo nguồn bất biến:**
  1. **Bảo lưu lịch sử đã đăng:** Giữ nguyên các video từ `1.mp4` đến `video_da_dang.mp4` trong `D:/TIKTOK-videonuoinick/<F_rend>/` để không làm loạn số đếm lịch sử và không bị đăng lặp.
  2. **Xóa sạch vĩnh viễn (Purge 100%):**
     * Xóa sạch toàn bộ video chưa đăng của ngách cũ từ `start_seq = (video_da_dang + 1)` trở đi trong thư mục render.
     * Xóa sạch toàn bộ video rác thừa trong thư mục gốc `D:/video goc/<F_raw>/` (chỉ giữ lại số lượng video khớp 1:1 với thư mục render).
     * Tuyệt đối không để thư mục backup tạm tồn tại sau khi hoán đổi hoàn tất.
  3. **Đánh số nối tiếp chính xác:** Toàn bộ video ngách hot mới nạp vào bắt buộc đánh số bắt đầu từ `start_seq`.

## 2. Kỷ Luật Đính Kèm Ảnh Proposal Canvas (Gate 6 Mandate)
- **Tín hiệu từ User:** *"Tại sao mày nói phương án xong mày đéo gửi hình? Lí do? Vi phạm gate?"*
- **Quy chuẩn:** CẤM TUYỆT ĐỐI xuất text mô tả các phương án Avatar (PA 1, 2, 3, 4) nếu chưa tạo và chưa gửi được bảng Proposal Canvas (`MEDIA:<path>`).
- Nếu việc tạo file canvas bị nghẽn (do guard/quota/tool): Phải báo cáo trung thực trạng thái bị nghẽn và đưa ra giải pháp mở khóa, tuyệt đối không xuất text mô tả chay tạo cảm giác hứa hẹn suông.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
