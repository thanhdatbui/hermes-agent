# Kỹ Thuật Chuẩn Hoá Kênh Hoạt Hình 3D Động Vật & Xử Lý Lệch Kho Crawl Gốc vs Kho Render Thực Tế (2026-10-16)

## 1. Hiện Tượng & Bối Cảnh Thực Tế (@vophuc1749 Máy 54 Tik 6)
- Kênh TikTok `@vophuc1749` (Máy 54, Tik 6):
  - Lưới video trên TikTok profile hiển thị 5 video hoạt hình động vật 3D (chú ếch xanh mặc vest đội mũ top hat / thể dục dụng cụ xà đơn, chú mèo con rapper đeo kính râm dây chuyền vàng neon, mèo mướp há to mồm).
  - Nhưng trên ứng dụng TikTok profile, avatar hiển thị lại là ảnh một nhóm người trong nhà (bạn nữ áo len hồng ngồi ghế sofa) và file `D:/video goc/430/avatar.jpg` là ảnh bạn nữ này.
- **Nguyên nhân gốc rễ**:
  - `D:/video goc/430` là video crawl người thật cũ ("Có thể hướng nội hết phần đời còn lại").
  - Trong khi đó, toàn bộ video thực tế đang nuôi và đăng bài trên kênh đến từ kho render **`D:/TIKTOK-videonuoinick/430/`** (5 video hoạt hình 3D động vật nhân hóa).
  - Thuật toán cũ hoặc script trước đó đã lấy avatar từ `D:/video goc/430/avatar.jpg` nạp lên kênh, gây ra sự cọc cạch nghiêm trọng: Kênh hoạt hình meme động vật nhưng avatar lại là người thật ngồi ghế sofa!

## 2. Quy Trình Chuẩn Hoá 3 Món (Ava - Hashtag - Pin) Chuẩn Xác

### Món 1: Ghim Video (Pin Gate $\ge 1.000$ views)
- **Quy tắc cứng**: Chỉ ghim video có $\ge 1.000$ views (tối đa 3 clip).
- Nếu toàn bộ video trên lưới đều $< 1.000$ views (ở kênh này: 113, 122, 334 views) $\rightarrow$ **BẮT BUỘC GIỮ NGUYÊN, KHÔNG GHIM**.

### Món 2: Niche & Hashtags
- Nội dung thực tế: Hoạt hình 3D động vật hài hước. Niche chuẩn: `haihuoc` / `thucung`.
- Tạo marker vật lý `.manual_hashtag_locked` tại cả 2 đầu thư mục (`D:/TIKTOK-videonuoinick/430/` và `D:/video goc/430/`) để ngăn các script tự động quét đè nhãn.

### Món 3: Avatar Trích Xuất Nhân Vật Hoạt Hình 3D
- **Trích xuất trực tiếp từ video render thực tế**: Đọc file `.mp4` trong `D:/TIKTOK-videonuoinick/<F_out>/` (ví dụ `5.mp4` - chú ếch xanh đội mũ, `4.mp4` - chú mèo con rapper).
- **Center-based Crop 512x512 kèm Mask Preview Viền Tròn Xanh**:
  - Đảm bảo đỉnh mũ/tai và cằm nằm lọt 100% trong vòng tròn xanh ($R=256$).
  - Soi mắt kiểm tra qua `browser_vision` và Antigravity Headless CLI (`ag_cli.py ask`).
  - Đưa 2 phương án rõ rệt cho User chọn (Phương án 1: Ếch xanh quý tộc; Phương án 2: Mèo rapper ngầu).

## 3. Khóa Bảo Vệ Registry & Nạp Avatar Tự Động
1. **Ghi đè file avatar**: Copy `avatar_opt1.jpg` sang:
   - `D:/TIKTOK-videonuoinick/430/avatar.jpg`
   - `D:/video goc/430/avatar.jpg`
   - `D:/video goc/454/avatar.jpg` (kho $F_{src}$ theo công thức Máy 54 Tik 6)
2. **Khóa 2 đầu Marker vật lý**:
   - `.manual_avatar_locked`
   - `.manual_hashtag_locked`
3. **Cập nhật 2 file JSON Registry**:
   - `D:/Taadaa/data/manual_avatar_protected_folders.json`
   - `D:/Taadaa/Tiktok-video/data/manual_avatar_protected_folders.json`
   Thêm folder `430`, `454` vào `protected_folders` và mapping `accounts['vophuc1749']`.
4. **Nạp Avatar lên thiết bị**:
   - Chạy runner nền: `python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik 6 --machine 54`.
   - Nghiệm thu artifact thực tế: Trích xuất `avatar-uploaded-confirmed.png` từ `D:/CodexRuntime/tiktok-video/runs/run_<serial>_<timestamp>/`.
   - Soi mắt kiểm chứng màn hình Sửa hồ sơ hiển thị avatar mới trước khi chốt DONE với User.
