# Phân Tích Sự Cố Bỏ Quên Gửi Ảnh Kết Quả (MEDIA Evidence Gate Protocol)

Ngày ghi nhận: 12/09/2026.
Tác nhân: Hermes Coordinator & Admin Hermes Bot (@taadaa_admin_hermes_bot).
Chỉ đạo từ User (Tad): "gọi claude cli fix cứng cho t lí do tại sao mỗi phiên làm việc vs automation lại k chịu gửi ảnh như bên admin đang bị".

---

## 1. BỐI CẢNH & HIỆN TƯỢNG SỰ CỐ
- Trên máy Admin (phụ trách đàn máy 200+), sau khi hoàn tất phiên automation chạy máy 246 (M246), bot Admin báo cáo kết quả text nhưng hoàn toàn không gửi ảnh chụp màn hình máy thật.
- User phản ứng gay gắt: *"hình kết quả đâu. t nhớ t lưu rule làm xong gửi hình báo cáo r mà, sao k gửi?"*.
- Bot Admin phản hồi luống cuống: *"Em nhận lỗi nghiêm trọng vì đã quên gửi ảnh kết quả ngay khi xong việc! Em đã gửi trực tiếp toàn bộ ảnh hiện trường thực tế của ca chạy M246... Từ giờ sau bất kỳ ca test/chạy nào, em tuyệt đối tuân thủ rule: Báo cáo luôn luôn phải đi kèm ảnh hiện trường thực tế."*.
- Vấn đề cốt lõi: Hiện tượng này không chỉ xảy ra trên Admin mà xảy ra trên TOÀN BỘ hệ thống (kể cả Kibe lẫn Admin).

---

## 2. NGUYÊN NHÂN GỐC RỄ (CLAUDE OPUS/SONNET AUDIT)

1. **Bẫy điều kiện mềm trong System Prompt (`Optional Loophole`):**
   - Trong `config.yaml` và các prompt cũ, các câu chữ như:
     - *"Khi có yêu cầu ảnh máy N, chụp qua ADB gửi qua MEDIA:."*
     - *"Khi cần gửi ảnh máy N, dùng ADB screencap gửi qua MEDIA:<path>."*
   - Cụm từ *"Khi cần"* hoặc *"Khi có yêu cầu"* tạo ra sự suy diễn tùy chọn cho LLM. Khi LLM thấy task chạy xong và stdout trả về success, nó tối ưu hóa completion và tự động kết luận "lần này chưa cần" nên cắt bỏ bước screencap.

2. **Xung đột phân vai Coordinator vs Worker (`Diffusion of Responsibility`):**
   - **Coordinator** ở session chính tuân thủ luật *"CẤM Coordinator tự chạm máy, cấm ADB tay, chỉ dispatch worker"*, nên Coordinator nghĩ bước gửi ảnh là do Worker làm.
   - **Worker** chạy trong subagent bị cô lập, không có kênh Telegram để gửi cú pháp `MEDIA:`, chỉ lưu ảnh local rồi trả về text tóm tắt.
   - Coordinator nhận kết quả text "SUCCESS" từ Worker liền copy ra báo cáo cho User mà không bốc path ảnh đính kèm `MEDIA:`.

3. **Xung đột Budget:**
   - Khi áp lực budget tool calls (<= 15-20 calls) hoặc giới hạn ký tự báo cáo (<= 1024 ký tự), LLM ưu tiên hoàn thành core logic và xem screencap là việc phụ, sẵn sàng prune bỏ.

4. **Thiếu Checkpoint Nghiệm Thu (Missing Gate):**
   - Hệ thống có Gate 0 (Canary), Gate 1 (Review), Gate 2 (Test)... nhưng hoàn toàn không có Gate bắt buộc kiểm tra sự hiện diện của thẻ `MEDIA:` trước khi gửi tin nhắn kết thúc task.

---

## 3. GIẢI PHÁP FIX CỨNG TRIỆT ĐỂ ĐÃ TRIỂN KHAI

### Tầng 1: Khóa Cứng System Prompt (`config.yaml` & `SOUL.md`)
- Xóa sạch mọi từ *"Khi cần"*, *"Khi có yêu cầu"*.
- Thay bằng quy tắc cứng bắt buộc:
  > `3. BÁO CÁO GỌN & NGHIỆM THU ẢNH (BẮT BUỘC): Chỉ gửi 1 báo cáo cuối (Mục đích -> Kết quả -> Blocker). Các lượt trung gian dùng [SILENT]. MỌI task đụng tới máy N (chạy batch, test, fix lỗi, canary, recovery): Báo cáo kết quả cuối cùng BẮT BUỘC PHẢI ĐÍNH KÈM MEDIA:<path_anh_screencap> ở dòng riêng. Thiếu MEDIA: = VI PHẠM GATE, COI NHƯ CHƯA XONG.`

### Tầng 2: GATE 6 — Media Evidence Gate (`SOUL.md` & `HERMES_SUBAGENT_RULES.md`)
- Bổ sung **GATE 6** vào danh sách các Gate điều phối bắt buộc:
  - Worker có trách nhiệm lưu ảnh screencap local và trả path tuyệt đối trong artifact output.
  - Coordinator bắt buộc kiểm tra path ảnh từ Worker (hoặc tự chụp screencap O(1) qua ADB serial) để đính kèm `MEDIA:<path>` ở dòng riêng biệt.
  - Báo cáo kết quả task farm mà thiếu thẻ `MEDIA:` bị coi là VI PHẠM GATE NGHIỆM THU, TASK CHƯA HOÀN THÀNH.

### Tầng 3: Đồng Bộ Đa Máy (Kibe → Admin)
- Cập nhật bản deploy template tại `D:/Taadaa/Hermes/deploy/hermes-home/config.yaml` và `D:/OneDrive/Taadaa_Sync_Shared/hermes-sync/config.yaml`.
- Đẩy commit lên GitHub (`fork main`).
- Lệnh 1-click để Admin đồng bộ ngay:
  `git -C D:\Taadaa\Hermes pull --rebase fork main && powershell -NoProfile -ExecutionPolicy Bypass -File D:\Taadaa\Hermes\deploy\sync-from-kibe.ps1`
