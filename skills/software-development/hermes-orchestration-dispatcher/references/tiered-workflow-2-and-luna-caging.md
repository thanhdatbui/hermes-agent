# Quy Chuẩn Tiered Workflow 2.0 & Cấu Hình Model Worker (Taadaa Farm)

## 1. Phân Tầng Vận Hành Thực Chiến
- **T0 (Hiện trường / Read-only / Ops O(1)):**
  - Chẩn đoán ADB, `inspect_machine.py <N>`, kill process, đọc log O(1), restart script.
  - Gemini Coordinator tự làm 100% (5–15s). CẤM quét đĩa diện rộng (`grep -r`, `os.walk`, `find`).
- **T1 (Vá hiện trường ốc lỏng <= 15 dòng):**
  - Chữa cháy: đổi tọa độ click, đổi selector text do UI drift, tăng timeout, thêm `try/except`, thêm `if... continue`.
  - Gemini Coordinator ĐƯỢC PHÉP TỰ SỬA TRỰC TIẾP O(1) nếu:
    1. Đúng 1 file duy nhất.
    2. Tổng diff (thêm + xóa) <= 15 dòng (theo `git diff --numstat`).
    3. Không đổi signature, không thêm dependency, không refactor.
    4. BẮT BUỘC Canary Gate trên 1 máy thật (chụp ảnh `MEDIA:`, log ADB sạch).
- **T2 (Thi công lớn / Kiến trúc > 15 dòng hoặc chạm watchdog/lock/semaphore):**
  - BẮT BUỘC qua `delegate_task`: Terra High lên bản vẽ (3–5s) chốt anchor $c==1 \rightarrow$ Luna High thi công trong Lồng Vô Trùng (`cage_gate.py`).

## 2. Kỷ Luật Worker Luna High (Chống Tê Liệt & Bịa Diff)
- **Model ghim cứng:** `cx/gpt-5.6-luna-high` (Codex qua OmniRoute :20129).
  - *Lưu ý cấu hình:* Phải dùng alias `cx/gpt-5.6-luna-high` thay vì `codex/gpt-5.6-luna-high` trong `delegation.model` của `config.yaml` để tránh Hermes hiểu nhầm `codex/` là provider rồi fallback ngầm về Gemini.
- **Tước quyền khóc nhè:**
  - CẤM viết văn bản giải trình, đề xuất kiến trúc ngoài lề. Báo cáo dài dòng bị hủy bỏ ngay.
  - Nếu gặp bế tắc thật sự (anchor chết / spec mâu thuẫn): CHỈ ĐƯỢC PHÉP TRẢ ĐÚNG 1 DÒNG DUY NHẤT:
    `BLOCKED:<MÃ_LÝ_DO>:<Mô tả ngắn gọn <= 120 ký tự>`
  - Hệ thống xử lý như timeout: đá văng ra ngay để chuyển việc cho Gemini/Terra, không cho ngâm việc.
- **Chống bịa diff:** Nộp diff bịa làm rớt Canary máy thật bị xử phạt nặng hơn cả việc báo BLOCKED thật thà.

## 3. Chốt Chặn Vật Lý Bắt Buộc (Hard Gates)
- **Anti-Multi-File:** Đặt tại dòng đầu tiên của hook dispatch (`D:/Taadaa/tools/hooks/guard_dispatch_contract.py`). Bất kỳ lệnh `delegate_task` nào chứa $\ge 2$ file code nghiệp vụ đều bị BLOCK ngay lập tức.
- **Closeout Gate:** Kết thúc phiên bắt buộc chạy `python D:/Taadaa/tools/closeout_gate.py --repo <path> --base HEAD~1 --json-output` được GPT-5.6 Sol High chấm điểm $\ge 85/100$ mới được phép đóng phiên.
