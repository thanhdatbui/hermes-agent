# Codex vs ChatGPT-Web — OAuth & OmniRoute 20129

User directive (2026-09-13): uu tien OAuth Codex truoc, tam dung ChatGPT-Web.

## 1. Khac biet cot loi
- Codex (`provider: codex`): model `gpt-5.6-sol*`, `gpt-5.5`, `codex/*`. Auth = OAuth Developer
  chuan (`accessToken` JWT qua callback server). Ben, auto-renew qua OmniRoute,
  khong dinh Cloudflare WAF web.
- ChatGPT-Web (`provider: chatgpt-web`): model `gpt-5.6-luna*`, `gpt-4o` web.
  Auth = cookie `__Secure-next-auth.session-token`. Chet nhanh (vai ngay),
  de dinh bot-detection / Cloudflare challenge o `chatgpt.com`.

## 2. Pitfalls Google SSO -> ChatGPT da va (2026-09-13, batch 5 workers)
1. Fast-path da login san: `goto chatgpt.com/auth/login` tu redirect 302 ve
   `chatgpt.com/` (khong con `/auth/`). Neu script van cho nut
   `Continue with Google` -> timeout 30s fail oan (vd: luuhuong28022000).
   Fix: check ngay sau goto, neu da o home thi nhay thang toi buoc lay token.
2. Google OAuth Consent (`accounts.google.com/signin/oauth/id`, "Dang nhap vao OpenAI"):
   nut `Tiep tuc`/`Continue` nam trong Web Component, locator Playwright thuong
   khong click an. Fix: JS evaluate tim button theo innerText roi `.click()`.
3. Onboarding `auth.openai.com/about-you` ("Ban bao nhieu tuoi?"): neu
   `input[name="name"]` trong thi nut submit `disabled`. Fix: dien ten tu
   profile/email + tuoi 22-28 roi submit.
4. OmniRoute `POST /api/providers` tra ve **201 Created** khi tao moi thanh cong,
   khong phai 200. Hook phai chap nhan `status in (200, 201)` keo bao loi gia.

## 3. Quy tac uu tien
- Chay OAuth Codex truoc (`run_codex_oauth_flow.py`: authorize -> GPM CDP duyet
  authUrl -> poll callback -> gan proxy 1:1). Chi quay lai ChatGPT-Web khi user
  yeu cau ro rang.
