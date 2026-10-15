# Bẫy Cắt Trúng Tóc Mất Mặt (Hair-Only Crop Trap) & Gate Kiểm Định 5 Bộ Phận Khuôn Mặt (2026-10-15)

## 1. Sự Cố Thực Tế (Incident Analysis: 15/10/2026 - @nhathasz4vw Máy 50)
- **Triệu chứng**:
  - Coordinator tạo avatar cho kênh `@nhathasz4vw` (Folder 396) từ video dọc ($1080 \times 1920$).
  - Thuật toán tự động Haar Cascade detect khuôn mặt, nhưng khi tính `side = max(fw, fh) * 2.8` và căn theo `y0`, tâm crop bị trôi lên trán/chữ caption đỉnh video.
  - Kết quả ảnh preview viền tròn gửi User: Hình tròn chứa toàn bộ chữ viết hoa slogan trên kính và phần đỉnh đầu/tóc, khuôn mặt thực sự bị tụt ra ngoài mép dưới (mất toàn bộ mắt, mũi, miệng, cằm).
  - User bức xúc phản hồi: *"Đổi ava lại... Ava loz gì k thấy ng hoặc thấy mỗi cái tóc v"*.
- **Nguyên nhân kỹ thuật**:
  1. **Lệch tâm hình học trên video portrait ($1080 \times 1920$)**: Box của Haar Cascade chỉ ôm vùng mắt-mũi hoặc bắt nhầm caption/sticker phía trên trán. Khi lấy `side` quá lớn mà không clamp chặt theo vị trí sống mũi (`fy + fh * 0.6`), điểm crop bị đẩy ngược lên khiến mặt thật tụt xuống đáy hình tròn.
  2. **Ảo giác thị giác khi kiểm tra lỏng lẻo**: Hỏi LLM chung chung *"Mô tả người trong ảnh"* dễ khiến model nhận diện tóc/trán rồi tự suy luận là có người, bỏ qua việc toàn bộ ngũ quan đã bị cắt sạch.

---

## 2. Công Thức Căn Crop Chuẩn Xác O(1) Cho Video Dọc
Khi trích xuất khuôn mặt từ video portrait $1080 \times 1920$:
```python
def crop_geometry(box, w, h):
    fx, fy, fw, fh = box
    head_center_x = fx + fw * 0.5
    # Tâm khuôn mặt chuẩn nằm ở giữa sống mũi:
    head_center_y = fy + fh * 0.6
    # Giới hạn kích thước cạnh crop vuông để không bị vượt biên ngang và tràn phản chiếu
    side = int(min(fw * 2.6, w * 0.9, h * 0.55))
    x0 = int(head_center_x - side / 2)
    y0 = int(head_center_y - side * 0.5)
    # Clamp cứng trong giới hạn khung hình
    x0 = max(0, min(x0, w - side))
    y0 = max(0, min(y0, h - side))
    return float(x0), float(y0), float(side), True
```

---

## 3. Quy Trình Gate Soi Mắt Nghiêm Ngặt: 5 Bộ Phận Ngũ Quan (Five-Features Gate)
Trước khi gửi bất kỳ ảnh avatar tròn nào (`circle_preview`) cho User, **CẤM TUYỆT ĐỐI** chỉ hỏi chung chung. BẮT BUỘC gọi `ag_cli.py ask` hoặc `browser_vision` với prompt bóc tách nhị phân bắt buộc trả lời đủ 2 câu hỏi:

```bash
python D:/Taadaa/tools/ag_cli.py ask --file "<path_circle.jpg>" \
  "Kiểm định avatar viền tròn xanh:
   1. Có thấy trọn vẹn và rõ nét ĐỦ CẢ 5 BỘ PHẬN: mắt, mũi, miệng, cằm và trán/tóc không? Có bị mất mũi/miệng/cằm hay chỉ thấy mỗi tóc không?
   2. Khuôn mặt có nằm ở trung tâm hình tròn không hay bị cắt mép/lệch đáy?"
```

### Tiêu Chuẩn Pass/Fail Tuyệt Đối:
- **FAIL NGAY LẬP TỨC NẾU**:
  - Không nhìn thấy miệng hoặc cằm (bị cắt ra ngoài viền dưới).
  - Không nhìn thấy mắt/trán (bị cắt ra ngoài viền trên).
  - Chỉ nhìn thấy đỉnh đầu, tóc hoặc lưng áo/mũ nón.
- **PASS KHI VÀ CHỈ KHI**:
  - Thấy rõ cả mắt, mũi, miệng, cằm.
  - Đỉnh tóc có headroom cách mép trên 20–40px, cằm cách mép dưới an toàn.
