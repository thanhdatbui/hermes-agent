# Case UI-61: Following Tab Localization Selector Drift & Canary Execution Bounds

## 1. Bối cảnh & Hiện tượng (Root Cause)
- Khi chạy Mode 2 (follow followers / following của anchor profile), runner cần mở danh sách tab Following trên trang cá nhân của anchor (`_open_following_tab`).
- Trên các phiên bản TikTok Android tiếng Việt và giữa các tài khoản khác nhau, tiêu đề tab này xuất hiện dưới nhiều biến thể chuỗi:
  - `Đã follow <count>`
  - `Đang follow <count>`
  - `Đang theo dõi <count>`
  - `Following <count>`
  - `Người theo dõi <count>` (dành cho tab follower)
- Trước bản vá commit `d47975e`, regex `_FOLLOWER_HEADER_RE` và `_FOLLOWER_EMPTY_LABELS` chỉ nhận diện `đã follow` mà thiếu `đang follow` và `đang theo dõi`. Khi anchor profile hiển thị "Đang follow 3" hoặc "Đang theo dõi 5", `_classify_follower_surface` phân loại sai hoặc `_open_following_tab` không nhận diện được tab đã chọn, dẫn đến fail-safe skip hoặc timeout.

## 2. Bản vá đã áp dụng (Commit `d47975e`)
Trong `follow_runner/flows/mode2_follow_followers.py`:
- Cập nhật `_FOLLOWER_HEADER_RE`:
  ```python
  _FOLLOWER_HEADER_RE = re.compile(
      r"^(follower|followers|người theo dõi|đã follow|đang follow|đang theo dõi|following)(?:\s+(\d+))?$",
      re.IGNORECASE,
  )
  ```
- Cập nhật `_FOLLOWER_EMPTY_LABELS`:
  ```python
  _FOLLOWER_EMPTY_LABELS = {
      "follower",
      "followers",
      "người theo dõi",
      "đã follow",
      "đang follow",
      "đang theo dõi",
      "following",
  }
  ```

## 3. Quy trình Canary & Lưu ý Timeout
- Lệnh chạy kiểm chứng:
  ```bash
  D:\Taadaa\python-envs\automation\Scripts\python.exe -m follow_runner.run_follow --machine <id> --config follow_runner/config.example.yaml --account-row-index <idx> --mode 2 --skip-identity-verify
  ```
- **Lưu ý Timeout**:
  - Chu trình Mode 2 bao gồm: vào profile anchor, kiểm tra video gate, xem video anchor, tap nút follow anchor, mở danh sách Following/Follower của anchor, duyệt từng profile con và thực hiện follow kèm delay tự nhiên.
  - Tổng thời gian cho một lượt chạy canary thực tế trên máy thật có thể vượt quá 300s-360s. Khi chạy bằng công cụ CLI có foreground timeout mặc định (180s hoặc 360s), lệnh có thể bị ngắt giữa chừng do timeout trước khi hoàn tất teardown.
  - Khi chạy canary: cần đặt timeout tối thiểu 480s-600s hoặc kiểm tra log/state độc lập sau khi kết thúc.
