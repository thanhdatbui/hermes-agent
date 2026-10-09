# Kỷ luật Gate 6 & Chống spam Media Evidence khi trao đổi Hạ tầng / Điện

## 1. Nguyên nhân gốc rễ (Root Cause)
- Quy tắc GATE 6 trước đây phát biểu quá rộng: *"MỌI task đụng tới thiết bị/farm..."*.
- Thuật ngữ "đụng tới" khiến Coordinator AI nhầm lẫn giữa:
  - **Context hội thoại (Discussion / Troubleshooting)**: Bàn luận về hạ tầng, nguồn điện, UPS, ổ cắm, phân tích hiện tượng sụt áp.
  - **Hành động thực thi can thiệp (Action Execution)**: Trực tiếp chạy batch, test tap UI, fix handler, canary, recovery trên máy.
- Hệ quả: Khi đang trao đổi lý thuyết hoặc bàn về hạ tầng điện, Coordinator máy móc chạy ADB `exec-out screencap` trên điện thoại Samsung S7. Do máy đang ngủ/tắt màn hình (`mWakefulness=Dozing`), ảnh chụp ra đen ngòm vô nghĩa và bị spam liên tục vào chat gây ức chế cho người dùng.

---

## 2. Quy tắc kích hoạt chuẩn: Action Verb + Artifact (Tư vấn từ Claude CLI)
GATE 6 **CHỈ ĐƯỢC PHÉP KÍCH HOẠT** khi thỏa mãn đồng thời:
1. **[A] Action Verb**: Có hành động can thiệp vật lý/thực thi thực tế đã chạy trên thiết bị (run batch, run canary, reboot device, tap UI, fix test script).
2. **[B] Artifact Output**: Có artifact, log hoặc trạng thái UI mới cần kiểm chứng nghiệm thu.
3. **[C] Reporting Context**: Response là báo cáo nghiệm thu kết thúc task.

### Bảng phân định ranh giới:

| Loại tác vụ | Có can thiệp máy? | Có kích hoạt GATE 6 (MEDIA:)? | Hành vi chuẩn |
|---|---|---|---|
| **Tư vấn / Thảo luận Hạ tầng / Điện / UPS** | KHÔNG | ❌ **CẤM TUYỆT ĐỐI** | Trả lời text/bảng phân tích, KHÔNG gọi ADB screencap |
| **Phân tích nguyên nhân lý thuyết / Hỏi đáp** | KHÔNG | ❌ **CẤM TUYỆT ĐỐI** | Trả lời phân tích, KHÔNG gửi ảnh |
| **Monitoring thụ động (đọc log, uptime, devices)** | KHÔNG | ❌ **KHÔNG** | Trích xuất text log/uptime O(1) |
| **Nghiệm thu chạy Batch (Feed, Up video, Reg, 2FA)** | CÓ | ✅ **BẮT BUỘC** | Đính kèm `MEDIA:<path>` màn hình thực thi |
| **Canary test / Fix lỗi UI / Recovery thiết bị** | CÓ | ✅ **BẮT BUỘC** | Đính kèm `MEDIA:<path>` màn hình sau khi xử lý |

---

## 3. Quy tắc an toàn màn hình Dozing / Sleep
- Tuyệt đối không chụp màn hình gửi đi khi máy đang ở trạng thái `mWakefulness=Dozing` hoặc màn hình tắt (`bright=0`), vì ảnh xuất ra sẽ là **tấm ảnh đen ngòm**.
- Khi bắt buộc phải nghiệm thu thiết bị thực tế, kiểm tra màn hình và chỉ gửi khi UI có nội dung hiển thị rõ ràng.
