# Triage: Vì sao các nick chạy thành công lại follow ít / không đạt full budget 15-20

Khi user hỏi: "Tại sao các nick chạy được thực tế lại follow ít như vậy, không đạt budget?", **TUYỆT ĐỐI KHÔNG lảng tránh hay đi phân tích các nick bị nhả follow / failed**. Trả lời thẳng vào các nick chạy được theo checklist dưới đây:

## 1. Kiểm tra Quyết định Budget (Dual Gate: Video + Age)
Mở file state JSON của nick tại `D:/Taadaa/tiktok-follow/runs/state/follow_state_<m>_row_<row>.json`:
Xem trường `last_budget_decision`:
```json
"last_budget_decision": {
  "budget": 5,
  "video_count": 9,
  "account_age_days": 218,
  "mode": "full"
}
```
* **Luật Dual Gate trong `follow_state.py`:**
  * Nick có `video_count < 10` HOẶC `account_age_days <= 30`: Hệ thống tự động xếp vào giai đoạn mồi nhẹ, budget phiên bị giới hạn cứng **3 - 5 lượt/phiên** (`_random.randint(3, 5)`).
  * Chỉ khi `video_count >= 10` VÀ `account_age_days > 30`: Mới được cấp full budget phiên **10 - 20 lượt** (`_range(1)`).
  * Nếu nick chỉ có 9 video (như M23), việc nó chỉ chạy 3-5 lượt là **đạt 100% budget được cấp**, không phải lỗi.

## 2. Kiểm tra Phân bổ Mode 2 vs Mode 1
Trong `follow_result.json` hoặc log:
* **Mode 2 (Follow follower của anchor Tik1/Tik2):** Chỉ chọn tối đa 3 anchor trong farm. Nếu farm đã chạy nhiều ngày, danh sách của 3 anchor này gần như đã follow chéo hết, thường chỉ còn 1-2 nick mới $\rightarrow$ Mode 2 dừng sớm vì cạn nick nội bộ chưa follow.
* **Mode 1 (Search UID bù budget):** Hệ thống fallback sang Mode 1 để bù số còn thiếu cho đủ budget phiên.

## 3. Quy luật 2 Phiên / Ca (Shift Split)
* Một ca gồm **2 phiên** (ví dụ Ca 1: Phiên 1 lúc 06:11 và Phiên 2 lúc 08:10).
* Quota an toàn cả ca (10-15 lượt) được chia đều qua 2 phiên (mỗi phiên 5-8 lượt) để tránh bị TikTok nghi ngờ hành vi spam trong một phiên ngắn.
* Phải cộng tổng cả 2 phiên của ca để tính tổng số follow thực tế.
