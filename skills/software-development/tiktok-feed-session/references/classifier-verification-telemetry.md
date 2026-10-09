# Classifier Verification & Telemetry Conventions

## Calling Signature of `classify_tiktok_screen`
In `D:/Taadaa/tiktok-luot nuoi acc/python_runner/core/classifier.py`:
- `classify_tiktok_screen(root)` expects an `xml.etree.ElementTree.Element` (or an object with `.iter("node")` yielding XML element nodes with `.attrib`), NOT a Python list of `UIElement`.
- To create mock tests or ad-hoc verification for `classify_tiktok_screen`:
  ```python
  import xml.etree.ElementTree as ET
  from core.classifier import classify_tiktok_screen

  root = ET.Element("hierarchy")
  node1 = ET.SubElement(root, "node", {
      "resource-id": "com.zhiliaoapp.musically:id/view_pager",
      "text": "",
      "content-desc": "",
      "clickable": "false",
      "bounds": "[0,0][1080,2400]",
  })
  node2 = ET.SubElement(root, "node", {
      "resource-id": "com.zhiliaoapp.musically:id/desc",
      "text": "nhập mã xác nhận",
      "content-desc": "",
      "clickable": "false",
      "bounds": "[50,1800][800,1900]",
  })
  res = classify_tiktok_screen(root)
  ```

## Verification Telemetry in Reasons
- When feed controls are active (`_has_feed_detail_controls(elements)`), challenge terms inside video descriptions/comments should NOT trigger `manual-needed:verification`.
- Instead, record telemetry in `reasons`:
  `feed controls active; verification keywords ignored on feed content: <matched_samples[:2]>`
- When feed controls are absent and verification keywords match:
  Return `manual-needed:verification` with reasons:
  `manual_challenge/verification text present: <matched_samples[:2]>`
- Keep reasons structured and include the first two matched samples to aid debugging and telemetry aggregation across farm machines without stopping feed flows prematurely.
