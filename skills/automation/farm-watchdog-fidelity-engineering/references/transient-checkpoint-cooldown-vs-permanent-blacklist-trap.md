# Transient Checkpoint Cooldown vs Permanent Blacklist Trap (Chống Ngọng Luôn)

## 1. Bản Chất Vấn Đề
Khi watchdog hoặc automation runner gặp lỗi xác minh danh tính (Google Checkpoint, Phone Challenge `challenge/iap`, Rate Limit, reCAPTCHA loop), phản xạ sai lầm phổ biến của agent là:
- Ném tài khoản vào một blacklist tĩnh (như `wrong_password_or_checkpoint` hoặc danh sách `quarantine` không có thời hạn).
- Hậu quả: Tài khoản bị loại trừ vĩnh viễn khỏi hàng đợi ("ngọng luôn"), không bao giờ có cơ hội tự phục hồi dù bản chất tài khoản vẫn sống và chỉ cần hạ nhiệt tạm thời (24h - 48h).

---

## 2. Kiến Trúc Phân Loại Lỗi: Permanent Block vs Dynamic Cooldown

| Nhóm lỗi | Ví dụ | Cơ chế lưu trữ | Hành vi Watchdog |
| :--- | :--- | :--- | :--- |
| **Permanent Fail** (Cứng) | Sai mật khẩu (`WRONG_PASSWORD`), tài khoản bị vô hiệu hoá (`ACCOUNT_DISABLED`), vi phạm điều khoản vĩnh viễn | `wrong_password` (Không có `retry_after`) | Loại trừ vĩnh viễn khỏi mọi đợt quét cho đến khi con người can thiệp cập nhật mật khẩu mới. |
| **Transient Security Challenge** (Mềm) | Google Phone Checkpoint (`challenge/iap`), 2SV sensitive cooldown (`signin/rejected?rrk=77`), SMS rate limit | `cooldown_bucket` (BẮT BUỘC kèm `retry_after: YYYY-MM-DDTHH:MM:SS`) | - Khi `today < retry_after`: Loại trừ an toàn, ngắt hoàn toàn spam để tài khoản hạ nhiệt.<br>- Khi `today >= retry_after`: **Tự động bốc lại vào hàng đợi ưu tiên** (`cooldown_expired`) để thử lại zero-touch. |

---

## 3. Quy Tắc Cơ Giới Hóa Trong Candidate Selector (`get_candidates`)

Mọi watchdog quản lý ứng viên đăng nhập / nuôi acc bắt buộc phải có 2 pha đối soát thời gian:

```python
# 1. Pha kiểm tra hạn ngạch cooldown
cooldown_expired = []
for account, info in status_data.get("cooldown_bucket", {}).items():
    retry_after = (info.get("retry_after") or "")[:10]
    if retry_after <= today_str:
        # Hết hạn cooldown -> Đủ điều kiện thử lại tự động
        cooldown_expired.append((account.lower(), info.get("machine")))
    else:
        # Đang trong thời gian hạ nhiệt -> Bảo vệ không spam
        excluded_accounts.add(account.lower())

# 2. Pha tự động kích hoạt lại ứng viên hết hạn
for account, mid in cooldown_expired:
    if account not in seen_today and account not in excluded_accounts:
        candidates.append({
            "email": account,
            "mid": mid,
            "priority": 1,  # Ưu tiên cao nhất để cứu phiên
            "reason": "cooldown_expired",
            "is_relogin": True
        })
```

---

## 4. Kỷ Luật Khi Retry Thất Bại (Chống Zombie Candidate)
- Nếu một tài khoản hết hạn cooldown (`cooldown_expired`) được bốc ra chạy lại nhưng **vẫn tiếp tục thất bại**:
  - **CẤM** giữ nguyên mốc `retry_after` cũ trong quá khứ (vì điều kiện `retry_after <= today` sẽ luôn đúng, biến tài khoản thành "zombie" bị bốc ra chạy đập đi đập lại mỗi ngày).
  - **BẮT BUỘC** tự động gia hạn `retry_after` lùi tiếp:
    ```python
    entry["retry_after"] = (datetime.now(HCMC) + timedelta(days=14)).strftime("%Y-%m-%d")
    ```
  - Đảm bảo tài khoản tiếp tục được nghỉ ngơi chu kỳ mới thay vì spam liên tục làm hỏng trust.
