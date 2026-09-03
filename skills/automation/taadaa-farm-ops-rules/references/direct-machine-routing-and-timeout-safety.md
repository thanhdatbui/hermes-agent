# Direct Machine Routing from Banner & Timeout Safety (Farm Ops)

## 1. Định tuyến O(1) trực tiếp từ Alert Banner [MAY N]
- Mọi ảnh alert đều có banner đỏ ở mép trên cùng ghi rõ: `[MAY <N>]` (ví dụ `[MAY 76] - 05:14:16 01/09`).
- Khi nhận ảnh hoặc alert ghi rõ Máy N:
  1. Tra ngay Serial từ `D:\Taadaa\machine-config\kibe.yaml` theo số máy `<N>`.
  2. Truy cập trực tiếp vào thư mục log/artifact riêng của máy đó:
     - `D:\Taadaa\runtime\kibe\live\<ngày>\*\machines\machine_<N>\`
     - `D:\Taadaa\runtime\kibe\artifacts\alert_machine_<N>.png`
     - Lấy XML/screenshot hiện trường: `adb -s <serial> ...`
  3. **TUYỆT ĐỐI CẤM:** Chạy lệnh quét đệ quy (`grep -rn`, `find`) trên toàn bộ thư mục `.ai-runs/` hoặc `D:\Taadaa\runtime\` gây nghẽn đĩa và timeout 900s.

## 2. Quy tắc Focused Test & Fail-Fast Timeout
- Khi debug hoặc chạy release gate, **CHỈ chạy focused test** theo file/class/chức năng vừa sửa (<30s).
- **CẤM chạy full test suite** toàn repo (hàng nghìn test) gây nghẽn luồng và timeout.
- Các lệnh terminal dài phải đặt timeout ngắn (30-60s) để fail-fast, không để lệnh treo quá 120s.
