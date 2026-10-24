# Triage Quy Trình: [ACCOUNT_SWITCHER_FAILED] ACCOUNT_VERIFY_MISMATCH vs Mất Phiên / Văng Account (False Alarm Triage)

**Ngày ghi nhận:** 17/10/2026  
**Ngữ cảnh áp dụng:** Khi nhận Farm Alert P0 dạng:
`⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Máy Mxx: UploadHook/FeedSession: [ACCOUNT_SWITCHER_FAILED] ACCOUNT_READY verify failed: ACCOUNT_VERIFY_MISMATCH: Profile did not show the expected account.`

---

## 1. Cơ Chế Lỗi & Phân Tích Hiện Trường (False Alarm Mechanism & Network Failure Link)

### Bản chất:
- Khi máy chuyển ca (ví dụ từ Ca Tik 5 `chungan981` sang Ca Tik 8 `phanlan097`):
  - Runner mở Account Switcher thành công (`[ACCOUNT_SWITCHER] Switcher opened via core ✓`).
  - Runner tìm thấy target account trong danh sách và tap chọn thành công (`[ACCOUNT_SWITCHER] Target account selected via core ✓`).
- **Nguyên nhân gốc rễ cốt lõi: Rớt mạng Internet / Proxy Egress Drop (Dấu chấm than Wi-Fi trên Status Bar):**
  - **BẪY FQDN/DOMAIN PROXY TRÊN ANDROID (2026-10-17 ROOT CAUSE):**
    * Khi proxy trên Android (`settings get global http_proxy`) bị gán dạng domain/FQDN ngoài (ví dụ `mirotik1.taadaa.click:1000x`) thay vì IP LAN nội bộ (`192.168.110.2:200xx` hoặc `192.168.110.2:1000x`):
    * Điện thoại Android phân giải qua DNS ngoài (như 8.8.8.8) ra **IP Public WAN Viettel** (`116.99.168.85`).
    * Gói tin từ trong LAN Wi-Fi gửi ra IP Public WAN bị Router MikroTik chặn lại (`DROP_EXTERNAL_PROXY_PORTS` / Hairpin NAT không hỗ trợ proxy ports).
    * Kết quả: Điện thoại bị cúp mạng Internet 100%, Android gắn cờ `"Không có Internet"`. Dù router MikroTik và PPPoE uptime 7 ngày không rớt mạng, điện thoại vẫn không thể ra được Internet!
  - **Dấu hiệu nhận diện đặc trưng trên UI/XML:**
    * Trên thanh Status bar, icon Wi-Fi xuất hiện **dấu chấm than** (`!`).
    * Node hệ thống trong `popup_before.xml`:
      `<node index="8" resource-id="com.android.systemui:id/wifi_combo" content-desc="Tín hiệu Wi-Fi ba vạch.,Không có Internet." bounds="[734,14][781,56]" />`
    * Vòng xoay loading giữa màn hình TikTok:
      `<node index="0" resource-id="com.ss.android.ugc.trill:id/tux_loading_hud" class="android.widget.ProgressBar" bounds="[420,825][660,1065]" />`
  - **Cơ chế TikTok hủy đổi tài khoản khi mất mạng:**
    * Khi tap chọn tài khoản, TikTok bắt buộc phải gửi API request lên server backend để xác thực session token của nick đích.
    * Khi đường truyền proxy bị đứt / rớt mạng (`Không có Internet`), request bị timeout hoặc bị reset.
    * TikTok hiện spinner `tux_loading_hud` quay một lúc, sau đó **hủy bỏ thao tác chuyển đổi tài khoản** và tự động giữ nguyên phiên làm việc của nick cũ (`@chungan981`).
  - **Dây chuyền phán đoán sai lệch:**
    * Script chuyển sang state `ACCOUNT_READY` và gọi `verify_selected_account(..., target_account)`.
    * UI Profile vẫn hiển thị nick ca trước -> Runner ném ngoại lệ: `ACCOUNT_VERIFY_MISMATCH: Profile did not show the expected account`.
    * Khi soft reboot recovery can thiệp, log ghi nhận: `Guarded reboot recovery failed: proxy watcher readiness was not published after reboot: proxy readiness timed out for <serial>`.
    * Watchdog bắt lỗi và tự động kích hoạt `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]`.
- **Thực tế:** Cả nick cũ và nick đích đều đăng nhập nguyên vẹn trong app (không bị logout, không bị ban). Đây là lỗi mạng/proxy tạm thời, TUYỆT ĐỐI CẤM sửa bừa tọa độ tap hay logic UI Switcher!

---

## 2. Quy Trình Khảo Sát T0 & Kiểm Chứng Bắt Buộc

1. **Khảo sát thiết bị O(1):**
   ```bash
   python D:/Taadaa/tools/inspect_machine.py <N>
   ```
2. **Truy vết Run Directory & Artifacts:**
   - Đọc `checkpoint.json` và `report.json` trong `D:/CodexRuntime/tiktok-video/runs/run_<serial>_<timestamp>/`.
   - **BẮT BUỘC kiểm tra `popup_before.xml`:**
     * Tìm node `com.android.systemui:id/wifi_combo`: nếu `content-desc` có cụm `"Không có Internet"`, xác định ngay đây là rớt mạng Internet/Proxy, KHÔNG PHẢI lỗi Switcher!
     * Tìm node `com.ss.android.ugc.trill:id/tux_loading_hud`: xác nhận TikTok đang quay spinner chờ network response từ server.
   - Kiểm tra `execution.log` tìm dòng `proxy readiness timed out` để khẳng định proxy bị rớt ở thời điểm chạy.
3. **Soi mắt kiểm chứng (WinRT OCR / Vision Invariant):**
   - Chạy WinRT OCR trên `account-switcher-profile.png` và `soft-reboot-account_ready-before.png`:
     * Kiểm tra icon Wi-Fi góc trên bên phải thanh Status Bar: có dấu chấm than (`!`) bên cạnh sóng Wi-Fi hay không.
     * Nếu OCR thấy thông tin Profile đầy đủ (Follower, Đang follow, Thích) với username của ca trước -> **100% FALSE ALARM cho mất phiên**.
   - BẮT BUỘC nạp qua `evidence_gate_verifier.py` trước khi đính kèm `MEDIA:` để tránh bị Evidence First Gate chặn:
     ```bash
     python D:/Taadaa/tools/evidence_gate_verifier.py --pre-image "<path_to_image>" --allow-single-inspection --max-age 86400
     ```
4. **Đối soát phiên song song & Khóa thiết bị (Cross-Session & Lock Discovery):**
   - Kiểm tra xem có phiên Agent khác đang điều tra/fix cùng máy/cùng batch không:
     `session_search(query="<mã_lỗi_hoặc_máy>", sort="newest")`
   - Kiểm tra khóa thiết bị `device_lock`:
     `ls -la C:/Users/Kibe/.codex/device-locks/`
     * Nếu có tiến trình nền (ví dụ `PID xxxxx: batch-live-2fa-reservation`) đang giữ lock trên máy, CẤM can thiệp ADB hay chạy lệnh cạnh tranh làm hỏng flow của tiến trình khác.

---

## 3. Kế Hoạch Xử Lý & Đề Xuất Kỹ Thuật

1. **Kỷ luật an toàn tuyệt đối:**
   - CẤM bấm tay ADB trên máy.
   - CẤM sửa bừa code UI tọa độ hay thuật toán Switcher khi nguyên nhân là do rớt mạng Internet/proxy.
   - CẤM xóa tài khoản hoặc đánh dấu DIE trên Excel / database.
2. **Kiểm tra liveness & Tự phục hồi đường truyền Proxy:**
   - Kiểm tra cổng proxy Singbox tương ứng (`192.168.110.2:200xx`) hoặc MobiProxy upstream (`test.taadaa.click:51xx`).
   - Nếu proxy upstream bị ngắt / 502 Bad Gateway: Kích hoạt `mobiproxy_auto_healer.py` hoặc gọi API `proxy_recreat` để reset modem cấp lại IP sạch.
3. **Khắc phục tầng Core & Defense-in-Depth:**
   - **Pre-switch network guard:** Trước khi thực hiện switch tài khoản, kiểm tra nhanh nếu UI chứa node `Không có Internet` hoặc probe egress fail, lập tức phân loại thành `TRANSIENT_NETWORK_DROPPED` thay vì cố tap rồi văng `ACCOUNT_SWITCHER_FAILED`.
   - Tăng `settle` sau `select_exact_account` từ `0.75s` lên `1.5s - 2.0s`.
   - Bổ sung bước đợi `tux_loading_hud` biến mất trước khi thoát khỏi switcher và bước vào `ACCOUNT_READY`.
4. **Phục hồi ca chạy:**
   - Thiết bị sau soft reboot đã được dọn sạch về Home và nhả lock an toàn. Cho phép re-run đợt sau bình thường khi proxy đã thông.
