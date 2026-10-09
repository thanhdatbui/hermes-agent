# Quy Trình Chuẩn Hóa 12 Cụm Niche Hot & Dọn Sạch Toàn Diện Cho Farm Mới / Đăng Ít Video

## 1. Kỷ Luật Tuyệt Đối Khi Cào Video Mới (Chống Đi Cào Niche Cùi)
- **Tình huống kích hoạt**: Khi User yêu cầu cào thêm video hoặc chuẩn hóa video cho dàn mới / acc chưa đăng nhiều video (như Kibe Tik 7, Tik 8 và toàn bộ dàn Admin Tik 1..8):
  - **CẤM TUYỆT ĐỐI**: Tiếp tục cào các niche khô khan/ngách hẹp không có Creator Shorts (ví dụ: *Vật tay, Nội thất, Phụ kiện, Sức khỏe y tế, Kinh doanh, Học tập, Thư viện...*).
  - **BẮT BUỘC**: Dẹp sạch toàn bộ các niche cùi này khỏi Database `state.db` và các Workbook Excel, phân bổ 100% về đúng **12 Cụm Niche Hot / Triệu View**.
  - **Ngoại lệ duy nhất**: Chỉ cào ngách cũ khi cào bổ sung cho các folder sẵn có đã có clip hot đạt chuẩn.

---

## 2. Danh Sách 12 Cụm Niche Hot Chuẩn Viral
1. `douyin_beauty`: Douyin Biến hình (Douyin Visual triệu view)
2. `thucung`: Thú cưng cute (Chó mèo hài hước, pet cute)
3. `cuoi`: Tiểu phẩm hài hước (Hài đời sống, troll hài giải trí)
4. `amthuc`: Món ngon đường phố (Ăn vặt đường phố, review đồ ăn)
5. `xe`: Siêu xe & Xe đẹp (Siêu xe, xe độ kiểng đẹp)
6. `dulich`: Cảnh đẹp du lịch (Phượt, cảnh đẹp Việt Nam check-in)
7. `anime_clip`: Anime Edit (Khoảnh khắc anime ngầu, edit mượt)
8. `gym_fit`: Fitness & Vóc dáng (Động lực giảm cân, workout biến hình)
9. `satisfying`: Mẹo vặt & Satisfying (ASMR phục hồi đồ cũ, life hacks satisfying)
10. `gaixinh_vn`: Gái xinh VN Lifestyle (Nữ sinh, outfit xinh gái VN)
11. `kienthuc_viral`: Sự thật bất ngờ (Bí ẩn thế giới, sự thật lạ lùng)
12. `banhngot`: Làm bánh ngọt (Trang trí bánh kem visual, decor bánh asmr)

---

## 3. Quy Trình Dọn Sạch & Đồng Bộ Kép (Excel Workbook + SQLite + Đĩa)
Khi tiến hành thay máu Niche Hot cho dàn mới:
1. **Dọn dẹp triệt để trên Đĩa**:
   - Quét toàn bộ folder chuyển đổi: Xóa toàn bộ file video gốc cũ dở dang (`.mp4`, `.part`, `.ytdl`).
   - Xóa sạch render output cũ nếu nguồn gốc chưa có video mới đạt chuẩn.
   - Xóa file `avatar.jpg` cũ và `channel_info.json` cũ để tránh nhận nhầm metadata.
2. **Đồng bộ Workbook Excel & State DB**:
   - Ghi đè cột `ChuDe` (Cột D) và `Niche` trong `Tik1.xlsx` .. `Tik8.xlsx` thành nhãn Niche Hot.
   - Cập nhật trường `niche` và đặt `status='pending'`, `video_count=0` trong `state.db` (`folders` table).
3. **Cào Kép TikTok + YouTube Shorts**:
   - Ưu tiên cào kênh TikTok từ kho Master độc quyền.
   - Failover tự động sang YouTube Shorts qua bộ từ khóa chuyên sâu theo từng Niche Hot.
4. **Tự động Cắt Avatar & Nạp Queue PENDING**:
   - Ngay khi tải xong $\ge 35$ clip từ kênh đạt chuẩn, tự động trích frame giây thứ 3.5 làm `avatar.jpg` (kích thước 512x512).
   - Copy `avatar.jpg` sang cả thư mục render output.
   - Nạp cờ `PENDING` vào bảng `avatar_replace_queue` trong `tiktok_tracker.db` để máy thật tự động đổi avatar mới.
