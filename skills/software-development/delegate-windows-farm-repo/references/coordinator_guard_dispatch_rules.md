# Quy Tắc Định Dạng Dispatch Worker Cho Coordinator Guard

Để vượt qua Coordinator Guard khi điều phối Worker Subagent (`delegate_task`), cần tuân thủ các quy tắc định dạng bắt buộc sau:

## 1. Khai Báo File Bắt Buộc (`EDIT_MISSING_FILE`)
- Bắt buộc có dòng tiền tố `FILE: <đường_dẫn_tuyệt_đối>` trong phần context hoặc goal của task sửa code.
- Ví dụ:
  ```text
  FILE: D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/multi_machine_feed_session.py
  ```

## 2. Giới Hạn Tối Đa File (`MULTI_FILE_VIOLATION`)
- Một task chỉ được phép chứa tối đa $\le 2$ files (1 file nghiệp vụ + 1 file test).
- **Cạm bẫy:** Tránh lặp lại đường dẫn file nhiều lần hoặc viết câu văn chứa nhiều đường dẫn trong cả context lẫn goal; bộ lọc regex của guard sẽ trích xuất tất cả các path và nếu tổng số path độc nhất $> 2$, task sẽ bị từ chối ngay lập tức.
- Nếu cần sửa nhiều hơn 2 files, BẮT BUỘC chẻ nhỏ thành các tasks độc lập.

## 3. Tránh Lỗi `OLD_EQUALS_NEW`
- Khi cung cấp `old_string` và `new_string` trong contract, tránh dùng các thẻ markdown fence lồng nhau (như triple backticks ```python) nếu nội dung code ngắn.
- Trình bóc tách regex của guard có thể parse sai ranh giới giữa các khối code dẫn đến nhận diện nhầm là old_string giống new_string.
- Nên dùng định dạng rõ ràng:
  ```text
  OLD:
  <đoạn code cũ>
  NEW:
  <đoạn code mới>
  ```
