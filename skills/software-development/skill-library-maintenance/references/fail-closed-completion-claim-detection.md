# Runtime Guard False-Positive Completion Detection

## Why this exists

A fail-closed evidence gate can become unusable if its completion detector treats bare task vocabulary (`login`, `pass`, `2FA`) as proof that work is complete. In the incident that motivated this reference, a normal request such as “mở GPM vào ChatGPT login kiểm tra acc die” was classified as a completed login and was replaced by an evidence warning. The correct fix is to narrow the detector, not weaken the evidence gate.

## Contract

Completion detection must recognize a **completed state assertion**, not a topic mention:

- Positive examples: `đã đăng nhập`, `login thành công`, `2FA đã bật`, `đã đổi mật khẩu`, `thiết lập 2FA thành công`.
- Non-claims: requests, instructions, questions, plans, in-progress language, failures, and troubleshooting: `kiểm tra login`, `đang login`, `sẽ đổi pass`, `login lỗi`, `bật 2FA bị lỗi`, `đã đăng nhập được chưa?`.
- A sentence containing multiple independent completed claims must preserve all categories so the evidence gate can require evidence for each one.
- Existing evidence enforcement remains fail-closed once a genuine completion claim is detected.

## Implementation pattern

1. Keep the detector separate from media validation.
2. Match completion-oriented constructions (`đã ...`, `... thành công`, `... đã bật`) rather than bare nouns/verbs.
3. Split compound text into clauses before classification so a request and a real completion claim do not contaminate one another.
4. Apply local negative filters before adding a claim:
   - prefix: `chưa`, `không`, `đang`, `sẽ`, `kiểm tra`, `hướng dẫn`, `quy trình`, `mở`, `thử`;
   - suffix: `lỗi`, `thất bại`, `die`, `timeout`, `không được`, `bị khóa`, `bị ban`;
   - interrogative markers: `?`, `được chưa`, `có ... không`, `tại sao`, `thế nào`.
5. Do not make the detector depend on the presence of `MEDIA:`; detection decides whether validation is needed, while validation decides whether the report is admissible.
6. Preserve the worker bypass only where the established guard contract explicitly requires it; do not use a broad bypass to hide false positives.

## Regression matrix

Every change to a completion detector should include both categories:

| Class | Examples | Expected |
|---|---|---|
| completed login | `Đã đăng nhập nick @x`, `login thành công` | `login` claim |
| completed 2FA | `2FA: ON`, `thiết lập 2FA thành công` | `2fa` claim |
| completed password | `Đã đổi pass thành công`, `Mật khẩu: đã đổi` | `password` claim |
| compound completion | `@x đã đăng nhập và bật 2FA thành công` | both claims |
| request/topic | `kiểm tra login`, `mở GPM ... login` | no claim |
| in-progress | `đang login`, `sẽ đổi pass`, `đang bật 2FA` | no claim |
| failure | `login lỗi`, `đăng nhập thất bại`, `bật 2FA bị lỗi` | no claim |
| question | `có đăng nhập được không?`, `đã đăng nhập được chưa?` | no claim |
| evidence bypass | genuine completion without `MEDIA:` | evidence gate blocks |

Run the focused gate suite after the detector edit, then the remaining guard suite. Report focused and broader evidence separately. A passing test that only covers positive claims is insufficient: the regression is specifically a false-positive classification.

## Reload and release note

A source-level pass does not prove a currently running Hermes process has reloaded the plugin. After changing a runtime plugin, explicitly assess reload/cache state and state whether a Hermes/gateway restart is required. Do not claim the live process is fixed from pytest alone.
