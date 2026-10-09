# Smart Proxy Quota Policy: Platform Error vs Script Error Separation

## 1. Nguyên Tắc Cốt Lõi (Farm Invariant)
Trong tất cả các tác vụ tự động hóa Login, Reg, Verify (OAuth, 2FA, ChatGPT, Gmail, TikTok...) trên cụm Proxy Farm:
* **Tài nguyên IP/Proxy là hữu hạn và rất dễ bị nền tảng gắn cờ (fraud score/checkpoint)**.
* **Quy tắc phân loại lỗi bắt buộc**:
  - **Lỗi Nền Tảng (Platform/Target Server Error):** Tính **1 lượt sử dụng trong ngày** (tương đương SUCCESS) -> **Khóa IP/Port proxy đó ngay lập tức** đến 00:00 hôm sau.
  - **Lỗi Script / Nội Bộ (Script/Environment Error):** **KHÔNG TÍNH VÀO QUOTA IP** -> Giữ IP để thử lại profile/acc khác trong ngày.

---

## 2. Bảng Phân Định Chi Tiết

| Loại lỗi | Dấu hiệu nhận diện | Hành vi xử lý Quota Proxy |
| :--- | :--- | :--- |
| **Lỗi Nền Tảng (Platform Error)** | - Google Checkpoint bắt số điện thoại (`challenge/iap`, `challenge/selection`)<br>- reCAPTCHA challenge / audio challenge fail<br>- Google báo *"Trình duyệt không an toàn"* / `rejected`<br>- Sai mật khẩu / Đổi mật khẩu (`BLOCKED_WRONG_PASSWORD`)<br>- Rate limit 429/403 từ server đích | 🛑 **TÍNH 1 LƯỢT DÙNG (như SUCCESS)**.<br>Ghi nhận `used_proxies[proxy_key] = {"status": "PLATFORM_FAIL", "reason": ...}`.<br>**Khóa IP/Port này cả ngày** để bảo vệ dàn nick sau không bị chết lây. |
| **Lỗi Script / Nội Bộ (Script Error)** | - GPM Local API timeout hoặc crash khi start profile (`START_FAILED`, `LAUNCH_FAILED`)<br>- Không tìm thấy mật khẩu / credentials trong Excel/DB (`MISSING_PASSWORD`)<br>- Profile bị skip do quy tắc lọc (ví dụ: `SKIPPED_KHOALEE`, `cooldown_7days`)<br>- Mất kết nối local CDP / crash Playwright trước khi load được web đích | ⚠️ **KHÔNG TÍNH QUOTA IP**.<br>IP/Port proxy đó **vẫn mở** để thử acc khác trong nhịp quét kế tiếp.<br>Chỉ ghi nhận email lỗi vào `failed_script_emails` để tránh lặp vô tận cùng 1 nick. |

---

## 3. Mô Hình Code Mẫu Chuẩn

```python
# Phân loại trạng thái sau khi thực thi
if status == "SUCCESS":
    daily_state["used_proxies"][proxy_key] = {"email": email, "status": "SUCCESS"}
    daily_state["success_emails"].append(email)
elif fail_type == "PLATFORM":
    # Khóa IP an toàn
    daily_state["used_proxies"][proxy_key] = {
        "email": email,
        "status": "PLATFORM_FAIL",
        "reason": reason
    }
else:
    # Lỗi script: Không khóa IP, chỉ blacklist email trong ngày
    daily_state["failed_script_emails"].append(email)
```

---

## 4. Định Dạng Báo Cáo Định Kỳ (Báo Cáo 6h)
Báo cáo định kỳ bắt buộc phân tách 3 nhóm rõ ràng để giám sát vận hành:
1. ✓ **Thành công**: Danh sách acc nạp/login thành công kèm Port.
2. 🛑 **Lỗi nền tảng (Đã khóa IP)**: Nêu rõ port và nguyên nhân (reCAPTCHA, Checkpoint SĐT, Sai pass).
3. ⚠️ **Lỗi script / nội bộ (IP được giữ)**: Nêu rõ lý do (GPM start fail, thiếu pass Excel) để bảo trì script mà không làm mất lượt IP của farm.
