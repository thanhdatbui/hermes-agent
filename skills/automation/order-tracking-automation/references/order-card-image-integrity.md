# Order-card image integrity — session detail

## Observed failure pattern

A portrait TikTok Shop order screenshot was saved successfully and the API returned its path, but the dashboard card rendered it inside a forced `4 / 3` frame with `object-fit: cover`. The source image therefore appeared incomplete even though the file itself was intact. The order card also modeled only one `image_path`, so it could not represent separate confirmation, product, address, and later tracking evidence.

## Reproduction checklist

1. Confirm the source file exists and record its dimensions.
2. Read the order endpoint and check whether it exposes one path or an image list.
3. Inspect the renderer for `aspect-ratio` and `object-fit`; `cover` in a fixed ratio is a likely crop.
4. Open the source image and the rendered dashboard state separately; do not infer UI fidelity from API success.
5. Compare the rendered image against the source, including top and bottom regions.

## Corrective design

- Keep a backward-compatible `image_path` for the primary artifact, but add `images: [{role, path, caption, captured_at}]` for multiple evidence images.
- Use a contain/native-ratio preview for portrait evidence and provide a click-through to the original:
  - CSS:
    ```css
    .order-thumb-wrap { position: relative; width: 100%; max-height: 480px; background: #0b0f19; display: flex; align-items: center; justify-content: center; }
    .order-thumb-link { display: block; width: 100%; text-align: center; }
    .order-thumb { width: 100%; max-height: 480px; object-fit: contain; display: block; cursor: zoom-in; }
    ```
  - Markup:
    ```html
    <a class="order-thumb-link" href="/orders/images/${encodeURIComponent(imgName)}" target="_blank" title="Bấm để xem ảnh gốc kích thước đầy đủ">
        <img class="order-thumb" loading="lazy" src="/orders/images/${encodeURIComponent(imgName)}" alt="Ảnh đơn ${ordersEsc(order.order_id)}"
             onerror="this.closest('.order-thumb-link').style.display='none';this.closest('.order-thumb-wrap').querySelector('.order-thumb-fallback').style.display='flex'">
    </a>
    ```
- Hot-reload under watchdog:
  - When updating `tiktok_dashboard.py`, running under `tiktok_dashboard_watchdog.ps1`, terminate the dashboard process (`p.terminate()`).
  - The watchdog respawns a fresh instance with the updated code within 2–5s. Verify HTTP 200 on port 1905 before browser navigation.
  - **Post-Reboot Cold-Start Latency (`WinError 10061` Trap)**:
    - Watchdogs typically execute `Start-Sleep -Seconds $IntervalSeconds` (e.g. 60s) before their first health check probe.
    - Probing the port immediately after a scheduled host reboot (e.g. 05:20) will return `ConnectionRefusedError: [WinError 10061]`.
    - Do NOT mistake this initial latency for a broken service, and DO NOT invoke prohibited coordinator commands (`cscript`, `netstat`, or calling python from protected venv paths).
    - Allow up to 60–75s with progressive 5s urllib polling, or check `psutil` process table for `watchdog.ps1` to confirm supervisor liveness before concluding hard failure.
- Keep product imagery separate from the order-confirmation screenshot; do not claim that a confirmation screenshot is a product gallery.
- Add a focused UI assertion that the image element has a non-cropping presentation and that all declared image roles render or are explicitly marked unavailable.
- Verification gate for "xem ảnh gốc qua web":
  - Navigate directly to `http://localhost:1905/orders/images/<filename>` in browser / `browser_vision`.
  - Validate all 4 critical sectors: Status & Stepper (Đã đặt hàng/Chờ chuyển phát), Recipient & Address, Product details, and Email notification toggle.
  - Verify edge fidelity (no cut text, no missing headers/footers).

## Reporting rule

Separate these claims:

- `stored`: the file exists and the endpoint returns it;
- `rendered`: the browser displays the file;
- `complete`: every required image role is present and visible/openable.

Only report `complete` after the third condition is verified. A metadata-rich card with a cropped or missing image is not complete.
