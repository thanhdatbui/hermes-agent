# Multi-Cluster Device Resolution Trong tiktok_login_v1 (Kibe vs Admin)

> **Date:** 2026-10-09  
> **Trigger:** `RuntimeError: Khong co STT N trong ACCOUNTS` khi chạy `tiktok_login_v1.py` cho máy cụm Admin ($N \ge 201$).

---

## 1. Bản Chất Sự Cố
- `tiktok_login_v1.py` kế thừa danh sách tĩnh `ACCOUNTS` từ `social_reg_v1.py` (vốn chỉ chứa STT 1–80 của cụm Kibe).
- Khi gọi phục hồi login trên cụm Admin (Máy 201–280):
  ```python
  def resolve_device(stt):
      acc = next((item for item in ACCOUNTS if item["stt"] == stt), None)
      if not acc:
          raise RuntimeError(f"Khong co STT {stt} trong ACCOUNTS")
      return acc["device"]
  ```
  Hàm văng lỗi thoát sớm trước khi kịp kết nối tới thiết bị.

---

## 2. Giải Pháp Chuẩn Hóa O(1)
Bổ sung fallback sang `load_machine_devices(TARGET_INVENTORY_WORKBOOK)`:
```python
def resolve_device(stt):
    acc = next((item for item in ACCOUNTS if item["stt"] == stt), None)
    if acc and acc.get("device"):
        return acc["device"]
    from project_paths import TARGET_INVENTORY_WORKBOOK
    from scripts.target_inventory import load_machine_devices
    dev = load_machine_devices(TARGET_INVENTORY_WORKBOOK).get(stt)
    if dev:
        return dev
    raise RuntimeError(f"Khong co STT {stt} trong ACCOUNTS")
```

### Ưu điểm:
1. `TARGET_INVENTORY_WORKBOOK` được định tuyến tự động theo biến môi trường `TAADAA_HOST_CONFIG` (trỏ tới `D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx` hoặc `kibe/taikhoan_run_safe.xlsx`).
2. Bao phủ đầy đủ 160 máy trên toàn farm.
3. Không làm thay đổi signature hay ảnh hưởng tới các script gọi upstream.

---

## 3. Lỗi Văng Phiên (Session Expired) Gây Kẹt Switcher
- Khi các tài khoản cũ trên máy bị văng về màn One-tap Login ("Chào mừng bạn trở lại"), TikTok Profile hiển thị view chết (unauthenticated), Account Switcher không bung ra khi tap username.
- Khắc phục: Phải chạy `tiktok_login_v1.py` kích hoạt lại phiên cho các tài khoản cũ trước khi reg bù hoặc chuyển tài khoản.
