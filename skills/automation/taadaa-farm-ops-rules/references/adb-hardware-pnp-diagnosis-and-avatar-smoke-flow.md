# Kỹ Thuật Chẩn Đoán Lỗi ADB Device Not Found & Quy Trình Thay Avatar Nữ Đơn Lẻ

## 1. Chẩn Đoán Sự Cố ADB Báo `device not found` Khi Inspect Máy Farm
Khi lệnh ADB hoặc script `python D:/Taadaa/tools/inspect_machine.py <N>` trả về:
```text
adb.exe: device '<SERIAL>' not found
```
Tuyệt đối KHÔNG chạy vòng lặp retry ADB mù gây nghẽn tiến trình điều phối. Thực hiện quy trình chẩn đoán O(1):
1. **Tra cứu Serial thiết bị:** Từ `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx` hoặc `PROXYgandienthoai.xlsx`.
2. **Kiểm tra trạng thái cắm cáp vật lý qua Windows PnP Device:**
   ```powershell
   powershell.exe -NoProfile -Command "(Get-PnpDevice -InstanceId 'USB\VID_04E8&PID_6860\<SERIAL>').Present"
   ```
   - **`Present: False`**: Máy bị mất kết nối vật lý (tuột cáp USB, lỏng cổng cắm USB Hub, hoặc máy cạn pin/tắt nguồn). Báo ngay người vận hành kiểm tra cắm lại máy tại rack.
   - **`Present: True` nhưng ADB không nhận**: Máy bị mất quyền USB Debugging (Unauthorized), kẹt chế độ USB Charging, hoặc `adb server` bị treo. Xử lý bằng cách restart server adb hoặc bật lại USB debugging.

---

## 2. Invariant Host 56-Core (Deadlock & Memory Allocation Guard)
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

## 3. Quy Trình Upload Avatar Đơn Lẻ Bằng `run_tiktok_upload_avatar.ps1`
Khi cần thay đổi avatar cho tài khoản cụ thể mà không đăng video mới và không làm sai lệch trạng thái video trong workbook:
- **Lệnh thực thi chuẩn:**
  ```powershell
  echo RUN | powershell.exe -NoProfile -ExecutionPolicy Bypass `
    -File "D:/Taadaa/Tiktok-video/run_tiktok_upload_avatar.ps1" `
    -Tik <N> `
    -ForceAvatarMachineList "<M1,M2,...>"
  ```
- **Nguyên lý an toàn:**
  - Kích hoạt `--avatar-smoke` và `--force-avatar-upload`.
  - Hoàn toàn KHÔNG chạm vào các trạng thái `RESOLVE_VIDEO`, `POST_VIDEO`, hay cập nhật số lượng video trong workbook.
  - Sau khi upload và xác minh xong avatar trên TikTok CDN, máy tự động chụp ảnh nghiệm thu, force-stop TikTok và đưa về màn hình Home.
