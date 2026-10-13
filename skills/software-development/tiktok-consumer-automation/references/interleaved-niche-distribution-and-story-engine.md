# Phân Bổ Xen Kẽ Niche (Anti-Clustering) & Chiến Lược Content Story Engine

## 1. Bối Cảnh & Bài Học Thực Nghiệm Farm (Tháng 10/2026)
### A. Tín hiệu dữ liệu từ tracker db
- Các kênh bùng nổ đề xuất và tăng tim mạnh nhất trên farm (`chungan981` 19.7k tim/6 clip, `tuantuannguyen56` 4.9k tim/8 clip, `thleyzilkva` 2.7k tim/9 clip, `hakha18062003` 1.0k tim/34 clip) đều thuộc nhóm **Story / Curiosity Engine** (Câu chuyện đời sống, Sự thật thú vị, Học sinh, Cuộc sống).
- Nhóm Visual trần (gái xinh, ẩm thực, xe, thú cưng...) tuy CTR 3 giây đầu cao nhưng thiếu **Curiosity Gap** để giữ chân người xem trọn vẹn 30–60s và kéo comment tranh luận.
- **Chiến lược Niche Hybrid**: Tích hợp 4 Story Niches (`cauchuyen`, `thuvi`, `cuocsong`, `hocsinh`) kết hợp với 8 Core Visual Niches (`gaixinh_vn`, `douyin_beauty`, `thucung`, `amthuc`, `cuoi`, `satisfying`, `kienthuc_viral`, `dulich`).

---

## 2. Invariant: Chống Gom Cụm Niche (Anti-Clustering) Khi Chạy Theo Phiên
### A. Nguyên tắc nghiệp vụ
- **CẤM TUYỆT ĐỐI** gán 1 niche cho toàn bộ máy trong cùng 1 Tik/slot.
- Khi 80 máy cùng chạy trong 1 phiên (batch upload hoặc render), các máy chạy song song. Nếu hàng loạt máy liền kề cùng đăng 1 ngách:
  1. Tự dẫm chân và triệt tiêu traffic lẫn nhau trên TikTok.
  2. Dễ bị thuật toán nhận diện trang trại clone/spam cùng chủ đề.

### B. Thuật toán rải đều Modular Permutation (Stride-based)
Sử dụng công thức bước nhảy nguyên tố cùng nhau với modulo 12:
```python
# m_idx: chỉ số máy (0..79 cho 80 máy)
# slot: số slot Tik (ví dụ 6, 7, 8)
niche_idx = (m_idx * 5 + (slot - 6) * 4) % len(DEFAULT_12_LIST)
```

### C. Tiêu chuẩn nghiệm thu bất biến (3 Invariants):
1. **0 Adjacent Duplicates:** Hai máy liền kề nhau ($M_i$ và $M_{i+1}$) chạy cùng 1 ca tuyệt đối không bao giờ trùng niche.
2. **0 Cross-Slot Overlap:** Cùng 1 máy ở các slot khác nhau (Tik6, Tik7, Tik8) luôn mang các niche khác nhau.
3. **Độ phủ đồng đều:** Mỗi niche trong 12 niche có chính xác 6 đến 7 máy phụ trách trên toàn cụm 80 máy.

---

## 3. Pitfall: Đồng Bộ Giữa Sheet TaiKhoan và Hashtag theo Folder
- Khi đổi Keyword/Niche trong sheet `TaiKhoan`, bắt buộc đồng bộ tương ứng sang sheet `Hashtag theo Folder` (Cột 1: Folder Nguồn, Cột 2: Folder Video, Cột 3: Keyword/Niche, Cột 4: Hashtag Pool).
- Cần chú ý kiểu dữ liệu key trong JSON mapping: Phải ép `str(src_id)` thay vì để lẫn `int` và `str`, tránh tình trạng số lượng keys tăng gấp đôi (ví dụ 640 bị tính thành 1280).
