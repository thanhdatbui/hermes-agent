# Architecture Consensus: Chống Lỗi Vòng Lặp Farm 80 Máy / 600 Nick (Write-without-Read & Excel Preflight)
*Ký duyệt bởi Claude CLI & Sol Planner (2026-09-17)*

## 1. NGUYÊN NHÂN GỐC RỄ (TRIPLE-WRITE & WRITE-WITHOUT-READ)
- **Căn bệnh Write-without-read:** Script reg nick/bù slot chỉ ghi 1 chiều vào Excel mà không kiểm tra thực tế Switcher trên máy thật. Khi máy chạm trần 8 nick, TikTok tự động đẩy nick cũ ra màn hình Fast Login cache, nick mồ côi ngồi chiếm chỗ.
- **Excel làm Control Plane thiếu ràng buộc cứng:** Không có `UNIQUE` constraint hay schema validation. Kéo chuột copy/paste hoặc fill tay lệch dòng sẽ gây trùng số Video Gốc (như 5 cặp máy trong `Tik3.xlsx` bị trỏ chung 1 video gốc: M64-M65, M66-M70, M67-M71, M68-M72, M69-M73) mà không có hệ thống nào chặn.
- **Lý thuyết suông vs Hiện trường:**
  - `adb.get_switcher_accounts()` KHÔNG TỒN TẠI trên Android/TikTok. Bắt buộc phải dùng ATX-Agent dump XML hoặc WinRT OCR màn hình Switcher.
  - SQLite đồng bộ qua OneDrive giữa Kibe và Admin sẽ gây lỗi `database is locked` và hỏng DB. Audit log phải ghi cục bộ (local JSONL per-machine).
  - Background scanner quét 80 máy liên tục sẽ làm nóng máy, hao pin, đụng lock với ca nuôi feed/upload. Bắt buộc dùng mô hình **JIT (Just-In-Time) Reconciliation** — chỉ kiểm tra ngay trước và sau khi thực hiện can thiệp.

---

## 2. 4 QUY TẮC BẤT BIẾN (SYSTEM INVARIANTS) BẮT BUỘC
1. **Trần cứng 8 slot:** `COUNT(slots) <= 8` trên mọi máy. Trước khi reg/login thêm nick mới, nếu Switcher máy thật đã có 8 nick thì BẮT BUỘC DỪNG NGAY (FAIL-LOUD), tuyệt đối không reg đè làm văng nick cũ.
2. **Độc bản vị trí slot:** `UNIQUE(device_id, slot_position)` — 1 slot chỉ 1 nick.
3. **Độc bản render folder:** `UNIQUE(folder_video)` — 1 folder render thành phẩm chỉ cấp cho đúng 1 tài khoản trên toàn farm.
4. **Độc bản kênh nguồn:** `UNIQUE(source_channel)` — 1 kênh video gốc chỉ cấp cho đúng 1 folder video gốc.

---

## 3. THIẾT KẾ LAI THỰC CHIẾN (PRAGMATIC HYBRID DESIGN)

### A. Data Layer (Excel + Preflight Validator)
- Excel vẫn giữ làm giao diện điều hành trực quan cho con người.
- Trước khi chạy bất kỳ pipeline nào (nuôi feed, upload, reg), bắt buộc chạy `excel_preflight_validator.py` để quét toàn bộ các file `Tik1..Tik8.xlsx` và `taikhoan_run_safe.xlsx`:
  - Phát hiện trùng slot, trùng video gốc, lệch công thức tịnh tiến `(slot - 1) * 80 + machine_id`.
  - Nếu phát hiện lỗi: DỪNG PIPELINE NGAY LẬP TỨC và báo rõ dòng/cột bị sai.

### B. Feedback Loop Layer (JIT Reconciliation)
- **Trước khi thêm/bù nick:**
  - Chụp màn hình Switcher $\rightarrow$ Dùng ATX hoặc WinRT OCR đếm số nick thực tế.
  - Nếu $\ge 8$ nick: Báo lỗi và dừng, yêu cầu logout nick mồ côi (đã backup credentials) trước khi nạp tiếp.
- **Sau khi nạp nick:**
  - Chụp lại màn hình Profile chính chủ để xác nhận username/handle khớp với nick vừa nạp.

### C. State & Audit Layer
- Ghi log append-only vào file `audit_log.jsonl` tại từng máy cục bộ (không chia sẻ database file qua cloud sync để tránh lock contention).
