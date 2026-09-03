# Location Dialog Cancel Handler — Detection, Dispatch, and Verification

## What was confirmed

The TikTok dialog shown as “Xem nội dung phù hợp và địa điểm lân cận” with buttons “Hủy” and “Mở cài đặt” is an allowlisted location-permission dialog. The intended safe action is to tap the semantic `Hủy` node, not `Mở cài đặt`, then require a fresh post-action capture.

## Detection contract

The strict core detector should require all of these in the same candidate modal subtree:

- exact title: `Xem nội dung phù hợp và địa điểm lân cận` (or the English equivalent);
- location-permission body text, such as `Truy cập Vị trí` / `Vị trí > Trong khi sử dụng`;
- settings button `android:id/button1` with `Mở cài đặt` / `Open settings`;
- cancel button `android:id/button3` with `Hủy` / `Huỷ` / `Cancel` / `Từ chối`, clickable and enabled;
- TikTok package identity on the dialog nodes.

Reject lookalikes: a generic `Hủy` node without the exact title/body, a wrong resource id such as a draft-discard button, another package, disabled buttons, or title/buttons split across sibling windows.

## Dispatch and action contract

The feed popup path must dispatch the location detector before generic popup fallback. The semantic match exposes the cancel element as the close target; the action may be represented internally as `dismiss_close_x`, but the actual target must be the matched `Hủy` node and its bounds/center. Never select the settings CTA. A registry/consumer wrapper may also support `Hủy`/`Huỷ`/`Từ chối`/`Cancel`, but broad fallback must not override the strict location match.

## Verification contract

A tap acknowledgement or `dismissed=True` without a usable fresh recapture is not success. After tapping `Hủy`, capture and inspect fresh XML/screenshot and verify the location dialog is absent, TikTok remains focused, and no sensitive/manual screen replaced it. If the dialog remains, classify the attempt as unverified/manual-needed and preserve the scene.

## Incident triage pattern

When an alert says a swipe recovery passed but the screenshot still shows this dialog, separate three questions:

1. Was the dialog recognized by the exact runtime XML?
2. Was the `Hủy` handler dispatched and did it tap the matched node?
3. Did the post-action recapture prove the dialog disappeared?

Read the exact attempt `log.jsonl`, matching `ui.xml`, and matching screenshot around the failure. Do not infer that the handler was skipped or that the screenshot is stale from the alert text alone. A “swipe recovery passed” record proves only that the bounded swipe verifier passed its own postcondition; it does not prove a later popup-dismiss pass ran or that the location dialog was absent in a different attempt.

## Regression coverage

Keep positive and negative fixtures for title/body/settings/cancel/package/same-subtree constraints, and a dispatch/action test that confirms `Hủy` is selected. Add a postcondition test that a missing or stale recapture cannot be reported as successful dismissal.
