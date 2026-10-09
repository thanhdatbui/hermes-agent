# UI Recovery Postcondition Contract

## Why this matters

A transient Android/TikTok startup network screen can expose a real retry control
while the device proxy and Wi-Fi are healthy. A handler that logs only `attempt`
or returns `dismissed=True` after issuing a tap can leave the caller believing the
screen was recovered. The authoritative result is the **new observation after the
action**, not the action's return value.

## Minimal fixture

Use an offline XML fixture that includes the TikTok package and the actual retry
node shape:

```xml
<node package="com.ss.android.ugc.trill"
      resource-id="com.ss.android.ugc.trill:id/dd9"
      text="Thử lại"
      bounds="[144,1329][936,1485]" />
<node package="com.ss.android.ugc.trill"
      resource-id="...:ze3"
      text="Không có kết nối Internet. Hãy nhấn để thử lại." />
<node package="com.ss.android.ugc.trill"
      resource-id="...:message_tv"
      text="Kết nối với internet và thử lại." />
```

The regression should prove that the selector chooses the retry node (and records
its resource-id/text/bounds) rather than tapping an arbitrary screen coordinate.

## Acceptance matrix

| Pre-capture | Action | Post-capture | Required result |
|---|---|---|---|
| Network marker + `dd9` | Exact retry tap | Network marker still present | Fail closed; retain latest artifact/reason; no success |
| Network marker + `dd9` | Exact retry tap | Marker absent and expected startup/feed screen present | Recovery success |
| Network marker + `dd9` | Tap unavailable | No valid target | Explicit failure; no blind fallback |
| Network marker | Bounded relaunch | Marker remains after retry budget | Fail closed with attempt count and final artifact |

## Test shape

Mock the XML capture, focus observation, tap/relaunch, and artifact paths. Return
observations in order and assert the order. Keep real devices, proxies, ADB, and
network calls out of the test. Assert both the decision (`success` versus
`manual-needed:network`/failure) and the evidence fields (`artifact_path`, reason,
retry count, selector metadata). A postcondition test must not pass merely because
`tap()` or `force_stop_and_relaunch_tiktok()` returned successfully.

## Scope discipline

If the user allowlists only a flow module and its test module, do not modify the
popup registry or shared device layer to make the fix easier. Read those layers
only to understand the existing seam; implement the smallest compatible change in
the allowed caller and cover it with mocked regressions.
