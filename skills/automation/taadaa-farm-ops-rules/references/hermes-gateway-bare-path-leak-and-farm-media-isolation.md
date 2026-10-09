# Hermes Gateway Bare-Path Auto-Upload Leak & Farm Media Isolation (Sự Cố Gửi Nhầm Video Từ Kho Nuôi Nick)

Ngày ghi nhận: 06/09/2026.
Tác nhân: Hermes Gateway Telegram Adapter (`gateway/platforms/base.py`) & Báo cáo kết thúc phiên Farm Alert Máy 39.

---

## 1. HIỆN TƯỢNG VÀ PHẢN ỨNG CỦA USER

- **Hiện tượng**: Ngay sau khi Coordinator gửi tin nhắn báo cáo chốt phiên Máy 39, Telegram nhận được 1 file video MP4 dung lượng 4MB (`file_1098.mp4`).
- **Phản ứng của User**:
  > *"ủa gửi video t chi v, hàm nào gọi lệnh gửi video v, tự nhiên tốn đống quota? hay gửi video k tốn quota nhiều"*
  > *"Ý là bth xong thì gửi ảnh trạng thái máy chứ sao h lại gửi video"*
  > *"Tại sao lại đi gửi video trong kho nuôi nick? Fix đi. Gọi claude cli hỏi"*

---

## 2. NGUYÊN NHÂN GỐC RỄ (ROOT CAUSE)

Trong tin nhắn báo cáo chốt phiên Gate 0, Coordinator ghi văn bản:
`...đăng thành công video 5 (D:\TIKTOK-videonuoinick\306\5.mp4)...` (đường dẫn trần, không bọc backtick).

Hermes Gateway sở hữu cơ chế tự động gửi đính kèm (`extract_local_files` trong `gateway/platforms/base.py`):
1. Gateway chạy regex `path_re` quét toàn bộ nội dung text để tìm các đường dẫn tệp tin cục bộ (trên Windows: `D:\...`, `C:\...` kết thúc bằng đuôi media `.mp4`, `.png`, `.jpg`, `.pdf`...).
2. Với mỗi path tìm thấy, Gateway kiểm tra `os.path.isfile(path)`. Vì file `5.mp4` thực sự tồn tại trong kho nuôi nick trên ổ D, điều kiện này trả về `True`.
3. Hàm `extract_local_files` xóa đường dẫn này khỏi text phản hồi và nhét vào danh sách `local_files`.
4. Trong vòng lặp gửi phản hồi (dòng ~5180), Gateway phân loại extension `.mp4` vào `_VIDEO_EXTS` và gọi `adapter.send_video(chat_id, video_path)` tải thẳng video 4MB từ ổ cứng host lên Telegram.
5. Hàm `validate_media_delivery_path` ở chế độ mặc định (non-strict) chỉ kiểm tra các thư mục hệ thống Linux/Unix (`/etc`, `/proc`, `~/.ssh`) mà hoàn toàn không có cơ chế chặn các thư mục kho dữ liệu lớn trên Windows farm (`D:\TIKTOK-videonuoinick`, `D:\video goc`, `D:\OneDrive`).

---

## 3. ĐÁNH GIÁ TÁC ĐỘNG QUOTA VÀ BĂNG THÔNG

- **Quota AI / API LLM = 0 token**: Việc trích xuất và gửi video diễn ra ở tầng adapter hạ tầng Python sau khi LLM đã hoàn tất sinh text. Không tiêu tốn quota hay token của model.
- **Tiêu tốn băng thông & Nguy cơ lộ dữ liệu**: Tiêu tốn băng thông upload internet (4MB/video), làm rác kênh chat Telegram và vi phạm nguyên tắc bảo mật tài nguyên kho nick farm.

---

## 4. GIẢI PHÁP PHÒNG THỦ 3 TẦNG ĐÃ TRIỂN KHAI

### Tầng 1: Tắt Auto-Deliver Bare Path trong Cấu Hình (`config.yaml`)
Trong file `C:/Users/Kibe/AppData/Local/hermes/config.yaml`:
```yaml
gateway:
  media_delivery:
    auto_deliver_local_files: false
    denied_paths:
      - "D:/TIKTOK-videonuoinick"
      - "D:/video goc"
      - "D:/OneDrive"
```
Helper `_auto_deliver_local_files_enabled()` kiểm tra cờ này; khi là `false`, Gateway bỏ qua toàn bộ việc quét và bốc bare path làm media attachment trong tin nhắn chat.

### Tầng 2: Khóa Cứng Denylist Farm Roots trong Code (`base.py`)
Trong `_media_delivery_denied_paths()` của `gateway/platforms/base.py`:
```python
_FARM_DENIED_ROOTS = (
    "D:/TIKTOK-videonuoinick",
    "D:\\TIKTOK-videonuoinick",
    "D:/video goc",
    "D:\\video goc",
    "D:/video_goc",
    "D:\\video_goc",
    "D:/OneDrive",
    "D:\\OneDrive",
)
for farm_root in _FARM_DENIED_ROOTS:
    denied.append(Path(farm_root))
```
Bất kỳ file nào nằm dưới các thư mục kho farm đều bị `validate_media_delivery_path()` từ chối (`return None`) và bị `extract_local_files()` bỏ qua, bảo vệ tuyệt đối kể cả khi có ai vô tình ghi `MEDIA:D:/TIKTOK-videonuoinick/...`.

### Tầng 3: Kỷ Luật Bọc Backtick Của Coordinator & Worker
- **BẮT BUỘC**: Mọi đường dẫn file dữ liệu farm, file mã nguồn hoặc file log khi nhắc đến trong văn bản chat **BẮT BUỘC PHẢI BỌC TRONG DẤU BACKTICK** (ví dụ: `` `D:\TIKTOK-videonuoinick\306\5.mp4` ``).
- **CẤM TUYỆT ĐỐI**: Không ghi đường dẫn trần (bare path) của bất kỳ file media/video/ảnh nào trong tin nhắn gửi user.
- **Nghiệm thu trực quan**: Khi hoàn tất phiên farm, **CHỈ ĐƯỢC GỬI ẢNH CHỤP MÀN HÌNH THIẾT BỊ (SCREENCAP)** qua cú pháp `MEDIA:C:/Users/Kibe/..._proof.png`. Tuyệt đối không gửi file video trong kho nuôi nick.
