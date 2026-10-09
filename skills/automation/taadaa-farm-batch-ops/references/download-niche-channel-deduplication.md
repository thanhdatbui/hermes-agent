# Hướng Dẫn Vận Hành & Chống Trùng Kênh Trong Batch Download Theo Niche

## 1. Cơ Chế Chống Trùng Nguồn Video (`download_by_niche.py`)
- **Nguyên nhân gốc rễ từng gây nhầm lẫn**:
  + `folders.source_channel` từng bị NULL trong các đợt tải cũ, khiến câu query `COUNT(*) FROM folders WHERE source_channel=?` trả về 0.
  + Cơ chế cào bù kênh khi thiếu video từng trộn nhiều kênh vào 1 folder (`min_videos`).
- **Thực tế kiểm chứng database**:
  + 0 video trùng lặp trên toàn farm (`video_id` là duy nhất).
  + Mỗi kênh chỉ nên cấp cho đúng 1 folder video gốc.
- **Quy tắc bảo vệ**:
  + Phải kiểm tra tồn tại chéo cả bảng `folders` lẫn bảng `videos` trước khi cấp source cho folder mới.
  + Tuyệt đối không để xảy ra tình trạng 1 folder video mang 2 kênh đại diện khác nhau.

## 2. Quy Tắc Đối Soát Thư Mục Video Gốc & Render
- **Thư mục video gốc**: `D:\video goc\{slot_video_goc}` (chứa video Shorts cào về từ kênh duy nhất).
- **Thư mục render nuôi nick**: `D:\TIKTOK-videonuoinick\{folder_video}` (được render biến đổi từ video gốc tương ứng).
- Không nhầm lẫn giữa số thứ tự Render Folder $(m-1)\times 8 + \text{slot}$ và Video Gốc $(\text{slot}-1)\times 80 + m$.
