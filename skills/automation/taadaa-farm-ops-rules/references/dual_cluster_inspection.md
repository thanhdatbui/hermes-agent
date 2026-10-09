# Dual-Cluster Farm Machine Inspection & Routing

## 1. Machine ID & Cluster Routing Specification
Fleet thiết bị Taadaa Farm phân bổ trên 2 cụm độc lập:
- **Kibe Local Cluster (`N < 200`)**:
  - Máy số: M1 -> M80 (hoặc ID < 200).
  - Mapping file: `D:/OneDrive/TaadaaData/kibe/PROXYgandienthoai.xlsx` (cột `Máy`, `device ID`).
  - ADB Host: Local ADB (`localhost:5037`), sử dụng `adb` local hoặc `C:\Program Files (x86)\xiaowei\tools\adb.exe`.
- **Admin Remote Cluster (`N >= 200`)**:
  - Máy số: M201 -> M280 (hoặc ID >= 200).
  - Mapping file: `D:/OneDrive/TaadaaData/admin/PROXYgandienthoai.xlsx` (cột `Máy`, `device ID`).
  - ADB Host: Remote ADB server tại `192.168.110.119:5037` (tham số `adb -H 192.168.110.119 -P 5037 ...`).

## 2. Standard Machine Inspection Probes (O(1) Live Check)
Khi kiểm tra hiện trường thiết bị, dùng các lệnh shell trích xuất trực tiếp:
1. **Model**:
   `adb [-H host -P port] -s <serial> shell getprop ro.product.model`
2. **Battery (Pin & Sạc)**:
   `adb [-H host -P port] -s <serial> shell "dumpsys battery | grep -E 'level|status'"`
   *(status: 2 = Charging, level: %)*
3. **Current Window Focus**:
   `adb [-H host -P port] -s <serial> shell "dumpsys window | grep mCurrentFocus"`
4. **Power & Screen State**:
   `adb [-H host -P port] -s <serial> shell "dumpsys power | grep -E 'Display Power|mWakefulness'"`

## 3. Tool Standard
Script chuẩn: `D:/Taadaa/tools/inspect_machine.py <N>`
- Cho phép truyền `<N>` hoặc `M<N>` (ví dụ: `201` hoặc `M201`).
- Tự động map cluster, đọc serial từ Excel (`data_only=True, read_only=True`), và hiển thị trạng thái chuẩn.
