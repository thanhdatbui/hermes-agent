# Email Reconciliation & Normalization Pitfalls

## Vấn đề gặp phải
Khi đối soát giữa nguồn mail (`gmail_clean_v2.xlsx`) và file theo dõi trạng thái TikTok (`taikhoan_dat_v2_updated .xlsx`), dữ liệu cột GMAIL trong file tracking có thể gặp các dạng:
1. Chỉ ghi username không có domain (ví dụ: `lamngocdiep030420000304` thay vì `lamngocdiep030420000304@gmail.com`).
2. Có tiền tố `mailto:` (ví dụ: `mailto:nguyenthiminhanh120320021203@gmail.com`).
3. Viết hoa/thường không đồng nhất.

## Quy tắc xử lý
BẮT BUỘC dùng chuẩn hóa `mailbox_key` trước khi so khớp:
```python
def normalize_mailbox(val: object) -> str:
    if val is None:
        return ""
    text = str(val).strip()
    if text.lower().startswith("mailto:"):
        text = text[7:].strip()
    norm = text.casefold()
    if norm and "@" not in norm:
        norm += "@gmail.com"
    return norm
```

## Kiểm tra trạng thái đã đăng ký (Registered)
Một mail được tính là **ĐÃ ĐĂNG KÝ** TikTok khi và chỉ khi:
- Trong bảng tracking có dòng tương ứng với mail đó (sau chuẩn hóa) VÀ cột `ID` (hoặc `PASS`) của TikTok không rỗng.
- Nếu mail có trong tracking nhưng `ID` trống, mail đó vẫn ở trạng thái PENDING / CHƯA REG.
