# Hashtag Selection Resilience & Niche Reconciliation Architecture

## 1. Vấn đề gốc: Lệch Niche ở tầng Data & Rủi ro Hashtag Mù

### Triệu chứng
- Kênh video phóng sự / tin tức xã hội (như Tin 3 Phút) nhưng caption bị gắn toàn bộ hashtag ca nhạc: `#nhacvietnam #singing #amnhac #nhac`.
- Kênh video selfie / yoga / gái xinh nhưng caption bị gắn toàn bộ hashtag gaming: `#game #choigame #gamingvietnam`.

### Nguyên nhân gốc (Root Cause)
1. **Lệch ở Data Layer (`state.db`)**: Khi tải video nguồn, bảng `folders` trong `D:\CodexRuntime\tiktok-video\state.db` bị gán niche theo thứ tự danh sách mẫu (`niches_pool.txt`) thay vì kiểm tra tên kênh thực tế (`uploader` / `source_channel`).
2. **Khuếch đại sang Excel (`Tik*.xlsx`)**: Cron `sync_all_tik_keywords.py` đọc từ `state.db` và ghi đè `Keyword Video` + `Hashtag Pool` vào các file `Tik1.xlsx` .. `Tik8.xlsx`.
3. **Bộ chọn cũ không có khiên bảo vệ**: `hashtag_selector.py` bốc ngẫu nhiên 3-5 tags từ `Hashtag Pool`. Khi Pool sai niche, 100% tags sinh ra đều sai bét so với video thực tế.

---

## 2. Kiến trúc giải pháp 2 tầng (Hybrid Architecture)

### Tầng 1: Lớp khiên bảo hiểm trong `hashtag_selector.py` (Upload Engine)
- **Công thức tuyển chọn 3-5 tag**:
  - Giữ nguyên biến thiên tự nhiên: 3 tag (15%), 4 tag (55%), 5 tag (30%).
  - **2 đến 4 tag Viral quốc dân**: Bốc ngẫu nhiên từ pool `#fyp #xuhuong #videohay #viral #trending #tiktokvietnam #moingay #hay`.
  - **Tối đa DUY NHẤT 1 tag Niche**: Bốc tối đa 1 tag ngách đại diện từ keyword/pool. Nếu không có hoặc pool toàn tag chung, bốc toàn bộ tag viral.
  - **Xáo trộn ngẫu nhiên (Shuffle)**: Tag niche không đứng cố định ở đầu hay cuối.
- **Lợi ích**: Khi dữ liệu nguồn bị lệch niche, video chỉ dính tối đa 1 tag ngách nhẹ nhàng; 3-4 tag viral còn lại kéo lại ngữ cảnh, thuật toán AI TikTok (Visual + Audio) tự phân phối đúng tệp mà không bị nhiễu.

### Tầng 2: Data Reconciliation (`state.db` & `sync_all_tik_keywords.py`)
1. **Đối soát tên kênh thực tế**:
   - Truy vấn bảng `videos` lấy `uploader` và `source_channel` của từng folder.
   - So khớp từ khóa trong tên kênh để ánh xạ về đúng slug trong `niches_pool.txt`:
     - *Xuân Hinh / Hài* -> `haihuoc`
     - *Tin 3 Phút / VTV / VTC / Báo* -> `cauchuyen` / `tintuc`
     - *Mê Xe / Otofun* -> `oto`
     - *nhaTO / Nội Thất Long Thành* -> `noithat`
     - *Thắm Dance Sports* -> `nhay`
     - *Yoga Phương Thùy* -> `yoga`
2. **Cập nhật `state.db`**: Ghi lại slug chuẩn vào cột `niche` của bảng `folders`.
3. **Đồng bộ hàng loạt sang 8 file Tik**:
   - Chạy `python C:/Users/Kibe/AppData/Local/hermes/scripts/sync_all_tik_keywords.py`.
   - Script tự động sao lưu `.bak` và ghi đè atomic vào `TaiKhoan` và `Hashtag theo Folder` của toàn bộ các file `Tik1.xlsx` .. `Tik8.xlsx`.
