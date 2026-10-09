# Curated Pool Multi-Channel Allocation and Direct Folder Growth (2026-10-07)

## 1. Bối cảnh & Vấn đề thực tế
Khi cào nguồn video mới cho 1 kênh độc quyền (như `@dresswithdan`), số lượng clip tải về thường rất lớn (200 - 300+ clip). Trong khi đó, định mức chuẩn tối thiểu của farm là 40 - 45 clip / folder.
Operator đã ra 2 chỉ thị điều phối và tối ưu hóa tài nguyên then chốt:
1. **45 clip là mốc tối thiểu (MIN), không phải trần cố định (MAX):** Nếu một kênh độc quyền có nhiều video đẹp, nạp thẳng 70+ clip vào folder nuôi độc quyền để nuôi dài hơi (7-8 tháng) thay vì tạo folder phụ lắt nhắt (`495_goi_dau_dot2`).
2. **Gom video dư sang Bể Gộp Đa Kênh (`curated_pool`):** Toàn bộ video thừa còn lại (sau khi nạp độc quyền) phải gom vào `D:\video goc\curated_pool` với định dạng `{channel_prefix}_{video_id}.mp4` để phân phối cho các folder đa kênh / kênh tổng hợp thiếu video trên toàn farm (cả Kibe và Admin).

## 2. Quy trình phân bổ 2 tầng (Exclusive Allocation & Pool Distribution)

### Bước 1: Nạp độc quyền & Tăng dung lượng folder trực tiếp
- Chọn `N` video (ví dụ 45 - 70 video) chất lượng cao nhất nạp thẳng vào `D:\video goc\<Folder>` (đánh số thứ tự tăng dần từ `1.mp4` đến `N.mp4`).
- CẤM tạo các folder đệm/gối đầu tạm bợ làm rối rắm hệ thống đường dẫn.

### Bước 2: Gom video thừa vào `curated_pool`
- Với toàn bộ video còn lại từ clip `N+1` trở đi:
  - Copy sang `D:\video goc\curated_pool` với tên `{uploader}_{video_id}.mp4` để chống trùng tên và lưu vết xuất xứ.
  - Loại bỏ các clip đã được gán độc quyền để đảm bảo không bị overlap giữa kênh độc quyền và kênh tổng hợp.

### Bước 3: Phân bổ từ Bể Gộp vào các Folder Đa Kênh / Folder thiếu video
- Quét các workbook (`Tik1..8.xlsx` của Kibe và Admin) để tìm các folder thuộc ngách phù hợp (Gái xinh VN, Douyin, Tổng hợp, Mix) đang thiếu video (< 40-45 clip).
- Phân bổ bù đủ `45` video cho mỗi folder mục tiêu (đánh số nối tiếp theo các file đã có trong folder).
- Áp dụng xáo trộn ngẫu nhiên (shuffle) để các folder tổng hợp nhận được phân bố clip đa dạng, không bị dồn cục 1 kênh.

### Bước 4: Kích hoạt Render thành phẩm tự động
- Chạy `random_batch_render.py` với cờ `--resume-verify-existing` (nếu folder đã có một phần clip render trước đó) hoặc render mới toàn bộ.
- Renderer luôn tự động chuyển hóa mọi tên file nguồn thành định dạng số thứ tự tăng dần: `1.mp4, 2.mp4, ..., 45.mp4`.
- Cập nhật trạng thái `RUNNING` / `OK` trong các file Excel tương ứng.
