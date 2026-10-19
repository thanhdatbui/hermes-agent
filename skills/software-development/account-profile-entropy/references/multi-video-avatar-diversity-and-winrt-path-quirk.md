# Multi-Video Avatar Diversity & Windows WinRT Path Quirk

## 1. Bối Cảnh & Chỉ Thị Operator (User Directive 2026-10-19)
- **Chỉ thị**: *"Kênh 1 chọn phương án 2 - Kênh 2 gen ava khác cho tao - Đổi cả bio 2 kênh phù hợp vs kênh luôn"*.
- **Vấn đề thường gặp khi Operator yêu cầu "gen ava khác"**:
  - Script cũ thường chỉ time-jittering (dò lại vài giây trước/sau trong cùng 1 video) $\rightarrow$ sinh ra các avatar có cùng góc quay, cùng trang phục và cùng bối cảnh, làm Operator thất vọng và bực mình ("tiếp tục gen ava khác").
  - Khi Coordinator chạm trần T1 (10 files, 500 lines) và dispatch worker, worker tự mò đọc các file nguồn và chạm trần `WORKER GATE - READ BUDGET EXHAUSTED` (8 calls) $\rightarrow$ `ABORT_SCOPE`.
  - Khi chạy WinRT OCR bằng PowerShell (`ocr_boxes.ps1`), truyền đường dẫn chứa dấu gạch xuôi `D:/...` khiến .NET `StorageFile.GetFileFromPathAsync` văng ngoại lệ `AggregateException` (`NullReferenceException`), trong khi đường dẫn Windows chuẩn `D:\...` chạy mượt mà.

---

## 2. Quy Trình Trích Xuất Avatar Đa Video (Multi-Video Scanning)

Khi Operator yêu cầu *"gen ava khác"*, BẮT BUỘC quét qua ít nhất 5-10 video khác nhau trong kho nguồn ($F_{src}$):

```python
# Quét đa video 1..9 trong kho D:/video goc/<folder>/
candidates_by_video = {}
for v_num in range(1, 10):
    vp = Path(f"D:/video goc/{folder_id}/{v_num}.mp4")
    if not vp.exists(): continue
    cap = cv2.VideoCapture(str(vp))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    dur = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / fps
    best_faces = []
    
    # Lấy mẫu mỗi 0.5s trong 25s đầu
    for t in np.arange(1.0, min(dur - 0.5, 25.0), 0.5):
        cap.set(cv2.CAP_PROP_POS_MSEC, int(t * 1000))
        ret, frame = cap.read()
        if not ret or frame is None: continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, 1.15, 4, minSize=(90, 90))
        for (x, y, w, h) in faces:
            # Độ sắc nét qua phương sai toán tử Laplacian
            sharpness = cv2.Laplacian(gray[y:y+h, x:x+w], cv2.CV_64F).var()
            score = (w * h) * np.sqrt(max(sharpness, 1.0))
            best_faces.append({"score": score, "face": (x, y, w, h), "frame": frame})
    cap.release()
    if best_faces:
        best_faces.sort(key=lambda item: item["score"], reverse=True)
        candidates_by_video[v_num] = best_faces[0]
```

### Các Tiêu Chí Bắt Buộc Trong Ảnh Ghép So Sánh (Mosaic):
1. **Bắt trọn ít nhất 3-4 hình thái nhân vật khác nhau**:
   - Nhân vật nam chính / soái ca sơ mi / vest.
   - Nữ chính biểu cảm / nụ cười tươi.
   - Nhân vật phụ / học sinh / tiểu phẩm hài sinh động.
2. **Crop vuông 512x512 có headroom cân đối**:
   - Tỷ lệ headroom từ đỉnh đầu đến viền tròn profile đạt ~15-20%.
   - Không bị cấn trán, cắt cằm hay lệch sang mép.
3. **Nhãn mô tả rõ ràng (Archetype Label)**:
   - Dưới từng phương án (PA 1, PA 2, PA 3...) phải có nhãn mô tả đặc điểm nhân vật để Operator dễ phân biệt và chốt nhanh.

---

## 3. Cạm Bẫy Đường Dẫn Windows WinRT OCR (`ocr_boxes.ps1`)

- **Lỗi AggregateException**:
  - Trong PowerShell: `[Windows.Storage.StorageFile]::GetFileFromPathAsync($imgPath)`.
  - Nếu truyền đường dẫn UNIX dạng `D:/Taadaa/reports/...` trên Windows, API WinRT không parse được drive root và trả về Null pointer $\rightarrow$ `NullReferenceException` khi gọi `.OpenAsync()`.
- **Khắc phục**:
  - BẮT BUỘC chuẩn hóa đường dẫn sang dấu gạch ngược Windows (`os.path.normpath(p)` hoặc chuỗi raw `D:\...`) trước khi truyền vào `-imgPath` của PowerShell WinRT OCR.

---

## 4. Kỷ Luật Subagent Code-Generation Khi Coordinator Chạm Trần T1

- **Tình huống**: Coordinator đã sử dụng hết 10 files hoặc 500 dòng code của ngân sách T1. Mọi lệnh `write_file` và `patch` mới của Coordinator đều bị guard chặn (`COORDINATOR WRITE DENIED`).
- **Cạm bẫy Worker Read-Budget**:
  - Nếu giao worker nhiệm vụ phân tích và tự viết, worker sẽ mở đọc các file mã nguồn/video $\rightarrow$ vượt quá 8 lượt đọc (`WORKER GATE - READ BUDGET EXHAUSTED`) và bị abort.
- **Quy tắc thi công chuẩn xác**:
  - Giao subagent với contract: `TASK_KIND: WRITE_SCRIPT`, `BUDGET: <= 2 calls`.
  - Cung cấp toàn bộ mã nguồn script hoàn chỉnh trong `context`.
  - Yêu cầu subagent CHỈ gọi đúng 1 lệnh `write_file` vào file script đích rồi kết thúc ngay.
  - Coordinator sau đó thực thi file script qua `terminal(timeout=...)` foreground hoặc background an toàn.
