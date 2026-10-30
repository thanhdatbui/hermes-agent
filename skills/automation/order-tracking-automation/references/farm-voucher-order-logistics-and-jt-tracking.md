# Farm Voucher Order Logistics & J&T Express Tracking

## 1. J&T Express Web Tracking & 4-Digit Phone Validation Trap

J&T Express public tracking endpoints reject or 404 on unauthenticated REST API calls. On their tracking web portal, entering only the billcode displays a blocking modal requiring the last 4 digits of the recipient's phone number (`document.getElementById("modal-verify")`).

### Solution: Direct Query Param Injection
Pass the last 4 digits directly via URL query parameter `cellphone=<last4>`:
```text
https://jtexpress.vn/vi/tracking?type=track&billcode=<BILLCODE>&cellphone=<LAST_4_DIGITS>
```
- **Response:** Fully hydrated HTML containing timeline section `id="chck-<BILLCODE>"`.
- **Parsing:** Extract date/time pairs (`HH:MM:SS` followed by `YYYY-MM-DD`) and status descriptions (e.g. `Hàng đã được chuyển đến【TTKT ĐÀ NẴNG】`, `Đã đến bưu cục...`, `Nhân viên... đang giao hàng`).

---

## 2. The Anti-App-Download Trap on Farm Voucher Orders

### The Blunder:
Recommending that the user "download the carrier app (J&T/SPX) and log in with recipient phone number" when tracking farm/voucher orders.

### The Ground Truth:
- In TikTok Shop farming and voucher exploitation, each account is deliberately provisioned with varied/disposable recipient names, dummy phone numbers, and modified street addresses to evade platform cluster fraud algorithms (Cluster Detection).
- The user **does not own or have physical SIM/OTP access** to these virtual/disposable numbers.
- **Rule:** NEVER suggest downloading carrier mobile apps or relying on carrier SMS/OTP for farm orders. All tracking must be programmatic via web tracking endpoints, in-app OCR on the farm device, or direct hub arrival interception.

---

## 3. Multi-Shipper Routing & Secret Keyword Convention

When orders are farmed across multiple couriers in the same delivery zone:
- Different platforms/stores allocate parcels to different couriers (e.g., SPX vs. J&T).
- Each carrier assigns specific delivery staff to a route. Some couriers are cooperative and can be coordinated with; others may mismanage orders or mark them as "Customer unreachable".
- **The Secret Keyword Pattern:**
  - Because recipient names and addresses must vary to bypass platform fraud filters, establish a fixed **"Secret Keyword / Code"** inside the order note or address suffix (e.g. `...(Giao 47 TCV)` or `[CODE-XYZ]`).
  - Coordinate once with the route couriers or the local hub dispatch manager: any parcel bearing that secret keyword belongs to the operator and should be held at the local counter or delivered in batch to the operator's physical location.

---

## 4. Dual-Channel Alerting & Host Audio Alarms

In farm environments where Telegram alert groups receive dozens or hundreds of bot notifications daily:
- Important milestone alerts (e.g. parcel arrived at local hub before morning delivery dispatch) will be lost in group notification noise or muted chats.
- **Implementation Pattern:**
  1. Route critical order alerts strictly to **User DM** (`deliver: origin`), never to shared farm alert groups.
  2. Implement local host audio alarms on the 24/7 host machine:
     ```python
     def play_alarm(text: str) -> None:
         try:
             import winsound
             for _ in range(3):
                 winsound.Beep(1200, 300)
                 winsound.Beep(1600, 300)
         except Exception:
             pass
         try:
             import win32com.client
             speaker = win32com.client.Dispatch("SAPI.SpVoice")
             speaker.Speak(text)
         except Exception:
             pass
     ```
  3. Fire the audible alarm specifically when the parcel hits `is_at_hub` (local dispatch station) or `is_out_for_delivery` so the user is immediately alerted that the courier is preparing to deliver the parcel to the destination address.

---

## 5. J&T Express Post Office Naming Syntax & Airport/City Code Prefix Trap (`(ĐNG)...`)

### The Trap:
In tracking timeline descriptions, J&T Express does not spell out the full province name for district delivery stations. Instead, it prefixes the branch name with a 3-letter IATA/telegraphic province code in parentheses, e.g.:
```text
Hàng đã được chuyển đến【(ĐNG)Đống Đa】
```
Where:
- `(ĐNG)` = Đà Nẵng.
- `Đống Đa` = Bưu cục phát Đống Đa (phụ trách các tuyến đường quận Hải Châu như Đinh Tiên Hoàng, Thuận Phước, Thạch Thang).

If destination arrival filters only check for naive full substrings such as `["đà nẵng", "da nang", "hải châu"]`, events like `Hàng đã được chuyển đến【(ĐNG)Đống Đa】` return `False`. As a result, the critical arrival milestone is silenced, and the status fails to update to "Đã đến bưu cục phát".

### The Invariant:
Arrival heuristics for J&T must include:
1. Short telegraphic city/province codes: `đng` (Đà Nẵng), `sgn` (TP.HCM), `han` (Hà Nội), etc.
2. Local delivery branch names: `đống đa`, `dong da`, `hải châu`, `hai chau`, etc.
3. Explicit check: `any(f in desc_clean for f in ["đà nẵng", "da nang", "hải châu", "hai chau", "ttkt đà nẵng", "đng", "đống đa", "dong da"])`.

---

## 6. The Anti-Counter-Pickup Invariant & Clickable Tracking Link Delivery

### The Rule (User Discipline):
- **CẤM TUYỆT ĐỐI giục/bảo user ra bưu cục lấy hàng:** Người dùng đặt hàng giao về tận nhà/địa chỉ; hệ thống chỉ có trách nhiệm theo dõi và cảnh báo mốc khi shipper nhận hàng đi phát về địa chỉ. Tuyệt đối không được bảo user ra quầy/bưu cục tự lấy hay dặn giữ hàng tại bưu cục.
- **Tiêu đề thông báo chuẩn:** Chỉ dùng `📦 THÔNG BÁO: HÀNG ĐÃ VỀ BƯU CỤC PHÁT` (chuẩn bị giao về địa chỉ) hoặc `🚨 BÁO ĐỘNG GIAO HÀNG: SHIPPER ĐANG ĐI PHÁT`, cấm dùng từ 'Thời điểm vàng lấy tại quầy'.
- **Clickable Tracking Links:** Khi gửi link tra cứu bưu cục cho user trên Telegram/chat, BẮT BUỘC gửi link dạng URL trần hoặc markdown link có thể click trực tiếp nhảy sang trình duyệt (`https://...` hoặc `[Tra cứu](https://...)`), TUYỆT ĐỐI CẤM bọc trong code block (```text) làm user không bấm nhảy trang được.
