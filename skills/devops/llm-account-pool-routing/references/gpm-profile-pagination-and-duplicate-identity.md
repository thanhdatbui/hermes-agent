# GPM profile pagination and duplicate identity

## Trigger
Use this when a pool account is mapped to a GPM profile, especially before OAuth refresh, token extraction, or profile deletion.

## Safe procedure

1. Query GPM Local API with its documented pagination parameters (`page`, `per_page`). Do not treat the first response's list length as the global profile count.
2. Read and validate `pagination.total_page` and, when present, `pagination.total`/`total_count`. Fetch every declared page. If a page is missing, malformed, empty before the declared final page, totals change, or fetched count disagrees with the declared total, fail closed and do not select or delete a profile.
3. Build `email -> list[profiles]`, never `email -> profile` with silent overwrite. Preserve `id`, `profile_path`, `created_at`/`created_time`, group, and proxy metadata in the ambiguity report.
4. If multiple profiles share an email, do not choose by API order, newest/oldest date, or name alone. Start each candidate only when live verification is explicitly authorized; inspect the candidate's Gmail/ChatGPT session identity and capture fresh evidence. A matching name is metadata, not proof.
5. Only after one candidate is proven to contain the target Gmail may an OAuth/token sync proceed. If both candidates are live or identity remains unresolved, report `AMBIGUOUS_GPM_PROFILE` and stop destructive actions.
6. If deletion is authorized, stop the candidate first, delete only via the GPM API's canonical delete endpoint, record HTTP status/response, then re-query all pages and verify the duplicate is gone while the retained profile remains.

## Evidence pattern

For each candidate, retain: profile ID, profile path, creation timestamp, exact API endpoint, fresh Gmail URL/title/body marker, screenshot path if UI was used, stop response, delete response, and post-delete enumeration. Never claim a profile is absent from a first-page result.

## Common failure
A `limit` or `per_page` value may still be capped by the API (for example, 50 per page). The only reliable count is the validated pagination metadata plus complete page enumeration.
