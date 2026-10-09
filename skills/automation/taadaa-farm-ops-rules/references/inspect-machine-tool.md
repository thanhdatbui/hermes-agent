# Tra cứu hiện trường thiết bị Farm: inspect_machine.py

Công cụ điều tra nhanh trạng thái thực tế của máy farm không chiếm lock:
`D:\Taadaa\tools\inspect_machine.py` (đồng bộ tự động qua symlink `D:\OneDrive\Taadaa_Sync_Shared\tools\inspect_machine.py`).

## Dual Cluster Routing
- **Máy Kibe Local (`N < 200`)**:
  - Tra cứu Serial từ `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`.
  - Kết nối qua ADB local mặc định (`adb -s <serial>`).
- **Máy Admin Remote (`N >= 200`)**:
  - Tra cứu Serial từ `D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx`.
  - Kết nối qua ADB remote Admin (`adb -H 192.168.110.119 -P 5037 -s <serial>`).

## Cú pháp sử dụng
- Kiểm tra 1 máy cụ thể:
  ```bash
  python D:/Taadaa/tools/inspect_machine.py 201    # Admin remote
  python D:/Taadaa/tools/inspect_machine.py 1      # Kibe local
  ```
- Liệt kê toàn bộ thiết bị đang gắn trên cả 2 cụm:
  ```bash
  python D:/Taadaa/tools/inspect_machine.py
  ```

## Thông tin thu thập O(1)
- Model thiết bị (`ro.product.model`).
- Mức pin & trạng thái sạc (`dumpsys battery`).
- Trạng thái màn hình Awake / Sleep (`dumpsys power`).
- Ứng dụng / Activity đang focus (`mCurrentFocus` từ `dumpsys window`).
