# Strict Profile Isolation & Collision Guard

## 1. Bối cảnh & Nguyên nhân lỗi
Khi quản lý pool tài khoản Google quy mô lớn trên GPMLogin kết hợp tự động hóa OAuth Playwright CDP:
- Nhiều tài khoản Google có thể được add trên cùng một thiết bị Samsung S7 phần cứng.
- Tuy nhiên, trên GPMLogin: **MỖI PROFILE TRÌNH DUYỆT BẮT BUỘC CHỈ MANG 1 GMAIL DUY NHẤT (1 Profile : 1 Gmail)**.
- **Lỗ hổng cũ:** Code kiểm tra thư mục profile chỉ dựa vào `os.path.exists(os.path.join(GPM_BASE, acc["profile"]))`. Nếu một batch script truyền nhầm profile path của máy cũ (ví dụ: `SUNVqFew4a-05092026` của `khahoan240161@gmail.com`), script thấy folder tồn tại nên nhảy thẳng vào mở browser $\rightarrow$ Dẫn đến Gmail mới đăng nhập đè lên profile của Gmail cũ, dính chung cookie/session và bị Google đánh dấu hoạt động bất thường (dính Hard SMS Checkpoint).

---

## 2. Quy chuẩn phân giải Profile (Strict Profile Resolution)

Hàm `resolve_profile_dir(acc, gpm_base)` được chuẩn hóa thành 3 chốt chặn:

```python
def resolve_profile_dir(acc, gpm_base=GPM_BASE):
    email = acc.get("email", "").strip().lower()
    mid = acc.get("mid", 0)
    prof_field = acc.get("profile", "").strip() if acc.get("profile") else ""
    db_path = os.path.join(gpm_base, "profile_data.db")

    # BƯỚC 1: Luôn tra cứu profile riêng theo chính xác Email trong SQLite trước tiên
    if os.path.exists(db_path) and email:
        try:
            with sqlite3.connect(db_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT ProfilePath, Name FROM Profiles WHERE lower(Name) LIKE ?", (f"%{email}%",))
                rows = cur.fetchall()
                if rows:
                    for ppath, pname in rows:
                        pdir = os.path.join(gpm_base, ppath)
                        if os.path.exists(pdir):
                            logger.info(f"[M{mid:02d}] ✅ Đã tìm thấy profile riêng của {email} -> {ppath}")
                            return pdir, None
        except Exception as e:
            logger.warning(f"Error querying profile_data.db: {e}")

    # BƯỚC 2: Cross-account Collision Guard (Nếu truyền prof_field từ bên ngoài)
    if prof_field:
        # Guard 2a: Nếu tên thư mục chứa ký tự @ nhưng không chứa email này -> Chặn ngay
        if "@" in prof_field and email not in prof_field.lower():
            err_msg = f"Profile directory '{prof_field}' contains another email, not {email}!"
            logger.error(f"[M{mid:02d}] 🚫 LỖI CÁCH LY PROFILE: {err_msg}")
            return None, "PROFILE_COLLISION_BLOCKED"

        # Guard 2b: Tra cứu trong DB xem ProfilePath có đang thuộc về email khác không
        if os.path.exists(db_path):
            try:
                with sqlite3.connect(db_path) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT Name FROM Profiles WHERE ProfilePath = ?", (prof_field,))
                    row = cur.fetchone()
                    if row and row[0] and "@" in row[0]:
                        if email not in row[0].lower():
                            err_msg = f"ProfilePath '{prof_field}' is owned by '{row[0]}', NOT {email}!"
                            logger.error(f"[M{mid:02d}] 🚫 LỖI CÁCH LY PROFILE: {err_msg}")
                            return None, "PROFILE_COLLISION_BLOCKED"
            except Exception as e:
                logger.warning(f"Error checking profile owner in DB: {e}")

        # Guard 2c: Thư mục hợp lệ trên đĩa
        pdir = os.path.join(gpm_base, prof_field)
        if os.path.exists(pdir):
            return pdir, None

    # BƯỚC 3: Tuyệt đối CẤM fallback mở bừa profile khác
    logger.error(f"[M{mid:02d}] 🚫 LỖI CÁCH LY PROFILE: Tài khoản {email} không có profile riêng hợp lệ trên hệ thống!")
    return None, "PROFILE_NOT_FOUND"
```

---

## 3. Nhận diện Hard SMS Checkpoint & Kỷ luật xử lý

- **Hiện tượng:** Màn hình Google hiển thị *"Có điều bất thường về hoạt động của bạn... Nhập số điện thoại để nhận tin nhắn văn bản"* kèm thông báo đỏ *"Đã xảy ra lỗi. Rất tiếc, đã xảy ra sự cố. Vui lòng thử lại."*
- **Bản chất:** Google chặn luồng trên IP/session đó và bắt buộc xác minh số điện thoại thực. Google **HOÀN TOÀN KHÔNG BẮN GOOGLE PROMPT VỀ ĐIỆN THOẠI S7**.
- **Kỷ luật xử lý:**
  1. **CẤM TUYỆT ĐỐI** cố gắng chạy retry liên tục trên cùng proxy/IP vì sẽ làm tài khoản bị blacklist sâu hơn.
  2. Cho tài khoản ngâm nghỉ (cool down ít nhất 24-48 giờ).
  3. Chỉ re-auth sau khi đổi proxy hoặc ưu tiên tài khoản có sẵn TOTP Secret (Authenticator) để bypass màn hình prompt/SMS.
