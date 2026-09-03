# ViChanger LSPosed Warning & AdbCaller Protocol (2026-08-24)

## 1. Bản chất Popup "Message: No LSPosed access !!!"
- Khi mở giao diện app ViChanger (`vn.vichanger.app`), popup cảnh báo `No LSPosed access !!!` hoặc `Invalid API Key!!!` thường xuyên xuất hiện trên màn hình thiết bị Android.
- **KẾT LUẬN QUAN TRỌNG:** Đây là hành vi mặc định của app, **HOÀN TOÀN KHÔNG ẢNH HƯỞNG** đến việc gán proxy hay kết nối VPN của hệ thống farm.
- **TUYỆT ĐỐI KHÔNG:** Không mở app bằng tay, không cố bấm cấp quyền LSPosed hay nhập API Key bừa bãi.

## 2. Gán Proxy chuẩn qua Broadcast ADB (AdbCaller)
- Toàn bộ việc gán proxy được thực thi ngầm qua script:
  - Repo: `D:\Taadaa\gan-proxy`
  - Lệnh: `python scripts/gan_proxy_fleet.py run --machines <STT> ...`
  - Cơ chế: Gửi broadcast `vn.vichanger.app.START_VPN` trực tiếp tới receiver `.AdbCaller`. ViChanger sẽ khởi tạo VpnService tunnel ngầm mà không cần tương tác qua giao diện UI của app.

## 3. Cách Verify Live IP chính xác
- Không dùng `curl`/`wget` trên shell Android vì ViChanger chỉ hook traffic ở tầng app Android qua VpnService.
- Kiểm tra bằng lệnh broadcast chuẩn:
  ```bash
  adb -s <serial> shell am broadcast -a vn.vichanger.app.GET_IP -n vn.vichanger.app/.AdbCaller
  ```
  - Kết quả hợp lệ: Trả về `result=200` kèm `data="<IP_PROXY>"`.
