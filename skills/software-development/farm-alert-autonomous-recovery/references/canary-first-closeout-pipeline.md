# Canary-First Closeout Pipeline & Session Lifecycle Contract

## 1. Bối cảnh & Nguyên Lý Kiến Trúc (Tư Vấn Từ Claude Code CLI)

Trong hệ thống điều phối Taadaa Phone Farm, mâu thuẫn lớn nhất giữa tự động hóa và an toàn vận hành là:
- **Tự động chốt phiên (Auto-Closeout)**: Coi hoàn thành session là push thẳng lên `main` -> Rollout code ra 160 máy khi User chưa nhìn thấy màn hình máy thật, dễ dính False Positive (script báo PASS nhưng màn hình thật bị méo/lỗi/popup mới).
- **Chờ thủ công hoàn toàn (User-Gated thuần)**: Chờ User gõ "chốt" mới chạy Reviewer (`closeout_gate.py`) -> Nếu Reviewer chấm rớt (<85), User bị làm phiền lần 2; đồng thời giữ lock thiết bị và session quá lâu.

### Phân định Session Lifecycle vs Git Lifecycle:
- **Session Lifecycle (Phiên làm việc)**: Tồn tại ngắn, tốn tài nguyên (giữ device lock, chiếm worker). Phải được **giải phóng ngay** sau khi chạy xong kiểm thử.
- **Git Lifecycle (Mã nguồn Farm)**: Bền vững, tác động trực tiếp tới toàn farm. Quyền quyết định "đây là sự thật của farm" thuộc về **User duyệt qua ảnh visual evidence**.
- **Giải pháp Hybrid (Phương án C)**: Tự động hóa mọi bước tạo bằng chứng và có thể hoàn tác (Unit test -> Canary -> Reviewer ngầm -> Commit local). Quyền push remote thuộc về User sau khi xem ảnh.

---

## 2. Pipeline 5 Bước Chuẩn A-Z

```text
BƯỚC 1: SỬA CODE & UNIT TEST FOCUSED (< 30s)
  ↓     Sửa tận gốc (T1 Coordinator O(1) <= 15 dòng hoặc T2 Worker), pass test, commit LOCAL. CẤM push remote.
BƯỚC 2: TỰ ĐỘNG CHẠY CANARY TRÊN MÁY THẬT ĐẠI DIỆN
  ↓     Acquire device lock -> chạy runner -> chụp ảnh MEDIA:<path>.
BƯỚC 3: TỰ ĐỘNG CHẠY WINRT OCR ĐỌC LẠI TEXT TRÊN ẢNH
  ↓     Chỉ kết luận PASS/FAIL dựa trên text OCR đọc được (OCR Readback Gate).
  ↓     NHẢ NGAY DEVICE LOCK sau khi có ảnh và OCR xong (không giữ lock qua Closeout hay vòng tự sửa).
BƯỚC 4: TỰ ĐỘNG CHẠY CLOSEOUT GATE NGẦM (REVIEWER SOL HIGH CHẤM >= 85)
  ↓     Chạy python D:/Taadaa/tools/closeout_gate.py --repo <repo> --base $(git merge-base HEAD '@{u}' 2>/dev/null || git merge-base HEAD origin/main).
  ↓     Nếu >= 85: Sang bước 5. Nếu < 85 hoặc Canary FAIL: tự sửa ngầm (tối đa 3 vòng lặp).
  ↓     Nếu hết 3 vòng vẫn trượt: BẮT BUỘC nhả sạch device lock và session trước khi dừng, báo đúng 1 blocker.
BƯỚC 5: NỘP BÁO CÁO NGHIỆM THU TRỌN GÓI CHO USER (Gửi 1 lần duy nhất)
  ↓     Gồm: Ảnh MEDIA: + Chữ OCR đọc được + Điểm Reviewer + Commit SHA + Diffstat.
  ↓     Trạng thái: device lock: RELEASED, session: RELEASED, push: CHỜ LỆNH USER.
BƯỚC 6: USER DUYỆT ẢNH VÀ PHÁT LỆNH PUSH:
  ├── User gõ "chốt" / "ok" / "done" khi trả lời báo cáo -> Agent mới PUSH remote và đóng phiên.
  └── User bảo "sửa X" -> Quay lại Bước 1 làm tiếp.
```

---

## 3. Bốn Quy Tắc Cứng (Hard Rules)

1. **Trần tối đa 3 vòng tự sửa ngầm & Nhả Lock tức thì**:
   - 1 vòng = 1 chu kỳ Bước 1->3. Trượt = Canary FAIL, điểm Sol < 85 hoặc exit != 0.
   - Khi trượt, Agent tự sửa và chạy lại tối đa 3 vòng lặp.
   - Nhả ngay device lock sau khi Canary xong ở Bước 3. Nếu qua 3 vòng vẫn không đạt, Agent bắt buộc nhả sạch device lock và worker session trước khi dừng, rồi báo cáo đúng 1 blocker duy nhất kèm bằng chứng thực tế, chống lặp vô hạn đốt token hay giữ treo thiết bị.
2. **Sử dụng `git merge-base` chuẩn mực cho Closeout Gate**:
   - Chạy `closeout_gate.py --base $(git merge-base HEAD '@{u}' 2>/dev/null || git merge-base HEAD origin/main)` để Reviewer chấm toàn bộ diff local chưa push so với upstream, tránh sót commit local chưa push và tương thích cú pháp an toàn trên cả PowerShell lẫn Bash (nhờ quote `'@{u}'`).
3. **Ngoại lệ Gate 6 cho Canary**:
   - Quá trình chạy Canary ngầm không bắn spam ảnh vụn vặt; toàn bộ ảnh nghiệm thu thực tế được **gom trọn gói nộp 1 lần** ở Bước 5 cho User.
4. **Phân định ngữ cảnh lệnh Push**:
   - Các từ khóa `chốt`, `chốt phiên`, `done`, `ok` chỉ kích hoạt `git push` khi User đang **trả lời tin nhắn báo cáo nghiệm thu**; cấm tự push khi User nói "ok" ở các ngữ cảnh thảo luận khác.
   - Chỉ push đúng SHA đã báo cáo cho User; nếu có commit mới phát sinh sau báo cáo thì bắt buộc quay lại Bước 2 chạy lại Canary.

---

## 4. Triage & Xử Lý Các Popup Điển Hình

### A. Popup PlayCore Google Play ("TikTok cần tải các tệp bổ sung xuống...")
- **Hiện tượng**: `com.android.vending/PlayCoreAcquisitionActivity` bung modal dialog sau khi switch account, làm văng lỗi `TikTok không trở lại foreground trước ACCOUNT_READY`.
- **Chính sách**: **TUYỆT ĐỐI KHÔNG TẢI**. Tải sẽ ngốn băng thông proxy, tràn bộ nhớ 32GB máy Samsung S7 và kẹt thêm popup Google Play mới.
- **Xử lý tự động**: Quét nút đóng (`"Đóng hộp thoại cập nhật"`, `"Đóng"`, `"Close"` qua text hoặc `content_desc`). Nếu không thấy nút, kích hoạt fallback phím `BACK` để dismiss modal dialog trong 1s, trả focus về TikTok an toàn.

### B. Popup Milestone Chúc Mừng Lượt Thích / Bạn Đang Nghĩ Gì
- **Hiện tượng**: `open_switcher` văng lỗi `SWITCHER_NOT_CONFIRMED: switcher markers were not confirmed` do popup *"Bạn có tin vui? ... đã nhận tổng cộng N lượt thích cho tất cả video [OK]"* che khuất Profile Header.
- **Xử lý tự động**: Gọi `_dismiss_simple_close_popup` trước khi mở switcher để tự động tap `OK` / `Xong` giải phóng Profile Header.
