# OmniRoute Round-Robin Sticky Limiting & Prompt-Cache Affinity

## 1. Bản chất của `stickyRoundRobinLimit` vs `disableSessionStickiness`

Khi một Combo được cấu hình chiến lược `round-robin` trên OmniRoute (`open-sse/services/combo.ts`):

### A. Thứ tự ưu tiên định tuyến trong `combo.ts`
1. **Lớp 1 — `applySessionStickiness()` (Ưu tiên cao nhất):**
   * Tính SHA-256 tin nhắn đầu tiên của phiên chat (`sessionHash`).
   * Nếu session đã có binding còn hiệu lực (`TTL = 15m`) và account còn headroom/healthy:
     * **Promote account cũ lên đầu danh sách targets**.
     * Bỏ qua hoàn toàn con trỏ Round-Robin của Combo.
     * Đảm bảo các turn tiếp theo trong cùng 1 cuộc hội thoại ở yên 1 account $\rightarrow$ **Bảo toàn >98% Upstream Prompt Cache**.

2. **Lớp 2 — `getStickyRoundRobinStartIndex()` (Round-Robin Bootstrap):**
   * Chỉ chạy khi request **chưa có binding session** (turn đầu tiên của session mới hoặc `disableSessionStickiness: true`).
   * Con trỏ này sử dụng cấu hình `stickyRoundRobinLimit` (mặc định trong nhiều template là `30` hoặc `3`).

---

## 2. Tử huyệt khi đặt `stickyRoundRobinLimit > 1` với Multi-Session Concurrency

* **Triệu chứng:** Người dùng chạy 5–10 agent/session song song, nhưng trên dashboard OmniRoute toàn bộ request đều đổ dồn vào đúng **1 account duy nhất** (`duo***`, `hoangthi***`), trong khi các account khác trong pool 70 acc hoàn toàn rảnh rỗi.
* **Nguyên nhân:**
  * `stickyRoundRobinLimit: 30` bắt buộc 1 account phải phục vụ đủ **30 request thành công** thì con trỏ toàn cục mới chịu chuyển sang account kế tiếp.
  * Khi 10 session khởi động gần như đồng thời, cả 10 session đều đến trong "vùng 30 request" của account hiện tại.
  * Lớp 2 gán cả 10 session vào cùng 1 account.
  * Ngay sau đó, Lớp 1 (`applySessionStickiness`) ghi nhận binding và **khóa cứng cả 10 session vào account đó**.
  * Hậu quả: Account bị quá tải concurrency $\rightarrow$ dính **Semaphore timeout (30000ms)** và lỗi **429 Too Many Requests**, pool 70 acc bị tê liệt dù quota còn dư thừa.

---

## 3. Cấu hình Vàng (Golden Configuration) cho Pool Lớn (Gemini / Claude / ChatGPT Web)

Áp dụng cho tất cả các Combo chạy Round-Robin (`ag-gemini-pool-3`, `ag-claude`, `chatgpt-web-pool`):

```json
{
  "strategy": "round-robin",
  "config": {
    "stickyRoundRobinLimit": 1,
    "disableSessionStickiness": false,
    "disablePromptCacheAffinity": false
  }
}
```

* **Tại sao hạ xuống `1` KHÔNG làm mất Prompt Cache?**
  * `stickyRoundRobinLimit: 1` chỉ điều phối lúc **cấp phát session mới**: Turn 1 của Session 1 vào Acc 1, Turn 1 của Session 2 vào Acc 2... $\rightarrow$ Tản đều 10 session ra 10 acc khác nhau ngay lập tức.
  * Từ Turn 2 trở đi của mỗi session, `applySessionStickiness` đã nắm quyền và ghim chặt session đó với acc đã cấp phát, **không bao giờ đi qua Round-Robin nữa**.
  * Vừa tránh dồn tải / Semaphore timeout 429, vừa bảo toàn tuyệt đối 100% prompt cache giữa các turn.
