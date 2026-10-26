# Batch Alert: Opportunistic Upload Hook Video Pick Create Entry False Positive Triage

## 1. Triệu Chứng & Mẫu Cảnh Báo (Symptom & Alert Pattern)
Khi nhận cảnh báo batch hệ thống trên farm:
```text
🚨 [BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG - 【FARM ADMIN - MÁY 201-280】
• Quy trình / Script: Nuôi Acc / Lướt Feed (tiktok-luot nuoi acc)
• Quy mô batch: 78 máy | Thành công: 0 | Thất bại: 78
• Tổng tỷ lệ thất bại toàn batch: 100.0% (78/78 máy)
• Số cụm lỗi hệ thống: 1

📋 CHI TIẾT LỖI VƯỢT NGƯỠNG KÉP (RATE & COUNT):
❌ Signature: UploadScriptError:UploadHook: [MANUAL_REVIEW] [VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Recaptured surface did not prove a labelled bottom-centre create control
   - Tỷ lệ trên toàn batch: 94.9% (74/78 máy)
   - Tỷ lệ trong số máy lỗi: 94.9% (74/78 máy lỗi)
   - Danh sách máy: M201, M202, ...
```

## 2. Phân Tích Cơ Chế Gốc (Root Cause Analysis)
- **Cơ chế Opportunistic Upload trong ca Nuôi Acc:** Cuối ca lướt feed (`tiktok-luot nuoi acc`), runner tự động gắn cờ `--allow-upload-hook` để kích hoạt đăng video cơ hội.
- **Fail-closed ở bước Create (+):** Khi thiết bị kết thúc lướt feed và chuyển sang upload video, nếu TikTok ở trạng thái giao diện chưa hiển thị nút Tạo (+) ở đáy trung tâm (ví dụ đang ở màn hình khác, hoặc layout điều hướng không khớp thẻ XML), state machine kích hoạt recovery và fail-closed an toàn với signature:
  `[MANUAL_REVIEW] [VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Recaptured surface did not prove a labelled bottom-centre create control`
- **Batch Aggregator Gom Lỗi Hệ Thống:** Do gần như toàn bộ cụm máy cùng gặp điều kiện này khi kết thúc phiên nuôi, `batch_aggregator.py` tổng hợp thành lỗi lan rộng vượt ngưỡng kép (rate > 10% & count >= 3).
- **Thực tế tài khoản & thiết bị:** Đây là hành vi fail-closed của riêng bước upload video sau ca nuôi; tài khoản TikTok hoàn toàn không bị checkpoint, không mất phiên, không dính CAPTCHA. Các máy sau ca nuôi đều tự dọn dẹp về `LauncherActivity` (Home screen) và tắt màn hình nghỉ ngơi an toàn.

## 3. Quy Trình Kiểm Chứng Hiện Trường O(1)
1. Tuyệt đối không quét đĩa diện rộng để tìm log/artifact (`search_files`, `os.walk`, `find`).
2. Chạy kiểm tra O(1) trên 1–3 máy đại diện bằng công cụ chuyên dụng:
   ```bash
   python D:/Taadaa/tools/inspect_machine.py <N>
   ```
3. Xác nhận 3 điều kiện an toàn:
   - `Current Focus`: `com.sec.android.app.launcher.activities.LauncherActivity` (hoặc TikTok đã đóng sạch).
   - Màn hình: `OFF (Sleep/Dozing)` hoặc nghỉ bình thường.
   - Wi-Fi IP & Proxy hoạt động ổn định, pin sạc bình thường.
4. **Kết luận dứt khoát:** BÁO ĐỘNG GIẢ (FALSE POSITIVE) về mặt vận hành tài khoản. Toàn bộ nick an toàn 100%.

## 4. Kỷ Luật Phản Hồi Operator
- Khẳng định ngay ở câu đầu tiên: BÁO ĐỘNG GIẢ, tài khoản và thiết bị an toàn 100%, không mất phiên, không dính CAPTCHA.
- Nêu rõ nguyên nhân do hook upload cơ hội sau ca nuôi gặp kiểm tra nút Tạo (+) fail-closed, không phải lỗi văng nick hay hỏng cụm máy.
- Báo cáo trạng thái hiện trường ngắn gọn (focus Home, màn hình tắt, pin/proxy tốt).
