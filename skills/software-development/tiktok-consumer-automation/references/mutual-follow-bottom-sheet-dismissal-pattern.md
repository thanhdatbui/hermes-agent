# Mutual Follow Bottom Sheet ("Đã follow chung") Dismissal Pattern

## Incident Context (M43 Incident)
During feed swipe, follow, and profile navigation flows on TikTok (Samsung Galaxy farm devices), TikTok frequently displays a bottom sheet overlay ("Trang tính dưới cùng") recommending accounts that share mutual follows ("Đã follow chung (N)").

If unhandled, this sheet intercepts touches and blocks subsequent feed swipes or interactions.

## UI Hierarchy Signature
```xml
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.ss.android.ugc.trill" bounds="[0,0][1080,1920]">
    <node index="0" text="" resource-id="com.ss.android.ugc.trill:id/f8_" class="android.view.ViewGroup" package="com.ss.android.ugc.trill" bounds="[0,72][1080,1920]">
      <node index="0" text="" resource-id="com.ss.android.ugc.trill:id/g1i" class="android.widget.FrameLayout" package="com.ss.android.ugc.trill" content-desc="Trang tính dưới cùng" bounds="[0,1266][1080,1920]">
        <node index="0" text="" resource-id="com.ss.android.ugc.trill:id/ps5" class="android.widget.LinearLayout" package="com.ss.android.ugc.trill" bounds="[298,1266][783,1422]">
          <node index="0" text="Đã follow chung (1)" resource-id="com.ss.android.ugc.trill:id/ps2" class="android.widget.TextView" package="com.ss.android.ugc.trill" content-desc="Đã follow chung (1)" bounds="[298,1311][783,1377]" />
        </node>
        <node NAF="true" index="1" text="" resource-id="" class="android.widget.ImageView" package="com.ss.android.ugc.trill" clickable="true" bounds="[936,1278][1056,1410]" />
        <node index="2" text="" resource-id="com.ss.android.ugc.trill:id/sn9" class="androidx.recyclerview.widget.RecyclerView" package="com.ss.android.ugc.trill" bounds="[0,1422][1080,1674]">
          <node index="0" text="" resource-id="" class="android.widget.LinearLayout" package="com.ss.android.ugc.trill" bounds="[0,1422][1080,1638]">
            <node index="3" text="Đã follow" resource-id="com.ss.android.ugc.trill:id/u68" class="android.widget.Button" package="com.ss.android.ugc.trill" clickable="true" bounds="[768,1482][1032,1578]" />
          </node>
        </node>
      </node>
    </node>
  </node>
</hierarchy>
```

## Detection & Close Target Resolution
1. **Detection**:
   - `detect_follow_friends_suggestion_popup(xml_root)` detects title text/content-desc starting with `đã follow chung` or `follow chung`.
2. **Close Button Resolution**:
   - `_find_follow_friends_semantic_close_control(xml_root)` identifies the header close button:
     - The close button (`android.widget.ImageView`) often has `NAF="true"`, empty `text`, and empty `resource-id`.
     - It is resolved via `is_sheet_header_close`: matching an `ImageView`/`ImageButton` that is clickable and aligned vertically with the bottom sheet header title (`t_bounds`).
     - In the M43 hierarchy, bounds resolve to `[936,1278][1056,1410]`.

## Unit Test Regression Guard
In `python_runner/tests/test_benign_popup_registry.py`:
- Use `ET.fromstring(xml)` directly on the hierarchy string.
- Assert `detect_follow_friends_suggestion_popup(root) is True`.
- Assert `_find_follow_friends_semantic_close_control(root)` is not None, with `bounds="[936,1278][1056,1410]"`.
- Run with `pytest -k "test_mutual_follow_bottom_sheet"`.
