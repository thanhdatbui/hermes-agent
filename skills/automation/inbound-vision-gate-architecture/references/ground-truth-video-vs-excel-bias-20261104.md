# Kỷ Luật Video Thật Thắng Mọi Nhãn Excel & Quy Trình Đính Chính Niche

## 1. Bài Học Xương Máu Về Niche Drift (Sự Cố Kênh @vyvy14190)
- **Hiện tượng:** Cột `Keyword Video` trong `Tik5.xlsx` ghi nhầm là `Thú Cưng / Chó Cưng`, gán hashtag `#chocung #thucung`. Coordinator tin tưởng tuyệt đối vào nhãn Excel này mà không soi video gốc, dẫn đến việc cắt trúng mặt diễn viên nam quát tháo trong quán ăn (`18.mp4` kho `394`) nhưng mồm vẫn bốc phét là "chú cún lông nâu nằm giữa tâm".
- **Sự thật:** Toàn bộ 52 video của kho `D:/video goc/394` là ngách **Phim ngắn / Drama đời sống** (quán ăn, đòi nợ, cãi vã đường phố), hoàn toàn không có bất kỳ con chó hay cún nào.

## 2. Invariant Bắt Buộc Khi Chuẩn Hóa Kênh
1. **Video Thật Là Chân Lý Tối Cao (Ground Truth First):**
   - Trước khi đề xuất Avatar, Bio, hay Hashtag, BẮT BUỘC dùng `vision_analyze_tool` soi trực tiếp ít nhất 2–3 clip trong kho video gốc.
   - Nếu nội dung video thực tế mâu thuẫn với nhãn Excel $\rightarrow$ Coi nhãn Excel là RÁC và tiến hành sửa ngay sổ cái Excel theo đúng video thật.
2. **Quy Trình Sửa Dứt Điểm:**
   - Cập nhật lại cột `Keyword` và `Hashtag Pool` trong file `Tik<N>.xlsx` của cụm tương ứng.
   - Đồng bộ sổ cái sang Admin host nếu là máy $\ge 200$.
   - Tạo file `.avatar_manifest.json` ghi nhận đúng `entity_type` và `attested_subject` của avatar đã cắt để khóa cứng chốt Outbound Gate.
