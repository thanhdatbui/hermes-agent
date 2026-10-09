# Unified Safe Workbook vs Separated Operational Workbooks (2026-09-20)

## Bối cảnh & Yêu cầu từ User
Khi mở rộng hệ thống sang mô hình Follow chéo giữa cụm Kibe (Máy 1..80) và cụm Admin (Máy 201..280), phát sinh câu hỏi kiến trúc:
**"Có nên gộp hết các file Excel của toàn Farm vào 1 file duy nhất không?"**

## Phán quyết Kiến trúc của Sol (Lead AI Architect & Security Auditor)
> **"KHÔNG GỘP HẾT EXCEL VÀO MỘT FILE. Gộp logic để đọc — tuyệt đối KHÔNG gộp vật lý để vận hành."**

---

## 1. Phân biệt mạch lạc 2 tầng dữ liệu

| Tầng Dữ Liệu | Danh sách File | Tính chất Vận hành | Nguyên tắc Phân lập |
|---|---|---|---|
| **Tầng 1: Sổ cái Vận hành** *(Operational Workbooks)* | • `kibe/taikhoan_dat_v2_updated .xlsx`<br>• `admin/taikhoan_dat_v2_updated .xlsx`<br>• `Tik1.xlsx` .. `Tik8.xlsx`<br>• `taikhoan_run_safe.xlsx` riêng từng cụm | • Chứa mật khẩu, mail, pass mail, 2FA, DOB<br>• Nhiều runner ghi/cập nhật đồng thời theo ca (`Video Đã Đăng`, status)<br>• Gắn chặt với hardware & lifecycle từng cụm máy | ❌ **CẤM GỘP TUYỆT ĐỐI**<br>• Tránh Race Condition, File Lock & OneDrive Conflict<br>• Tránh Single Point of Failure (hỏng 1 file sập cả 160 máy)<br>• Giữ vững Blast Radius an toàn giữa các domain |
| **Tầng 2: Nguồn Đích Follow** *(Target Read-Only Pool)* | • `taikhoan_run_safe_combined.xlsx` | • Danh bạ ID tài khoản hợp nhất toàn farm (Kibe + Admin)<br>• Thuần túy READ-ONLY, không chứa credentials, không có runner nào ghi đè | ✅ **TẠO VIEW GỘP CHỈ ĐỌC**<br>(611 nick Kibe + 319 nick Admin = 930 UIDs) |

---

## 2. Triển khai Kỹ thuật Chuẩn Farm

### A. Tự động xuất file gộp `taikhoan_run_safe_combined.xlsx`
- Script chuẩn: `D:/Taadaa/tools/sync_combined_safe_workbook.py`.
- Đọc `read_only=True` từ cả 2 nguồn:
  - `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx` (Máy 1..80)
  - `D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx` (Máy 201..280)
- Ghi nguyên tử (atomic replace trên cùng filesystem `D:`) xuất ra:
  `D:/OneDrive/TaadaaData/taikhoan_run_safe_combined.xlsx`
- Hook tự động: Móc trực tiếp vào cuối `hermes_taikhoan_sync_cron.py` (chạy mỗi 5 phút). Khi có thay đổi nick mới ở bất kỳ cụm nào, file gộp tự động làm mới.

### B. Khóa cứng Hard Gate cho Anchor Mode 2 (`follow_engine.py`)
- Khi một máy chạy Follow Mode 2 (đi tìm nick Anchor dày follower/following để follow danh sách fan):
  - **BẮT BUỘC chỉ bốc nick của cụm Kibe (`machine <= 80` và $\ge 10$ video)**.
  - **LOẠI TRỪ TUYỆT ĐỐI dàn Admin làm Anchor** (`machine >= 201`): Vì tài khoản bên Admin mới tạo/nuôi, đồ thị following còn mỏng, nếu bốc làm anchor sẽ lãng phí quota tìm kiếm. Dàn Admin chỉ đóng vai trò Target được follow trong pool.
- Đoạn code Hard Gate trong `FollowEngine.anchor_uids()`:
  ```python
  uid_to_machine: dict[str, int] = {}
  for row in getattr(self.uid_source_mapping, "rows", []):
      ...
      try:
          machine_val = int(getattr(row, "machine", 0))
      except Exception:
          machine_val = 0
      uid_to_machine.setdefault(uid.casefold(), machine_val)

  filtered = [
      u for u in uids
      if row_uids.get(str(u).casefold(), 99) <= 2
      and row_video_counts.get(str(u).casefold(), 0) >= 10
      and uid_to_machine.get(str(u).casefold(), 999) <= 80  # Hard Gate: CHỈ máy Kibe (1..80)
      and str(u).strip().lstrip("@").casefold() != active
  ]
  ```

### C. Cấu hình Runner Follow (`tiktok-follow`)
- Toàn bộ `config.example.yaml` và `config/machine*.yaml` trỏ:
  ```yaml
  workbook: "D:\\OneDrive\\TaadaaData\\taikhoan_run_safe_combined.xlsx"
  ```
- Toàn bộ 930 UIDs (cả Kibe lẫn Admin) đều có cơ hội nhận follow từ các máy khác.
