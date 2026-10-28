# Dual-Cluster Wi-Fi Preflight Fallback & Vision Gate Claim Fix

## 1. Dual-Cluster Wi-Fi Preflight Fallback (`vpn_preflight.py`)

### Hiện Tượng
Khi chạy batch hoặc watchdog trên host Kibe (máy 1–80) đối với thiết bị thuộc cluster Admin (máy 201–280):
- Khi thiết bị Admin rớt Wi-Fi, Stage 1 Radio toggle (`svc wifi disable && svc wifi enable`) không phục hồi được IP.
- Hệ thống lẽ ra phải kích hoạt Stage 2 Recovery (`adbjoinwifi` vào `admin 1` hoặc `admin 2`), nhưng Stage 2 bị BỎ QUA HOÀN TOÀN (`reconnect_attempted=False`, không có log `stage2_wifi_adbjoinwifi_attempt`).
- Toàn bộ các máy rớt Wi-Fi lập tức bị đánh dấu fail-closed: `dumpsys connectivity: Wi-Fi not connected` hoặc `proxy unreachable`.

### Nguyên Nhân Gốc (Root Cause)
- Hàm `get_wifi_credentials_for_serial(serial)` gọi `get_default_proxy_mapping()`.
- Trên host Kibe, mapping workbook mặc định trỏ về `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` (chỉ chứa serial máy M1–M80).
- Khi tra cứu serial của máy Admin (M201–M280), serial không tồn tại trong workbook Kibe -> hàm trả về `None`.
- Đoạn mã Stage 2 kiểm tra:
  ```python
  wifi_creds = get_wifi_credentials_for_serial(serial)
  if wifi_creds:
      target_ssid, target_pass = wifi_creds
      ...
  ```
  Vì `wifi_creds` là `None`, toàn bộ logic `adbjoinwifi` bị bypass im lặng!

### Giải Pháp Dual-Cluster Fallback
Khi `machine = snapshot.get(clean_serial)` trả về `None`:
Tự động đối chiếu sang workbook của peer cluster (`kibe` <-> `admin`):
```python
peer_name = "admin" if mapping_path.parent.name == "kibe" else "kibe"
peer_path = mapping_path.parent.parent / peer_name / mapping_path.name
if peer_path.is_file():
    try:
        peer_table = _read_serial_machine_table(peer_path)
        machine = peer_table.get(clean_serial)
    except Exception:
        pass
```
Sau đó lấy credentials từ `get_wifi_credentials_for_machine(machine)`.

---

## 2. Phòng Ngừa False Positive Trên Vision Gate Guard (`guard_media_vision_gate.py`)

### Hiện Tượng
Coordinator gửi báo cáo điều tra kèm ảnh hiện trường UI (`screen.png` đã qua OCR kiểm định hợp lệ), nhưng tin nhắn trả lời User bị Vision Gate Guard ghi đè thành:
`Trạng thái: DEGRADED | Mã: UNVERIFIED_BY_VISION | Thiết bị: ...`

### Nguyên Nhân Gốc
Trong `guard_media_vision_gate.py`:
- `is_visual_claim` chứa các từ khóa trần: `"de xuat"`, `"phuong an"`.
- Khi Coordinator viết báo cáo kỹ thuật chứa câu như *"Phương án xử lý:"* hoặc *"Đề xuất retry:"*, regex bắt trúng và gắn cờ tin nhắn là có "Visual Claim" thẩm mỹ (như tranh ảnh, hoa, lá, cảnh).
- Guard sau đó đòi hỏi vé `browser_vision` (từ chối vé `run_winrt_ocr`), bất kể ảnh đính kèm chỉ là ảnh chụp màn hình UI hệ thống.

### Quy Tắc Chuẩn Hóa
1. `is_visual_claim` chỉ được bắt các cụm từ thẩm mỹ/avatar rõ ràng: `"de xuat avatar"`, `"phuong an avatar"`, `"de xuat anh"`, `"phuong an anh"`.
2. Kiểm tra kết hợp `is_visual_image`: Chỉ bắt buộc `browser_vision` khi ảnh thực sự là ảnh đề xuất mỹ thuật/avatar (`proposal`, `avatar`, `canvas`, `crop`, `cand`, `nature`, `scene`). Với ảnh UI thuần (`screen.png`, `ui.png`), vé `run_winrt_ocr` là hoàn toàn hợp lệ theo Invariant Soi Mắt Đọc Ảnh.
