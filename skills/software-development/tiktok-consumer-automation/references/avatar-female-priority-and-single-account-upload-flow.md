# Quy Chuẩn Tạo Avatar Ưu Tiên Nữ & Upload Avatar Cho Kênh Phone Farm

## 1. Sự Cố Chọn Nhầm Avatar Nam Cho Kênh Gái Xinh (Incident 2026-09-24)
- **Hiện tượng:** Tài khoản `@tubanlrnrmg` (Máy 35 / Sheet `Tik3.xlsx` dòng 36 / Slot 3 / Folder video `275` liên kết video gốc `195`) là kênh gái xinh nhưng avatar hiển thị ảnh một người đàn ông.
- **Nguyên nhân gốc rễ:**
  - Trong kho video gốc `195` (57 video), đa số là video nữ nhưng có một vài video xuất hiện khuôn mặt nam (khách mời, người đi cùng).
  - Hàm `make_representative_avatar` cũ trong `D:/Taadaa/Tiktok-video/scripts/pipeline_common.py` chỉ dùng OpenCV Haar Cascade để phát hiện khuôn mặt rồi gom nhóm (clustering) theo số lần xuất hiện và diện tích bounding box mà **hoàn toàn không có bộ lọc nhận diện giới tính hay ưu tiên nữ**.
  - Kết quả: Cụm khuôn mặt nam vô tình có diện tích hoặc số frame rõ nét cao hơn nên thuật toán chọn nhầm làm ảnh đại diện cho kênh.

---

## 2. Invariant: Ưu Tiên Tuyệt Đối Khuôn Mặt Nữ Bằng AI Vision Filter

### 2.1. Phân loại giới tính tự động bằng ViT ONNX
Mọi quy trình tạo avatar đại diện từ video (`make_representative_avatar`, `make_person_avatar`, `download_by_niche.py:make_avatar_for_folder`) BẮT BUỘC phải tích hợp model thị giác AI `AIFemaleFilter` (`D:/Taadaa/Tiktok-video/models/onnx/model_quantized.onnx`):
```python
from ai_channel_filter import AIFemaleFilter

female_filter = AIFemaleFilter()
if female_filter.is_ready():
    for cluster in clusters:
        if cluster.get("kind") == "person":
            res = female_filter.classify_frame(cluster["crop"])
            cluster["is_female"] = bool(res.get("is_female", False))
            cluster["female_prob"] = float(res.get("female_prob", 0.0))

    female_clusters = [c for c in clusters if c.get("is_female")]
    if female_clusters:
        # Ưu tiên cụm nữ có tần suất xuất hiện cao nhất và độ tin cậy nữ cao nhất
        best = max(female_clusters, key=lambda item: (item["count"], item.get("female_prob", 0.0), item["quality"]))
    else:
        # Fallback về cụm thông thường khi kênh hoàn toàn không có nữ
        best = max(clusters, key=lambda item: (item["count"], item["quality"]))
```

### 2.2. Invariant Host 56-Core (Deadlock & Memory Crash Guard)
Trên máy chủ farm nhiều nhân (56 logical cores):
- Thư viện OpenBLAS mặc định spawn số thread bằng số core CPU cho mỗi phép tính toán ma trận (NumPy, PyTorch, OpenCV, ONNX Runtime).
- Khi chạy script xử lý ảnh/video hoặc pytest, điều này dẫn đến tranh chấp tài nguyên (thread thrashing), làm treo tiến trình (deadlock 100% CPU) hoặc crash cấp phát bộ nhớ ảo `VirtualAlloc`.
- **Quy tắc bắt buộc:** Mọi lệnh thực thi Python liên quan đến media/AI BẮT BUỘC phải kèm biến môi trường:
  ```bash
  export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
  # Hoặc khi gọi lệnh đơn lẻ:
  OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python.exe ...
  ```

---

## 3. Quy Trình Upload Avatar Đơn Lẻ (Avatar-Only Mode)

Khi cần thay đổi avatar cho tài khoản cụ thể mà không đăng video mới và không làm sai lệch trạng thái video trong workbook:

### 3.1. Lệnh thực thi chuẩn (Canonical Command)
```powershell
echo RUN | powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File "D:/Taadaa/Tiktok-video/run_tiktok_upload_avatar.ps1" `
  -Tik <N> `
  -ForceAvatarMachineList "<M1,M2,...>"
```

### 3.2. Cơ chế bảo vệ & Lifecycle của Avatar-Only
1. **Cô lập luồng đăng video:**
   - Script gọi `run_tiktok_upload_batch.ps1` với switch `-AvatarOnly` và `-ForceAvatarMachineList`.
   - Chạy StateMachine ở chế độ `--avatar-smoke` và `--force-avatar-upload`.
   - Hoàn toàn KHÔNG chạm vào các trạng thái `RESOLVE_VIDEO`, `POST_VIDEO`, hay cập nhật số lượng video trong workbook.
2. **Quy trình thực hiện trên thiết bị:**
   - Resolve đường dẫn avatar từ `D:/video goc/<id>/avatar.jpg` hoặc `D:/TIKTOK-videonuoinick/<folder>/avatar.jpg`.
   - Push ảnh lên `/sdcard/Pictures/av_<folder>_<ts>.jpg`.
   - Kích hoạt MediaStore re-index để ảnh xuất hiện trên đầu Gallery/Photos.
   - Điều hướng Profile -> Sửa hồ sơ -> Chọn ảnh mới -> Bỏ tích Story -> Bấm Lưu.
   - Chờ hoàn tất upload lên TikTok CDN và chụp ảnh nghiệm thu `avatar-uploaded-confirmed.png`.
   - Force-stop TikTok và nhấn Home đưa máy về trạng thái an toàn.

---

## 4. Kỹ Thuật Chẩn Đoán Phần Cứng Khi ADB Báo `device not found`

Khi lệnh `adb -s <SERIAL> ...` hoặc `inspect_machine.py <N>` báo lỗi `device 'SERIAL' not found`:
1. **Không thử retry lệnh ADB liên tục:** Dễ gây nghẽn timeout cho toàn bộ session điều phối.
2. **Kiểm tra trạng thái cắm cáp vật lý qua Windows PnP Device:**
   ```powershell
   powershell.exe -NoProfile -Command "(Get-PnpDevice -InstanceId 'USB\VID_04E8&PID_6860\<SERIAL>').Present"
   ```
   - **`Present: False`**: Thiết bị đã bị rút cáp vật lý, lỏng cổng cắm trên USB Hub, hoặc máy bị sập nguồn / tắt nguồn. Báo ngay người vận hành kiểm tra phần cứng tại giá rack.
   - **`Present: True` nhưng ADB không nhận**: Thiết bị bị kẹt chế độ USB Charging, mất quyền USB Debugging (Unauthorized), hoặc kẹt adb daemon. Lúc này mới dùng lệnh reset adb hoặc toggle kết nối.
