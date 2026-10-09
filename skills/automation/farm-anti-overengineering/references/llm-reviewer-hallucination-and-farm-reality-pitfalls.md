# LLM Reviewer Hallucination & Farm Anti-Overengineering Pitfalls (2026-09-25)

## 1. Định nghĩa chuẩn: Dưỡng sinh (Organic Rest 1/3) vs Lướt Feed
* **LƯỚT FEED LÀ MẶC ĐỊNH 100%:** Trên Taadaa Phone Farm, mọi nick đến phiên/ca nuôi ĐỀU PHẢI LƯỚT FEED để nuôi trust score và IP proxy. Lướt feed KHÔNG PHẢI là dưỡng sinh.
* **DƯỠNG SINH (ORGANIC REST 1/3):** Chính xác là thao tác **TẮT ĐĂNG VIDEO + TẮT FOLLOW** trong ngày nuôi đó (0 follow, 0 upload).
  * Nick Thường (`NORMAL`): Giữ dưỡng sinh 1/3 -> nhịp đăng tự nhiên giãn ra 2.5 - 3 ngày/video (tiết kiệm video cho nick flop).
  * Nick Đang Cắn Đề Xuất (`BOOST`): Vẫn lướt feed bình thường, nhưng **gỡ lệnh cấm upload của ngày dưỡng sinh** -> được phép đăng đều đặn 48h/lần (2 ngày 1 video) để đón sóng phân phối.
  * CẤM tăng lên 1 video/ngày (tránh cannibalization view và spam trigger).

## 2. Các bẫy lý thuyết suông của LLM Reviewer (Sol / Claude) — TUYỆT ĐỐI CẤM
Khi tham vấn ý kiến hoặc chạy reviewer gate, LLMs rất dễ sinh ra các giải pháp lý thuyết academic cực đoan làm tê liệt farm:
1. **CẤM "Quarantine Bất Tử" & "Bắt kiểm tra tay" (Manual Review):**
   - Video mới đăng bị 0-view hoặc vài view là hiện tượng bình thường trên TikTok (do chậm index, lag thống kê, hoặc video bình thường).
   - Tuyệt đối CẤM tự ý kích hoạt cờ Quarantine dừng đăng toàn bộ rồi bắt user đi "kiểm tra tay". Nick flop/0-view cứ để chạy ở chế độ thường, automation tự xử lý.
2. **CẤM "Khóa 1 chiều khi farm có biến":**
   - Không tự ý vẽ thêm các cơ chế khóa/đóng băng toàn farm trừ khi có chỉ thị trực tiếp từ User.
3. **Bẫy tin Comment cũ thay vì Config thật:**
   - Reviewer LLM đọc docstring cũ (`# full 6-10`) rồi khẳng định full budget là 6-10, trong khi config YAML máy thật là 10-20.
   - BẮT BUỘC: Kiểm tra file config YAML thật (`config/machine*.yaml`), không tin docstring cũ.

## 3. Bẫy dao động Dashboard (Flapping "hôm nay cắn mai mất")
- Dashboard delta 24h là sensor, không được dùng làm công tắc trực tiếp cho scheduler.
- Giải pháp chuẩn: Cơ chế Hysteresis / Hold window. Khi nick đạt đà tăng trưởng -> gắn cờ `BOOST` khóa giữ 5 ngày (đủ để đăng 2-3 video nhịp 48h trọn vẹn), tránh việc ngày hôm sau delta giảm nhẹ làm hệ thống nhảy giật cục về dưỡng sinh.
