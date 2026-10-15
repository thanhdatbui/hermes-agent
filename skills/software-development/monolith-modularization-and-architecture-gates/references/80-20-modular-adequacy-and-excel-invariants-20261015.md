# Kỷ Luật 80/20 Trong Modular Hóa & Chẩn Đoán Invariant Excel (15/10/2026)

## 1. Nguyên Tắc 80/20: Điểm Dừng Modular Hóa (Stopping at Operational Sufficiency)
- **Tập trung 20% cốt lõi mang lại 80% kết quả:** Khi phân rã một monolith lớn (như `scripts/feed_session_watchdog.py`), mục tiêu chính là đưa dung lượng dòng xuống dưới Architecture Gate (`<= 1.450` dòng) và tách các domain chịu tải độc lập (`lock`, `merger`, `alerts`, `formatters`, `parser`).
- **Bẫy Over-Modularization (80% công sức chỉ đổi <20% giá trị):** Khi tất cả unit tests đã pass và cron/daemon chạy thành công (`exit 0`), **DỪNG LẠI NGAY**. Không tiếp tục tách nhỏ các khối toán học hay logic tiện ích nội bộ (như reconcile math) chỉ để thỏa mãn sự cầu toàn hình thức.
- **Phong cách giao tiếp:** Báo cáo thẳng vào kết quả và chỉ ra đúng điểm nghẽn thực sự thay vì tường thuật dài dòng hoặc đề xuất thêm các bước tái cấu trúc không cần thiết.

## 2. Dual-Path Import Fallback Khi Chạy Từ Deploy Staging
Khi script monolith được chạy từ nhiều môi trường khác nhau (như repo gốc `D:\Taadaa\...` vs deploy directory `%LOCALAPPDATA%\hermes\scripts`):
- `from watchdog.lock import ...` hay `from scripts.watchdog.lock import ...` sẽ bị crash `ModuleNotFoundError` nếu không đưa đường dẫn repo `scripts/` vào `sys.path`.
- **Pattern chuẩn:**
  ```python
  _this_dir = os.path.dirname(os.path.abspath(__file__))
  _scripts_fallback = r"D:\Taadaa\tiktok-luot nuoi acc\scripts"
  for _p in (_this_dir, _scripts_fallback):
      if os.path.isdir(_p) and _p not in sys.path:
          sys.path.insert(0, _p)
  from watchdog.lock import ProcessLock, ...
  ```

## 3. Khắc Phục Lỗi Invariant Excel (Rule 3: Folder Video) Bằng Preflight Validator
- **Triệu chứng:** Cron job `taikhoan-run-safe-sync` dừng an toàn và báo lỗi:
  `[PREFLIGHT_VALIDATOR_FAIL] Tik4.xlsx: dòng X, cột 4, máy M - Sai công thức Folder Video: Y (kỳ vọng: Z theo công thức (M - 1) * 8 + Slot)`
- **Nguyên nhân phổ biến:** Nhập nhầm giá trị của cột `video gốc` (cột 5) đè sang cột `Folder Video` (cột 4), dẫn đến trùng lặp Folder Video trên toàn farm.
- **Quy trình xử lý O(1) chuẩn 80/20:**
  1. Chạy `python D:/Taadaa/tools/excel_preflight_validator.py --excel-dir D:/OneDrive/TaadaaData/kibe` để định vị chính xác ô lỗi.
  2. Tạo bản backup có timestamp: `Tik{S}.xlsx.bak_YYYYMMDD_HHMMSS`.
  3. Mở workbook qua `openpyxl`, gán lại đúng công thức: `Folder Video = (Máy - 1) * 8 + Slot`.
  4. Lưu file và kiểm tra lại bằng `excel_preflight_validator.py` cho đến khi đạt `PASS 100%`.
  5. Kích hoạt cronjob test ngay lập tức để xác nhận `last_status: ok`.
