# Quy Chuẩn Kiến Trúc Multi-Cluster 2FA TikTok & Watchdog Decoupling (Kibe & Admin)

Tài liệu đúc kết từ phiên vận hành thực tế ngày 06/10/2026.

---

## 1. Bài học về Ràng buộc Dải Máy (Machine Range Constraint)
- **Vấn đề cũ:** Trong `run_batch_live_2fa.py`, hàm helper `_machine(value)` bị khóa cứng `1 <= number <= 80`. Khi chạy trên Cụm Farm Admin (Máy 201–280), toàn bộ máy bị loại bỏ ngay tại bước freeze target (`NO_ELIGIBLE_TARGETS`).
- **Chuẩn hóa kiến trúc:**
  - Nới lỏng kiểm tra `1 <= number <= 999` cho helper `_machine`.
  - Bổ sung boundary unit tests trong `test_run_batch_live_2fa.py`:
    - Accept: `1`, `80`, `81`, `201`, `280`, `999`.
    - Reject: `0`, `1000`, `"nonnumeric"`, `None`.
  - Bổ sung Telemetry phạm vi cụm tại bước freeze:
    ```python
    kibe_count = sum(1 for t in frozen if int(t.machine) <= 80)
    admin_count = len(frozen) - kibe_count
    print(f"[telemetry:freeze-targets] total={len(frozen)} kibe_targets={kibe_count} admin_targets={admin_count}", flush=True)
    ```

---

## 2. Decouple Watchdog: Chống Chết Chùm Chuỗi Đa Tác Vụ
- **Vấn đề cũ (`post_noon_chain_watchdog.py`):**
  - Khóa lane: Script mặc định `--lane gmail`, và khi `--lane all` thì in dòng chú thích rồi bỏ qua TikTok.
  - Phụ thuộc lỗi (Coupling): Khi Phase Reg Gmail gặp lỗi mạng / platform (`failed`), Phase Add 2FA TikTok bị hủy bỏ toàn bộ.
- **Quy chuẩn Decoupling:**
  - Tách bạch 2 Phase độc lập: Dù Phase 1 (Reg Gmail) trả về `code != 0` hay `failed`, Phase 2 (Add 2FA TikTok) **bắt buộc phải tiếp tục chạy**.
  - Không để lỗi của giai đoạn trước làm tắc nghẽn giai đoạn bảo mật phía sau (Reg fail vẫn phải chạy 2FA).

---

## 3. Phân Lập Dữ Liệu Tuyệt Đối Giữa Các Dàn Farm
- **Dàn Kibe (Máy 1–80):**
  - Workbook: `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`
  - Thực thi cục bộ qua ADB XiaoWei.
- **Dàn Admin (Máy 201–280):**
  - Workbook: `D:\OneDrive\TaadaaData\admin\taikhoan_dat_v2_updated .xlsx`
  - Thực thi remote qua `ssh admin-farm` gọi Python môi trường `D:/Taadaa/python-envs/automation`.
- **Cơ chế ghi an toàn (`core/workbook.py`):**
  - Sử dụng Single-Writer Lock chống xung đột đa tiến trình.
  - Auto-backup file `.backup` có timestamp trước khi ghi cell.
  - Mở lại file kiểm tra (`re-open verify`) trước khi nhả lock.

---

## 4. Tần Suất & Báo Cáo 2 Cấp Độ
1. **Báo cáo Thực thi (Event-driven):**
   - Phân tách số liệu rõ ràng trong nội dung gửi Telegram:
     - `Farm Kibe (Máy 1-80): Hoàn tất X | Bỏ qua Y | Lỗi Z`
     - `Farm Admin (Máy 201-280): Hoàn tất A | Bỏ qua B | Lỗi C`
2. **Báo cáo Thống kê Hàng ngày (Daily 07:00):**
   - Tích hợp trực tiếp vào `tiktok_account_tracker.py` để quét và báo cáo tỷ lệ phủ 2FA của từng dàn:
     - `Bảo mật 2FA Farm Kibe (M1-80): 454/639 nick (71%)`
     - `Bảo mật 2FA Farm Admin (M201-280): 0/614 nick (0%)`
