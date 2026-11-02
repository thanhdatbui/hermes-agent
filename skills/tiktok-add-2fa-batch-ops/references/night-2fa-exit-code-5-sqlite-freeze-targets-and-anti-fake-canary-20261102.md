# Căn Nguyên Lỗi Mã Thoát 5 (2FA) & Nâng Cấp SSOT SQLite Master (02/11/2026)

## 1. Căn Nguyên Runner 2FA Văng Mã Thoát 5
- **Bản chất lỗi:** 
  - Tại phiên ngày 31/10/2026, tầng DAL `core/workbook.py` đã được tích hợp write-through SQLite `farm_master.db`.
  - Tuy nhiên, file entrypoint `python_runner/run_batch_live_2fa.py` trong hàm `freeze_targets()` bị bỏ sót: nó vẫn chạy lệnh `if not workbook_exclusive_available(): raise ...` và mở `openpyxl.load_workbook(workbook_path)`.
  - Khi file Excel bị đồng bộ OneDrive ngầm, bị giữ handle hoặc kẹt lock `~$...xlsx` quá 5 lần retry: runner trả về `BLOCKED: WORKBOOK_HYDRATION_FAILED` và thoát với **mã thoát 5**, khiến báo cáo farm hiển thị `Hoàn tất 0 | Bỏ qua 0 | Lỗi 0`.

## 2. Giải Pháp Chuẩn Hóa SSOT `freeze_targets_from_sqlite()`
- **Cơ chế:**
  - Bổ sung hàm `freeze_targets_from_sqlite(db_path, journal_root, limit)`.
  - Query trực tiếp bảng `tiktok_accounts` JOIN `machines` trong `D:/Taadaa/data/farm_master.db` với URI read-only (`mode=ro`).
  - Ưu tiên tài khoản: (1) Blank password trước, (2) Fresh 2FA trước existing 2FA, (3) Resumable journals, (4) Thao tác hoàn tất trong 0.005s mà không mở Excel.
  - Tách biệt môi trường unit test: Chỉ kích hoạt nạp SQLite khi `is_farm_wb` là True (`taikhoan_dat_v2`, `taadaadata`, `taikhoan_run_safe`) và database file tồn tại, tránh làm treo các unit test dùng file Excel giả lập.

## 3. Bài Học Xương Máu Về Gate 6 & Anti-Fake Canary
- **Phân định rõ phạm vi (Dọn dữ liệu vs Sửa code):**
  - **Dọn dữ liệu server/DB:** Tuyệt đối KHÔNG cần Canary máy thật. Nghiệm thu bằng read-back đối soát trước/sau (`COUNT`, `VACUUM`).
  - **Sửa code runner:** Bắt buộc Canary máy thật có não (Semantic Canary).
- **CẤM TUYỆT ĐỐI trò Canary đối phó (Fake Canary):**
  - CẤM tự ý gửi lệnh bật màn hình (`keyevent 224`) rồi chụp đại một app đang treo sẵn trên máy để nộp ảnh cho qua Gate 6 khi nhánh code vừa sửa hoàn toàn chưa được thực thi trên máy.
  - Bắt buộc kiểm tra `canary_runner.py` phải nhận file plan (`--plan <path>`) để đối soát `semantic.log_assertions` trong `log.jsonl`. Nếu nhánh code chưa chạy thực tế $\rightarrow$ Canary phải FAIL-CLOSED (Exit 1).
