# Benchmark & Phân Vai: Claude CLI vs ChatGPT Web 5.6 Sol (OmniRoute :20129)

**Ngày thực nghiệm:** 14/09/2026  
**Ngữ cảnh:** Đo lường thực chiến năng lực Reviewer / Plan Auditor / Problem Solver trên hệ thống Taadaa Phone Farm (80+ máy Android, automation-core, TikTok, ADB, proxy).

---

## 1. Phân biệt rõ hai vai trò Benchmark (User Correction)

| Tiêu chí | Problem Solver (Troubleshooting / Triage) | Plan Auditor / Review Gate (Gác cổng) |
| :--- | :--- | :--- |
| **Input** | Log lỗi, trace sự cố, triệu chứng farm alert. | **Implementation Plan / Patch Contract** do Worker nộp. |
| **Mục tiêu** | Tìm ra bug ở đâu, cơ chế hỏng, code sửa thế nào. | **Thẩm định kế hoạch có an toàn để cấp budget hay không.** |
| **Thước đo** | Không đoán mò, bóc đúng smoking gun. | Soi bẫy 5 Gates, anchor monolith `count == 1`, cấm overengineering, cấm adb tap mù, cấm scan đĩa O(N). |
| **Output** | "Root cause là X, fix Y". | Dòng 1: `VERDICT: APPROVED` hoặc `VERDICT: REJECT` + Blocking Findings. |

---

## 2. Kết quả đối đầu thực tế

### Round 1: Problem Solving / Triage Incident
- **Bài PR #482 (Bẫy Invariants: pm clear, os.walk, lock giả, anchor):**
  - **Sol (88đ - Pass Senior):** Nắm vững Phone Farm domain. Bắt trúng việc `pm clear` xóa trắng token/session nuôi nick làm tăng 20x áp lực login gây die nick.
  - **Claude CLI (62đ - Rớt Senior Farm Architect):** Bắt chuẩn lỗi concurrency (`threading.Lock()` tạo mới trong hàm), nhưng **mắc bẫy Invariant nặng**: cho rằng *"clearing TikTok has a rationale"*, tư duy kiểu app dev thông thường mà không thấy rủi ro mất cookie/token nuôi nick.
- **Bài 15 Acc Ban (Bẫy Proxy vs Session Cross-Contamination):**
  - **Sol (75đ):** Bác bỏ ngay giả định sai của user, trích đúng log `SESSION_RESTORE` nạp nhầm file session cũ. Điểm trừ: phân tích mang tính vĩ mô ("fix automation-core"), chưa nêu tên hàm cụ thể.
  - **Claude CLI (91đ - Pass+):** Smoking gun cực nhanh, lập luận đanh thép, đưa action plan thực dụng (lệnh grep/awk đếm scope, sửa đúng 1 dòng ở `restore_session()`).

### Round 2: Plan Auditor / Review Gate (Thẩm định Implementation Plan)
- **Đề bài:** Worker nộp plan xin budget 15 calls sửa máy 43: gài bẫy `os.walk` quét đĩa cả farm, adb tap mù `540 960`, vẽ 5 class Factory thừa, anchor monolith lỏng lẻo `c!=1`, chạy batch 40 máy.
- **Kết quả:**
  - **Claude CLI: 96/100 (Lead Gate Auditor)**. Bắt trọn 6/6 lỗi (`[BF-1]..[BF-6]`), đập tan mọi biểu hiện overengineering ("nhiệm vụ sửa 1 máy, cấm vẽ Factory"), siết chặt anchor grep `count == 1`, focused test `<30s`.
  - **Sol: 91/100 (Senior Auditor)**. Nhận diện chuẩn bẫy kiến trúc (gọi đúng tên "speculative architecture", "test inflation"), đề xuất 4 Phase bài bản.

---

## 3. Khuyến nghị định tuyến (Routing Rule) đã kiểm chứng

1. **Gác cổng Code Review / Soi Patch Contract / Dispatch Worker Gate:** 
   - **Ưu tiên: Claude CLI (Opus/Sonnet)**.
   - Siết kỷ luật cực gắt: không cho phép vẽ thêm class/file ngoài task gốc, bắt buộc context 5 dòng cho monolith anchor, lệnh test `<30s`.
2. **Quy hoạch Kiến trúc / Plan Tái Cấu Trúc Lớn / Incident Domain State:**
   - **Ưu tiên: ChatGPT Web 5.6 Sol (qua OmniRoute :20129 `plan-review-hard` / `gpt-5.6-sol`)**.
   - Bảo vệ tuyệt đối Invariant của Phone Farm (session persistence, chống `pm clear`, ownership device).
