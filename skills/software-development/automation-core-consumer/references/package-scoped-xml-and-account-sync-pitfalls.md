# Package-scoped UI XML Parsing & Device Account Sync Pitfalls

## 1. Package-Scoped XML Parsing (Consumer vs Android System UI)

### Vấn đề
Khi dump UI XML qua uiautomator / atx-agent trên Android, cây XML chứa node của toàn bộ các ứng dụng và hệ thống hiển thị trên màn hình:
- Package Ứng dụng mục tiêu: e.g. `com.ss.android.ugc.trill`
- Package System UI / Notification bar: `com.android.systemui` (e.g. "Thông báo của Dịch vụ Google Play: Yêu cầu đăng nhập", "Không có điện thoại nào", cảnh báo pin...)
- Package Bàn phím / Chooser: `com.sec.android.inputmethod`, `android`

Nếu parser dùng `strip_accents(xml).lower()` hoặc `root.iter("node")` không lọc theo package:
- Các chữ như "đăng nhập", "điện thoại" trong System UI notification sẽ kích hoạt nhầm các flag modal / state của app mục tiêu.
- Dẫn đến script nhận diện sai trạng thái màn hình và thực hiện tap nhầm hành động.

### Giải pháp chuẩn
1. Hàm duyệt node theo package (có kế thừa package từ node cha):
```python
def _iter_package_nodes(root, package):
    def walk(node, inherited_package=None):
        node_package = node.attrib.get("package") or inherited_package
        if node_package == package and node.tag == "node":
            yield node
        for child in node:
            yield from walk(child, node_package)
    yield from walk(root, root.attrib.get("package"))
```
2. Trích xuất text/desc/resource-id chỉ thuộc package mục tiêu (`_package_flat_text`).
3. Truyền `package=APP_PACKAGE` cho các hàm tìm kiếm UI như `find_node_in_xml()`, `find_text_tap()`, `wait_for_text()`, `list_edittext_nodes()`.

---

## 2. Lệch đồng bộ giữa Workbook nguồn, Thiết bị và Tracking

### Hiện tượng
Target detector chọn 1 Gmail từ file nguồn clean (`gmail_clean_v2.xlsx`) làm target vì thấy email đó chưa có tài khoản trong tracking workbook. Tuy nhiên khi chạy thật đến bước đọc OTP trong Gmail app thì báo tài khoản không tồn tại trên thiết bị.

### Nguyên nhân gốc rễ
1. **Lịch sử xóa tài khoản trên Android (`dumpsys account`):** Tài khoản Gmail có thể từng được đăng nhập trên máy trong quá khứ, nhưng sau đó đã bị hệ thống/user xóa khỏi máy (`action_account_remove`).
2. **File nguồn tĩnh:** File danh sách tài khoản nguồn không tự động xóa dòng khi một tài khoản bị gỡ khỏi thiết bị Android.
3. **Tracking remap:** Khi tài khoản mạng xã hội tương ứng bị sửa/map sang email khác, email ban đầu trở thành "mồ côi" và detector tưởng là email mới chưa dùng.

### Quy tắc chẩn đoán & Vận hành
- Khi script báo không tìm thấy tài khoản trong Gmail app:
  1. Chạy `adb shell dumpsys account` để kiểm tra danh sách account thực tế đang có trên thiết bị (`Accounts: N` và `Accounts History`).
  2. Đối chiếu file nguồn với các tài khoản đang active trên máy.
  3. Nếu account đã bị xóa khỏi thiết bị trong quá khứ, cần bổ sung/đăng nhập lại trên thiết bị hoặc cập nhật lại danh sách target hợp lệ.
