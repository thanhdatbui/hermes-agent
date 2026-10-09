# Triển Khai `--password-only` Trong Batch Runner `run_batch_live_2fa.py`

## Bối cảnh
Khi mở rộng quy tắc Chuỗi Đêm (13/09/2026), runner batch `run_batch_live_2fa.py` không chỉ quét các nick chưa có 2FA mà còn phải quét các nick **đã có 2FA nhưng mật khẩu còn yếu** (`password_needs_rotation(pwd) == True`) để đổi sang mật khẩu mạnh ngẫu nhiên mới.

Trước đó, cờ `--password-only` đã được implement trên worker đơn `run_capture_phase_b.py`, nhưng cấp batch `run_batch_live_2fa.py` chưa được cập nhật đầy đủ để nhận diện và truyền cờ này xuống worker con.

## Các bước triển khai chuẩn trong `run_batch_live_2fa.py`

1. **Thêm thuộc tính `password_only: bool = False` vào `BatchTarget`:**
   ```python
   @dataclass
   class BatchTarget:
       machine: str
       serial: str
       source_row: int
       username: str
       has_journal: bool = False
       password_only: bool = False
   ```

2. **Cập nhật hàm `_required_columns` nhận diện cột `pass`:**
   - Trích xuất thêm `password_col = headers.get("pass", 0)` và trả về tuple 5 phần tử:
     `(machine, serial, username, two_fa, password_col)`.

3. **Cập nhật hàm `freeze_targets`:**
   - Đọc giá trị mật khẩu hiện tại trong hàng:
     ```python
     pwd_val = _clean(values[pass_col - 1]) if pass_col else ""
     needs_pwd = password_needs_rotation(pwd_val)
     ```
   - Điều kiện lọc:
     ```python
     if not machine or not serial or not username:
         continue
     if has_2fa and not needs_pwd:
         continue
     pw_only = has_2fa and needs_pwd
     ```
   - Khởi tạo `BatchTarget(..., password_only=pw_only)`.

4. **Truyền `--password-only` vào subprocess command trong `_worker_command`:**
   ```python
   if target.password_only:
       command.append("--password-only")
   ```

## Lưu ý về Test Fixtures & Unit Test
- Khi viết hoặc sửa test fixture cho `freeze_targets`: Nếu tạo một dòng mẫu đại diện cho nick "đã có 2FA và cần bị loại trừ", **bắt buộc phải set password mạnh** (ví dụ: `"StrongP@ss123-"` với `password_needs_rotation(...) == False`).
- Nếu để password trống (`None`) hoặc password dạng legacy farm (`xxx@Ks`), logic mới sẽ coi đây là nick cần rotate mật khẩu và đưa vào danh sách candidates với `password_only=True`, khiến các test assert loại trừ (ví dụ `assertNotIn`) bị fail.
