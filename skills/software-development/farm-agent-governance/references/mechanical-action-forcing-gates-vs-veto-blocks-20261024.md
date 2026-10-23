# MECHANICAL ACTION-FORCING GATES VS VETO BLOCKS & ANTI-BUREAUCRATIC HELPLESSNESS (24/10/2026)

## 1. Bối cảnh & Hiện tượng (The 37-Turn Context Explosion Trap)

Khi nhận yêu cầu *"Chuẩn hoá kênh này"* kèm ảnh profile TikTok, agent cần tra cứu tài khoản nằm ở máy nào, slot nào, folder nào trong farm:
- Agent gọi `search_files` quét đĩa $\rightarrow$ chạm vào `GUARD_SEARCH_FILES_ROOT` và `COORDINATOR_GUARD_TERMINAL` $\rightarrow$ **Bị chặn đứng!**
- **Điểm gãy cốt tử:** Guard chỉ in thông báo cấm vô cảm (`⛔ BỊ CHẶN VÔ ĐIỀU KIỆN!`) mà **không cung cấp đường đi thay thế O(1)**.
- **Hậu quả:** Agent không biết cách nào để tra cứu nhanh, bắt đầu đi đường vòng thủ công: mở bảng `Tik4.xlsx`, trích xuất thumbnail v116, dùng `browser_vision` soi mắt từng frame đối chiếu... Đốt hết **37 tool calls / 9 phút**, nạp đầy log và ảnh vào context làm phình to bộ nhớ và kích hoạt **context compression**!

---

## 2. Phân loại 2 mô hình Gate (Veto Gate vs Action-Forcing Gate)

| Tiêu chí | Veto Gate (Chặn câm / Thụ động) | Action-Forcing Guidance Gate (Cưỡng chế có chỉ dẫn O(1)) |
|---|---|---|
| **Cơ chế** | Bắt lỗi $\rightarrow$ `sys.exit(1)` hoặc in `⛔ BỊ CHẶN!`. | Bắt lỗi $\rightarrow$ Chặn đứng + in `REQUIRED_NEXT_ACTION` kèm lệnh mẫu chuẩn xác. |
| **Phản xạ của LLM** | Coi là "bị bắt lỗi" $\rightarrow$ Loay hoay tìm đường vòng, thử lại mù quáng, hoặc dừng lại viết sớ phân trần / xin lỗi. | Coi là "chỉ dẫn bước kế tiếp" $\rightarrow$ Copy lệnh O(1) chạy ngay ở turn tiếp theo. |
| **Chi phí token / time** | Tốn hàng chục turns, phình context window, cạn quota. | O(1) — hoàn thành ngay trong 1-2 turn kế tiếp. |
| **Trạng thái kết thúc** | Rơi vào paralysis (bại liệt) hoặc cháy budget. | Tiến thẳng về DONE hoặc BLOCKED có evidence xác thực. |

---

## 3. Ba Quy Chuẩn Bắt Buộc Khi Thiết Kế Gate / Guard Cơ Học

### Quy chuẩn 1: Bắt buộc Action Mandate O(1) khi DENY (CẤM CHẶN CÂM)
Mọi Guard (`guard_*.py`, hook terminal, guardgate, closeout_gate) khi `DENY / BLOCK` **bắt buộc phải trả về ít nhất 1 lệnh thực thi thay thế chuẩn hóa (Canonical O(1) Command)** đã điền sẵn tham số thật:
```text
⛔ [GUARD DENY - CẤM QUÉT ĐĨA DIỆN RỘNG]
LÝ DO: Cấm dùng search_files hoặc find/grep trên root farm.
👉 BƯỚC HÀNH ĐỘNG DUY NHẤT HỢP LỆ (O(1)):
   Chạy ngay: python D:/Taadaa/tools/tiktok_account_tracker.py find --username <tên_nick>
   Hoặc tra cứu SQLite: D:/Taadaa/data/tiktok_tracker.db
CẤM đi đường vòng thủ công hoặc trích xuất frame đối chiếu.
```

### Quy chuẩn 2: Auto-Quarantine Khả Hồi (Reversible Self-Healing)
Khi Gate chặn diff hoặc thay đổi code trái phép (ví dụ vi phạm invariant hằng số hoặc chạm vùng cấm):
- Gate không được để lại working tree bẩn (`MM` hoặc diff dở dang) khiến agent sau bối rối.
- Tự động thực hiện **Auto-Quarantine bằng `git stash` an toàn** (không dùng `git checkout --` để tránh mất dữ liệu chưa commit của các vùng hợp lệ):
  ```bash
  git stash push --keep-index -- "<file_vi_pham>" -m "guardgate-quarantine-<rule_id>-<timestamp>"
  ```
- In rõ: *"Đã tự động cách ly thay đổi vi phạm vào stash ref. File đã sạch, tiếp tục thực thi."*

### Quy chuẩn 3: Triệt Tiêu Khóc Lóc Hành Chính Hóa (Anti-Bureaucratic Helplessness)
- **Cạm bẫy:** Sau 3 lần fail, agent ghi ticket vào `_queue.jsonl` rồi dừng phiên phân trần *"Em đã mở ticket chờ sếp duyệt"*. Đây thực chất là hành vi **đùn đẩy trách nhiệm** ném việc ngược về tay Operator!
- **Kỷ luật cưỡng chế:**
  1. Nếu gate thất bại lần 3: Tự động trigger pipeline sửa chữa độc lập (`sol_repair.py`) trong background.
  2. Nếu không thể tự sửa: Đóng dấu task hiện tại là **`BLOCKED` kèm bằng chứng kỹ thuật** (log vi phạm, diff vi phạm) $\rightarrow$ **LẬP TỨC CHUYỂN SANG TASK ĐỘC LẬP KẾ TIẾP trong hàng đợi**, tuyệt đối cấm dừng session hay ngồi đợi User cứu!
