# Dual-Cluster Farm Alert Scope & O(1) Upload Failure Triage

## 1. Bối Cảnh & Vấn Đề Người Vận Hành Chất Vấn

Khi Watchdog phát cảnh báo đỏ diện rộng:
```text
🚨 [FARM ALERT] PHÁT HIỆN LỖI SCRIPT HÀNG LOẠT (10 máy lỗi script Upload) - Ca 3 - Phiên 1/2 (Tối) (Row 6)

🏢 【FARM KIBE - MÁY 1-80】
• Tổng máy xử lý: 80 máy
...
• Đăng Video (1/2 - 47 video đã đăng):
  + Success (47): ...
  + Timeout/Quá giờ (0): Không có
  + Lỗi script/xác minh (10): 8, 18, 28, 29, 47, 48, 54, 58, 61, 74
  + Bỏ qua (21): Đang dưỡng sinh (21)
```

**Câu hỏi thường gặp từ người vận hành:** *"10 máy lỗi trên tổng farm hay sao?"*

**Nguyên nhân gây hiểu lầm:**
1. Tiêu đề `[FARM ALERT]` ghi tổng số máy lỗi gộp nhưng không ghi rõ tên cụm trong header nếu chỉ có 1 cụm phát sinh lỗi hoặc chỉ có 1 cụm tham gia chạy phiên đó.
2. Farm gồm 2 cụm độc lập:
   - **Cụm Kibe (Máy 1–80)**: 80 máy.
   - **Cụm Admin (Máy 201–280)**: 80 máy.
   - **Tổng toàn Farm**: 160 máy.
3. Khi Cụm Admin không có lượt chạy (hoặc chưa chạy Row tương ứng), chỉ có khối `🏢 【FARM KIBE - MÁY 1-80】` xuất hiện trong tin nhắn. Người vận hành dễ hoang mang không rõ 10 máy là trên 80 máy, trên 160 máy, hay trên số máy thực tế cần đăng video.

---

## 2. Quy Tắc Phân Định Scope Cho Điều Phối Viên (Coordinator)

Khi trả lời hoặc phân tích cảnh báo Farm Alert:
1. **Xác định cụm xuất hiện trong báo cáo**:
   - Nếu tin nhắn chỉ có khối `🏢 【FARM KIBE - MÁY 1-80】` -> Khẳng định ngay: **Chỉ tính trên Cụm Kibe**, không phải trên toàn bộ 160 máy cả farm.
   - Kiểm tra nhanh thư mục runtime: `D:/Taadaa/runtime/admin/live/<date>/row-<R>-<time>` để xác nhận Admin có chạy hay không.
2. **Làm rõ Mẫu số (Denominator)**:
   - Tổng máy cụm: 80 máy.
   - Máy dưỡng sinh (Organic Rest): ví dụ 21 máy (chỉ lướt feed, không đăng video).
   - Máy thực tế cần đăng: `80 - 21 = 59 máy`.
   - Thành công: 47 máy (~80%).
   - Lỗi: 10 máy (~17% số máy tham gia đăng).

---

## 3. Quy Trình Điều Tra O(1) Lỗi Upload Hàng Loạt (Tuyệt Đối Cấm Quét Đĩa Diện Rộng)

Theo **Farm Safety Invariants**, cấm tuyệt đối dùng `os.walk`, `glob(recursive=True)`, `find`, `grep -r`, hoặc `search_files` quét diện rộng.

### Bước truy xuất O(1) trực tiếp:
Từ tên thư mục phiên (ví dụ `row-6-180026`) tìm được thư mục con run (chỉ chứa 1 run id dạng `20261002-180309`):
1. Đường dẫn trực tiếp của từng máy lỗi:
   `D:/Taadaa/runtime/<cluster>/live/<date>/<row_dir>/<run_id>/machines/machine_<M>/<run_id>/upload_result.json`
2. Đọc trực tiếp trường `reason` và `status` bằng snippet Python có timeout hoặc lệnh focused:
   ```python
   import json, os
   error_machines = [8, 18, 28, 29, 47, 48, 54, 58, 61, 74]
   base_dir = r"D:\Taadaa\runtime\kibe\live\2026-10-02\row-6-180026\20261002-180309\machines"
   for m in error_machines:
       p = os.path.join(base_dir, f"machine_{m}", "20261002-180309", "upload_result.json")
       if os.path.exists(p):
           with open(p, "r", encoding="utf-8") as f:
               d = json.load(f)
               print(f"M{m}: {d.get('reason')}")
   ```

---

## 4. Phân Loại 4 Cụm Nguyên Nhân Lỗi Upload Thực Chiến

Khi bóc tách danh sách máy lỗi upload, phân loại rõ ràng thành 4 nhóm để người vận hành nắm chính xác bản chất:

1. **Nhóm Fail-Closed Post-Verification (`POST_SUBMISSION_UNKNOWN`)**:
   - *Triệu chứng*: `post_submission_state=UNKNOWN: không có bằng chứng TikTok ACCEPTED submission; không được ghi workbook hay báo success (COMPAT-POST-VERIFY-004)`.
   - *Bản chất*: **Đây là chốt an toàn có chủ đích, KHÔNG phải script crash hay exception**. Video đã hoàn tất các khâu tải và bấm nút Đăng, nhưng TikTok load chậm hoặc popup không bắt được màn hình xác nhận bài đăng thành công. Script từ chối ghi PASS vào workbook để chống ghi khống dữ liệu.
2. **Nhóm Lỗi Chuyển Đổi Tài Khoản (`ACCOUNT_SWITCHER_FAILED`)**:
   - *Triệu chứng*: `open_switcher failed: SWITCHER_NOT_CONFIRMED: switcher markers were not confirmed`.
   - *Bản chất*: Không mở được menu Switcher chuyển tài khoản. Thường do vướng popup onboarding, thông báo hệ thống, hoặc phiên TikTok bị văng về màn hình chưa đăng nhập.
3. **Nhóm Kẹt Luồng Navigation / Picker (`VIDEO_PICK_*`)**:
   - *Triệu chứng*: Kẹt tại `VIDEO_PICK_PROFILE_VIDEO_ACTION_SHEET` hoặc `VIDEO_PICK_HOME_NOT_REACHED` (quá budget 60s không đạt Home root).
   - *Bản chất*: Giao diện TikTok bị lag hoặc pop-up che khuất nút Home/Create (+).
4. **Nhóm Lỗi Phần Cứng / Kết Nối (`PREFLIGHT_VPN_BLOCKED` / Device Offline)**:
   - *Triệu chứng*: `device offline or ADB/USB disconnected`.
   - *Bản chất*: Lỏng cáp USB, hub USB ngắt kết nối hoặc ADB transport bị nghẽn socket.

---

## 5. Quy Chuẩn Báo Cáo Phản Hồi Cho Người Vận Hành

Cấu trúc câu trả lời chuẩn khi nhận chất vấn về lỗi diện rộng:
1. **Khẳng định ngay phạm vi**: Nêu rõ lỗi chỉ xảy ra trên Cụm Kibe (1–80) hay toàn Farm (160 máy), và tình trạng của cụm còn lại.
2. **Thống kê tỷ lệ thực**: Bóc tách rõ số máy dưỡng sinh (không up), số máy tham gia up, số máy thành công và số máy lỗi.
3. **Phân rã chi tiết nguyên nhân**: Phân loại theo 4 nhóm trên, giải thích rõ nhóm nào là chốt an toàn fail-closed (`POST_SUBMISSION_UNKNOWN`) để người vận hành không hiểu nhầm là bot bị hỏng toàn bộ.
