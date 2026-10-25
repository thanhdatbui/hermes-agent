# Đối Soát Định Lượng Payload, Tools Schema & Trùng Lặp Tri Thức (Audit 25/10/2026)

## 1. Phương Pháp Truy Vết Thực Tế O(1)
Để đối soát chính xác những gì Hermes gửi sang OmniRoute mà không vi phạm Guard quét đĩa:
- Thư mục chứa call log thật: `C:\Users\Kibe\.omniroute\call_logs\<YYYY-MM-DD>\`
- Lấy file mới nhất:
  ```python
  import json, os
  p = 'C:/Users/Kibe/.omniroute/call_logs/2026-10-25'
  f = sorted(os.listdir(p))[-1]
  data = json.load(open(os.path.join(p, f), encoding='utf-8'))
  ```

## 2. Số Liệu Đo Lường Thực Tế (Session Baseline Overhead)
Tại turn mở đầu, trước khi tính đến lịch sử hội thoại hay ảnh:
- **System Prompt:** 16.415 ký tự (~4.100 tokens).
- **Tools Definitions Schema:** 61.171 ký tự JSON (~14.500 tokens).
- **Tổng Base Overhead mỗi turn:** ~18.600 tokens.

### Bảng Thống Kê 28 Tools Schema
| Tên Tool | Ký tự Mô tả | Số Parameters | Trạng thái Thực tế |
| :--- | :--- | :--- | :--- |
| `session_search` | 4.121 | 8 | Quá dài, nên tinh gọn hướng dẫn FTS5 |
| `skill_manage` | 2.069 | 10 | Đầy đủ hướng dẫn curator |
| `delegate_task` | 1.900 | 5 | Coordinator bị cấm sửa code bằng tool này |
| `execute_code` | 1.723 | 1 | **DEAD SCHEMA** (Coordinator Guard đã cấm hoàn toàn) |
| `memory` | 1.476 | 5 | Hướng dẫn batch atomic |
| `terminal` | 1.376 | 7 | Quy tắc an toàn foreground/background |
| `clarify` | 1.365 | 3 | Cấu trúc 4 điểm bắt buộc |
| `cronjob` | 1.016 | 14 | Quản lý lịch trình |
| `computer_use` | 492 | 49 | Schema JSON nặng do 49 params |
| 10 Tools `browser_*` | ~2.500 | 11 | Chiếm ~10k JSON schema |

## 3. Điểm Nghẽn Trùng Lặp Tri Thức & Rác Ngữ Cảnh

### A. Trùng lặp 100% giữa MEMORY (98%) và USER PROFILE (96%)
- **Shift Pool 4d 3 ca:** Ca 1 {1,2,7}, Ca 2 {3,4,8}, Ca 3 {5,6}; D0 rank 1...
- **Reboot né Game:** Né TFT/War3, Live C: PBE D:...
- **Quy chuẩn Bio / Tên TikTok:** 100% TV có dấu, cấm trùng, cấm văn mẫu...
- **Tracking Vận đơn:** Hub Thanh Khê, J&T/SPX, 47 TCV...
- **Cơ chế Auto-heal:** Sonnet Planner -> O(1) Worker -> Canary -> Closeout...

### B. Trùng lặp Invariants trong System Prompt
- Chi tiết ngân sách O(1) của L2 Emergency Surgery (`<= 2 files`, `<= 30 dòng`, `1 test focused <30s`, `commit [L2-surgery]`) được định nghĩa chi tiết 2 lần:
  1. Trong `THANG LEO THANG KHI KẸT (Mục 3 - L2)`.
  2. Trong `6 GATES ĐIỀU PHỐI (Gate 2 & Gate 5)`.

### C. Case Study Đối Chứng: `sharkrebel/everything-everywhere-for-antigravity`
- **Quy mô:** 346 skills root + 325 skills plugins (11.440 files).
- **Hậu quả:** Nạp tĩnh toàn bộ gây ngộ độc ~15k tokens mô tả/turn, phá vỡ local reasoning ("fix lỗi này lòi lỗi khác"), script install thiếu sót không copy thư mục skills.
- **Khẳng định kiến trúc:** Dynamic Skill Routing O(1) (bốc 3-5 skills theo intent query) là kiến trúc sống còn để duy trì sự tập trung của Agent.
