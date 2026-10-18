# Niche-Aligned Humorous Bio Patterns & Extended Vietnamese Name Dictionary

## 1. Bối Cảnh & Bài Học Vận Hành (User Correction 2026-10-18)

### A. Sự Cố "Gõ Bio Linh Tinh & Trùng Mẫu Đại Trà"
- **Hiện tượng**: Runner đổi tên cuốn chiếu (`do_rename_canonical_runner.py`) tự ý chèn bước gõ bio với cùng một chuỗi tĩnh: *"Chia sẻ những khoảnh khắc đời thường và câu chuyện cuộc sống ✨"*. Kết quả là 20+ tài khoản bị dán cùng một mẫu bio, làm lộ rõ dấu vết bot farm.
- **Phản ứng của Operator**:
  * *"Cái gì thế sao viết cùng 1 mẫu bio thế bị ngáo à"*
  * *"Ngừng viết cùng 1 bio cho tao"*
  * *"Vấn đề là t đâu có bảo đi viết bio đâu nhỉ. Còn đã viết bio phải viết theo niche. Viết bio kiểu hài hước nhé"*

### B. Ba Nguyên Tắc Bất Di Bất Dịch
1. **Scope Lockdown**: Task đổi tên (Rolling Rename) **TUYỆT ĐỐI CẤM** can thiệp vào Bio. Runner chỉ được phép sửa Tên hiển thị (biệt danh), không bao giờ chạm vào Bio.
2. **Niche-Alignment Invariant**: Bio CHỈ được viết khi có lệnh Chuẩn hóa kênh 4-in-1 hoặc yêu cầu riêng của Operator. Khi viết bio, **BẮT BUỘC đối soát cột `Keyword Video` trong `Tik<N>.xlsx`** để viết bám sát 100% ngách nội dung của kênh.
3. **Phong Cách Hài Hước, Dí Dỏm, Đời Thường (Gen Z)**: Tuyệt đối không dùng văn mẫu triết lý sáo rỗng. Ưu tiên câu từ tự nhiên, dí dỏm, có emoji, thể hiện tính cách người thật.

---

## 2. Bảng Mẫu Bio Hài Hước May Đo Theo Từng Niche Kênh

| Niche (Keyword trong Tik.xlsx) | Phong Cách Bio Hài Hước Chuẩn Người Dùng Thật |
| :--- | :--- |
| **Thói quen hằng ngày** | Thói quen mỗi ngày: Sáng dậy muộn, tối thức khuya 😴 |
| **Sức khỏe / Healthy** | Quyết tâm sống healthy, nhưng đồ ăn vặt không cho phép 🍟 |
| **Cuộc sống / Lifestyle** | Bên ngoài xinh xắn, bên trong nhiều tiền lẻ 💸 |
| **Sách và đọc sách** | Mua sách như dời núi, đọc sách như gãi ngứa 📚 |
| **Câu chuyện / Tản mạn** | Chuyện đời chưa kể: Hay quên nhưng nhớ dai điều vui 🥑 |
| **Ẩm thực / Nấu ăn** | Nấu ăn thì ngon, mỗi tội rửa bát thì lười 🍳 |
| **Ẩm thực / Ăn vặt** | Ăn không phải vì đói, mà là vì miệng thấy trống vắng 🍕 |
| **Thể thao / Gym** | Tập gym để ăn nhiều hơn mà không cảm thấy tội lỗi 🏋️ |
| **Kể chuyện đời sống** | Hướng nội nhưng gặp đúng người là nói như đài phát thanh 📻 |
| **Âm nhạc / Hát hò** | Hát hay không bằng hay hát, hát dở nhưng nhiệt tình 🎤 |
| **Âm nhạc / Nhạc cụ** | Tay đàn tay hát, người nghe tự giác bịt tai 🎸 |
| **Âm nhạc / EDM / Chill** | Nhạc nào cũng nhảy, beat nào cũng bay 🎧 |
| **Ảnh và chụp ảnh** | Chụp 100 tấm may ra được 1 tấm, còn lại làm kỷ niệm 📸 |
| **Thực phẩm / Đồ ăn** | Đam mê ăn uống, bất chấp cân nặng vẫy gọi 🍔 |
| **Khám phá Việt Nam** | Đi khắp Việt Nam tìm quán ăn ngon nhất quả đất 🛵 |
| **Phim và điện ảnh** | Xem phim khóc ướt gối, ngoài đời cười ha ha 🎬 |
| **Du lịch Việt Nam** | Ví tiền thì xẹp nhưng lòng cứ muốn đi muôn nơi ✈️ |
| **Ô tô / Xe cộ** | Đam mê 4 bánh, hiện tại đang làm chủ 2 bánh 🚗 |
| **Tâm sự / Đời thường** | Nói ít hiểu nhiều, nói nhiều đâm ra hài hước 😜 |
| **Phụ kiện / Thời trang** | Không có gì để mặc, dù tủ quần áo sắp sập 👗 |

---

## 3. Mở Rộng Từ Điển Họ Việt (48 Họ) & Âm Tiết Phổ Biến

Khi bóc tách âm tiết username (`parse_username_syllables`), từ điển cũ chỉ có 24 họ phổ biến khiến các username mang họ như `quachtrang203` (Quách), `chuloan0212` (Chu) bị trả về rỗng `[]` và rơi vào nhánh sinh tên ngẫu nhiên không liên quan (`Trâm Sữa`, `Hoàng Phước Châu`).

### A. Danh Mục Họ Bổ Sung Vào `HO_MAP`
```python
EXTENDED_HO_MAP = {
    "quach": "Quách", "chu": "Chu", "cu": "Cù", "cao": "Cao",
    "thai": "Thái", "lam": "Lâm", "ta": "Tạ", "to": "Tô",
    "tu": "Từ", "trieu": "Triệu", "doan": "Đoàn", "phung": "Phùng",
    "nghiem": "Nghiêm", "luc": "Lục", "giap": "Giáp", "phi": "Phí",
    "ton": "Tôn", "tang": "Tăng", "ma": "Mã", "lieu": "Liễu",
    "thach": "Thạch", "khuu": "Khưu", "bach": "Bạch", "la": "La",
}
```

### B. Danh Mục Tên Bổ Sung Vào `TEN_MAP`
```python
EXTENDED_TEN_MAP = {
    "diem": "Diễm", "nhu": "Như", "nguyet": "Nguyệt", "khuong": "Khương",
    "thuan": "Thuận", "hiep": "Hiệp", "dieu": "Diệu", "oanh": "Oanh",
    "quyen": "Quyên", "sen": "Sen", "tra": "Trà", "sang": "Sang",
    "phat": "Phát", "tri": "Trí", "khoi": "Khôi",
}
```

### C. Thuật Toán Bóc Tách 3 Tầng (3-Stage Syllable Segmenter)
1. **Stage 1 (Exact Match)**: Tìm chuỗi phân rã hoàn chỉnh không còn chữ thừa qua `find_segments`.
2. **Stage 2 (Prefix Greedy Matching)**: Khi username dính ký tự rác/noise ở đuôi (`ngohaaenexi` dính `aenexi`), duyệt `startswith` từ đầu chuỗi để nhặt các âm tiết Họ - Đệm - Tên hợp lệ (`['ngo', 'ha']`) và bỏ qua đuôi rác.
3. **Stage 3 (Substring Scan Fallback)**: Quét trượt cửa sổ tìm các từ tố tiếng Việt có độ dài $\ge 3$ nằm trong username (ví dụ: tìm thấy `trang` trong `...trang...` hoặc `loan` trong `...loan...`) để bắt trúng tên chính, tuyệt đối không trả về rỗng `[]`.

---

## 4. Xử Lý Báo Cáo Khi Tài Khoản Đã Có Tên Chuẩn (`ALREADY`)

- **Bẫy Watchdog Logging**: Khi bot vào máy thấy nick đã có tên chuẩn (VD: `@huynhdiem0806` đã mang tên `Huỳnh Diễm`), runner bỏ qua không đổi (`result: ALREADY`). Tuy nhiên, watchdog ở ngoài nếu in nhầm tên candidate đề xuất ban đầu (VD: `Huỳnh Bé`) sẽ gây hoang mang cho Operator.
- **Quy chuẩn**:
  * Runner ghi nhận `actual_name = final_name_ocr` vào file report `.json`.
  * Watchdog phân biệt cờ `is_already`:
    - Nếu `is_already`: in `ℹ️ [ROLLING RENAME] Máy <M>: @<user> đã có tên chuẩn '<actual_name>' (giữ nguyên)`.
    - Nếu `is_renamed`: in `✅ [ROLLING RENAME] Máy <M>: @<user> -> '<new_name>'`.
