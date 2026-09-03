# Path B: Suggested RecyclerView Regression

## Symptom

Mode 2 reports `MANUAL_REVIEW: Path B fail` after tapping a follower row. The
profile dump contains a TikTok 46.x RecyclerView ID such as `id/uo1` because the
profile renders a `Tài khoản được đề xuất` tray. A check that treats the recycler
ID alone as proof that the app is still on the follower/following list rejects the
real profile before identity/action verification.

## Root cause

`_path_b_verify` previously used:

```python
not any(node["resource_id"] in FOLLOWER_LIST_RECYCLER_IDS for node in profile_nodes)
```

This is a false screen classifier. The same resource-ID family can occur in a
suggested-account component on a profile.

## Correct fix

Use the full structural classifier (`_on_follower_list`) rather than a raw
RecyclerView-ID test. Only a screen with a proven selected relation header and a
valid populated/empty relation surface counts as the follower list. Otherwise,
continue Path B profile verification, while retaining all fail-closed gates:

- exact normalized target handle in the profile header;
- valid identity element;
- exactly classified relationship action;
- successful Back and restored follower-list proof.

Do not solve this by removing identity checks or accepting a target found only in
suggestions. Add a fixture with a suggested RecyclerView using the same ID and a
negative fixture where the target exists only below the header.

## Verification

Run the focused Path B/Case 49 tests and the complete Mode 2 test module with the
repo's pinned interpreter. Report offline regression evidence separately from any
live canary; a live canary may be explicitly excluded by the operator.
