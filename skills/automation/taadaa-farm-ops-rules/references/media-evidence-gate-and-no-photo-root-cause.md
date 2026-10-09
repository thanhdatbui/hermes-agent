# Case Study: Sự Cố Thiếu Ảnh Báo Cáo Automation và Cơ Chế Khóa Cứng Invariant Media Gate

Ngày ghi nhận: 12/09/2026.
Hệ thống: Hermes Multi-Agent (Kibe Worker & Admin Coordinator) & Taadaa Phone Farm.

---

## 1. HIỆN TƯỢNG VÀ SỰ CỐ
- Trên kênh chat Telegram của bot Admin (`@taadaa_admin_hermes_bot`), sau khi hoàn tất ca chạy/test automation trên thiết bị M246, bot trả về tin nhắn kết quả văn bản nhưng **HOÀN TOÀN KHÔNG GỬI ẢNH HIỆN TRƯỜNG KẾT QUẢ**.
- User (Tad) bức xúc chất vấn:
  > *"hình kết quả đâu. t nhớ t lưu rule làm xong gửi hình báo cáo r mà. sao k gửi?"*
- Bot Admin sau đó luống cuống nhận lỗi và gửi bù 4 ảnh.
- Vấn đề có tính lặp lại mang tính hệ thống trên cả 2 máy (Kibe lẫn Admin), các agent thường xuyên "quên" hoặc lười gửi ảnh kết quả dù quy tắc đã được nhắc nhiều lần.

---

## 2. NGUYÊN NHÂN GỐC RỄ (CLAUDE CODE CLI ANALYSIS)

Qua phân tích chuyên sâu của Claude Code CLI (`claude -p`), 4 tử huyệt kỹ thuật được xác định:

1. **Bẫy điều kiện mềm trong System Prompt (Optional Loophole):**
   - Các chỉ thị trong `config.yaml` và `SOUL.md` dùng từ ngữ mang tính điều kiện:
     - *"Khi cần gửi ảnh máy N, dùng ADB screencap gửi qua MEDIA:<path>."*
     - *"Khi có yêu cầu ảnh máy N..."*
   - LLM luôn tối ưu hóa chi phí token và completion. Khi automation trả về output text thành công, LLM tự suy luận rằng *"Lần này không có yêu cầu cụ thể nên chưa cần gửi ảnh"* và tự động drop/prune bước capture/gửi ảnh.

2. **Khuếch tán trách nhiệm giữa Coordinator và Worker (Diffusion of Responsibility):**
   - **Coordinator (Session chính):** Ràng buộc cấm chạm máy/cấm lệnh ADB ngoài, chỉ đọc log và dispatch worker -> nghĩ rằng Worker chạy automation sẽ tự gửi ảnh.
   - **Worker (Subagent):** Chạy độc lập trong terminal, không có access trực tiếp vào adapter Telegram để bắn `MEDIA:`, chỉ lưu ảnh ra đĩa rồi trả text summary.
   - Kết quả: Không ai gửi ảnh lên chat. Coordinator copy text summary của Worker rồi báo cáo hoàn thành.

3. **Xung đột mục tiêu và áp lực tiết kiệm Budget (Goal Conflict):**
   - Ràng buộc báo cáo ngắn gọn (<= 1024 ký tự) và budget giới hạn (<= 15-20 tool calls) khiến LLM xem bước capture/upload ảnh là "nice-to-have" và ưu tiên loại bỏ đầu tiên khi sắp cạn budget.

4. **Thiếu chốt chặn nghiệm thu cứng (Missing Enforcement Point / Gate):**
   - Hệ thống có Gate 0 (Canary), Gate 1 (Review), Gate 2 (Test)... nhưng không có validator nào chặn việc đóng phiên khi tin nhắn báo cáo thiếu thẻ `MEDIA:<path>`.

---

## 3. GIẢI PHÁP KHÓA CỨNG: INVARIANT MEDIA EVIDENCE GATE

### A. Xóa bỏ hoàn toàn ngôn từ tùy chọn
- Tuyệt đối CẤM các từ: *"Khi cần"*, *"Nếu có yêu cầu"*, *"Khi phù hợp"*.
- Thay bằng: **LUÔN LUÔN, MỌI TASK CHẠM THIẾT BỊ, KHÔNG CÓ NGOẠI LỆ.**

### B. Phân định rõ ràng trách nhiệm
1. **Worker (MEDIA OWNER):**
   - Là chủ sở hữu tuyệt đối việc capture ảnh hiện trường ngay sau khi chạy xong automation (thành công hay thất bại).
   - Bắt buộc trả về đường dẫn file ảnh tuyệt đối (`absolute_path`) trong kết quả bàn giao.
2. **Coordinator (MEDIA VERIFIER & DELIVERER):**
   - Nhận artifact ảnh từ Worker (hoặc tự lấy screencap O(1) theo serial thiết bị nếu script ngoài không bàn giao).
   - BẮT BUỘC nhúng tag `MEDIA:<đường_dẫn_tuyệt_đối>` vào tin nhắn báo cáo cuối cùng gửi User.
   - **Hard Reject:** Báo cáo automation mà THIẾU thẻ `MEDIA:` = VI PHẠM GATE NGHIỆM THU, TASK CHƯA HOÀN THÀNH.
