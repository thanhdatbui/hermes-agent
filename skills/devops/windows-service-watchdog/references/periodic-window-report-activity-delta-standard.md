# Periodic Window Report Activity Delta Standard (6h / 12h / Daily)

## Bối cảnh & Phản ánh từ Operator (2026-10-20)
Khi nhận báo cáo định kỳ mỗi 6 giờ (`BÁO CÁO 6H: VÒNG ĐỜI HOTMAIL -> GPM -> CHATGPT TOÀN FARM`), báo cáo chỉ hiển thị các con số tổng lũy kế (cumulative snapshot):
```text
📊 [BÁO CÁO 6H: VÒNG ĐỜI HOTMAIL -> GPM -> CHATGPT TOÀN FARM]
• Tổng số tài khoản trong Queue: 1037 (Kibe: 409 | Admin: 628)

🔑 TIẾN ĐỘ HOTMAIL LOGIN:
  • Toàn Farm Đã Login Hotmail : 676/1037 (65.2%)
...
🔐 TIẾN ĐỘ CHANGE HOTMAIL & BẢO MẬT:
  • Đã Hoàn Tất Đổi Pass (DONE) : 155/1037 (14.9%)
```
Operator phản ánh trực tiếp:
> *"Đọc report này khó theo dõi tiến độ trong 6h qua quá"*

## Vấn đề cốt lõi: Bẫy Báo Cáo Mù Thời Gian (Time-Blind Snapshot Trap)
- Báo cáo mang tiêu đề "Báo cáo 6h" nhưng nội dung hoàn toàn không chứa bất kỳ mốc thời gian nào liên quan đến 6 giờ vừa qua (`cutoff = now - 6h`).
- Toàn bộ số liệu là tích lũy từ ngày đầu vận hành đến hiện tại.
- Người vận hành nhìn vào không thể biết:
  1. Trong 6h qua hệ thống có chạy không hay đang bị treo/chết lâm sàng?
  2. Sản lượng trong ca này là bao nhiêu acc (Throughput & Velocity)?
  3. Cụm nào đang chạy tích cực, cụm nào đang tạm dừng/cooldown?
  4. Những tài khoản/máy nào vừa hoàn thành mốc quan trọng?

## Quy chuẩn cấu trúc báo cáo định kỳ theo cửa sổ thời gian
Mọi báo cáo định kỳ theo khung giờ (6h / 12h / 24h) BẮT BUỘC tuân thủ cấu trúc 2 tầng:

### Tầng 1: Khối BIẾN ĐỘNG TRONG CỬA SỔ (ĐẶT NGAY ĐẦU BÁO CÁO)
Phải bóc tách từ trường `last_result` (`at`) và mảng `history` (`at >= cutoff`):
1. **Tổng lượt xử lý trong ca:** Tổng số tài khoản/máy có phát sinh hành động trong cửa sổ `[now - Xh, now]`. Chia rõ theo từng cluster/cụm máy (ví dụ `Kibe: 55 | Admin: 20`).
2. **Sản lượng hoàn thành mới (Velocity):**
   - Đổi pass / Chốt bảo mật DONE mới: `+N accounts (Cluster: N) [M218, M220, ...]`
   - ChatGPT Reg mới: `+M accounts (Cluster: M)`
   - Chuyển tiếp trạng thái (Ready CHANGE_INFO): `+K accounts`
3. **Phát sinh lỗi / Cooldown mới:** Số lượng tài khoản fail chuyển trạng thái cooldown trong ca (kèm nguyên nhân chính).
4. **Trạng thái hoạt động 2 cụm (Cluster Activity Status):** Nêu rõ lý do nếu 1 cụm có 0 biến động (ví dụ: *Kibe ngâm cooldown 24h IP | Admin đang chạy cuốn chiếu*). Nếu toàn farm không có biến động, ghi rõ: `(0 biến động trong ca - Toàn bộ tài khoản đang trong chu kỳ ngâm cooldown)`.

### Tầng 2: Khối TỔNG QUAN TÍCH LŨY (LIFETIME / QUEUE)
Đặt ở nửa dưới của báo cáo:
- Đặt tiêu đề rõ ràng: `TỔNG QUAN TÍCH LŨY TOÀN HÀNG ĐỢI (LIFETIME)` để người đọc không nhầm lẫn với số liệu của ca vừa qua.
- Thống kê tỷ lệ phần trăm trên tổng queue (`676/1037 (65.2%)`).

## Thuật toán bóc tách dữ liệu Delta O(1) từ State JSON
```python
def aggregate_recent_activity(raw_profiles: dict[str, Any], cutoff: datetime) -> dict[str, Any]:
    total_processed = 0
    new_done = []
    new_chatgpt = []
    new_login = []
    failed_login = []
    ready_change = []

    for k, p in raw_profiles.items():
        had_action = False
        lr = p.get("last_result") or {}
        lr_at = parse_time(lr.get("at")) if isinstance(lr, dict) else None

        if lr_at and lr_at >= cutoff:
            had_action = True
            m_str = f"M{p.get('machine', 0):02d}" if p.get("machine") else k.split(":")[0]
            stg = lr.get("stage")
            nstg = lr.get("next_stage")
            stat = lr.get("status")
            if stat == "COMPLETED":
                if stg == "CHANGE_INFO" or nstg == "DONE":
                    new_done.append(m_str)
                elif stg == "CHATGPT_REG" or nstg == "WAIT_7D":
                    new_chatgpt.append(m_str)
                elif stg == "WAIT_7D" and nstg == "CHANGE_INFO":
                    ready_change.append(m_str)
                elif stg == "HOTMAIL_LOGIN":
                    new_login.append(m_str)
            elif stat in {"FAILED", "BLOCKED", "ERROR"}:
                if stg == "HOTMAIL_LOGIN":
                    failed_login.append(m_str)

        # Rà soát thêm trong mảng history nếu có sự kiện trước đó trong cùng cửa sổ
        for h in p.get("history", []) or []:
            if isinstance(h, dict) and h.get("at"):
                h_at = parse_time(h.get("at"))
                if h_at and h_at >= cutoff:
                    had_action = True
                    m_str = f"M{p.get('machine', 0):02d}" if p.get("machine") else k.split(":")[0]
                    if h.get("stage") == "CHANGE_INFO" and m_str not in new_done:
                        new_done.append(m_str)
                    elif h.get("stage") == "CHATGPT_REG" and m_str not in new_chatgpt:
                        new_chatgpt.append(m_str)
                    elif h.get("stage") == "HOTMAIL_LOGIN" and m_str not in new_login:
                        new_login.append(m_str)

        if had_action:
            total_processed += 1

    return {
        "total_processed": total_processed,
        "new_done": sorted(new_done),
        "new_chatgpt": sorted(new_chatgpt),
        "new_login": sorted(new_login),
        "failed_login": sorted(failed_login),
        "ready_change": sorted(ready_change),
    }
```
