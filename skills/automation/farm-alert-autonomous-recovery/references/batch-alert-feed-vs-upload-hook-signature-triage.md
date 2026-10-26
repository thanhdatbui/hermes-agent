# Batch Alert: Nuôi Acc / Lướt Feed vs UploadHook Signature Triage

## 1. Triệu Chứng & Mẫu Cảnh Báo Gây Bối Rối (Symptom & Confusion Matrix)
Khi nhận cảnh báo batch:
```text
🚨 [BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG - 【FARM ADMIN / KIBE】
• Quy trình / Script: Nuôi Acc / Lướt Feed (tiktok-luot nuoi acc)
• Quy mô batch: 78 máy | Thành công: 0 | Thất bại: 78
❌ Signature: UploadScriptError:UploadHook: [MANUAL_REVIEW] [VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Recaptured surface did not prove a labelled bottom-centre create control
```
- **Nghịch lý nhận thức của Operator:** Tên script hiển thị là `Nuôi Acc / Lướt Feed (tiktok-luot nuoi acc)` nhưng signature lại là `UploadScriptError:UploadHook`, gây hiểu nhầm là lỗi nuôi nick hoặc tài khoản gặp sự cố nghiêm trọng toàn fleet.

## 2. Bản Chất Kỹ Thuật (Architecture & Root Cause)
1. **Cơ chế Opportunistic Upload Hook:**
   - Trong `tiktok_runner.py` và `run-feed-session.ps1`, cờ `-AllowUploadHook` được kích hoạt để tận dụng thời điểm sau khi lướt feed xong nhằm đăng video bổ sung (`scripts.tiktok_workflow.run_post`).
   - Pha Lướt Feed: **ĐÃ HOÀN TẤT THÀNH CÔNG 100%** (số swipe hoàn thành, tương tác tự nhiên bình thường).
2. **Cơ chế Fail-Closed của Upload Hook:**
   - Khi script upload mở TikTok, hàm `_find_bounded_create_button` tìm kiếm nút Tạo (+) ở vị trí chuẩn (`0.40 <= center_x <= 0.60`, `center_y >= 0.88 * height`).
   - Nếu màn hình TikTok sau ca feed đang ở tab khác hoặc giao diện biến thể, script không xác nhận được nút Tạo và kích hoạt `[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED]`.
   - Script chủ động fail-closed: dọn Recent Apps, đưa thiết bị về màn hình chính (`LauncherActivity`), tắt màn hình (`Sleep/Dozing`) và nhả lock an toàn.
3. **Cơ chế Batch Aggregator:**
   - `batch_aggregator.py` tổng hợp từ `upload_result.json` trong thư mục artifact của feed session.
   - Do 100% máy trong batch đều trả về cùng chữ ký fail-closed này, ngưỡng kép (rate & count) bị kích hoạt và phát cảnh báo gán theo tên root script (`tiktok-luot nuoi acc`).

## 3. Quy Trình Đối Soát Hiện Trường O(1)
1. Kiểm tra nhanh máy đại diện bằng lệnh O(1):
   ```bash
   python D:/Taadaa/tools/inspect_machine.py <N>
   ```
2. Xác nhận 3 điều kiện an toàn:
   - Current Focus: `LauncherActivity` (Home screen sạch sẽ).
   - Màn hình: `OFF (Sleep/Dozing)` hoặc nghỉ an toàn.
   - Tài khoản và thiết bị: Không kẹt trong TikTok, không có popup cảnh báo, không dính checkpoint/captcha.

## 4. Kỷ Luật Trả Lời Operator (Bottom-line First)
- **Khẳng định ngay lập tức bản chất:** Xác nhận rõ ràng: **Ca nuôi nick (Lướt Feed) đã hoàn tất thành công 100%**. Lỗi phát sinh từ **bước phụ Đăng video (Upload Hook)** chạy kèm ở cuối phiên.
- **Hiện trạng máy & nick:** Toàn bộ máy và nick an toàn tuyệt đối, máy đã dọn dẹp về Home và tắt màn hình nghỉ ngơi.
- **Hành động tiếp theo:** Không can thiệp thủ công lên thiết bị đang nghỉ; kiểm tra lại cấu hình video render hoặc layout camera trên cụm máy nếu cần chạy ca upload chuyên dụng.
