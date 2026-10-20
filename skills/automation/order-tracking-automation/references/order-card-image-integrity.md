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
- Use a contain/native-ratio preview for portrait evidence and provide a click-through to the original.
- Keep product imagery separate from the order-confirmation screenshot; do not claim that a confirmation screenshot is a product gallery.
- Add a focused UI assertion that the image element has a non-cropping presentation and that all declared image roles render or are explicitly marked unavailable.

## Reporting rule

Separate these claims:

- `stored`: the file exists and the endpoint returns it;
- `rendered`: the browser displays the file;
- `complete`: every required image role is present and visible/openable.

Only report `complete` after the third condition is verified. A metadata-rich card with a cropped or missing image is not complete.
