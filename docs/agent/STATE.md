# Oreo handoff state

Updated 2026-10-07. Active checkout:
`/Users/manishmandal/oreo/.claude/worktrees/web-ui`, branch `worktree-web-ui`.
Application commit `132c8ef` is pushed to origin/main. Token quotas are removed,
the original circular logo is restored, and personal Settings is live at
https://oreo.manish.engineer. Verified custom-domain deployment
`dpl_ASBE2tUYFtP4kNxutjCP6xXyH8sG` is READY. No SQL changes required.

## Changes

All authenticated users bypass the old reserve_chat/daily_usage quota path.
New conversations use a server-owned insert, existing conversation ownership is
checked before history/research, and atomic owned saves and leases remain.
No application max_tokens answer cap or 6,000-character message limit remains.
Provider limits and physical upload constraints still apply. No SQL migration.

Visible header Settings includes standing instructions, default model, brief/
balanced/thorough replies, creativity, efficient/balanced/extended recent context,
latest attachment reuse, web defaults and Enter behavior. Stored per account in
this browser, not across devices. Efficient context and ranked earlier-document
excerpts reduce repeated input without deleting saved history. A fewer-tokens
preset selects brief replies, efficient context and web off. New uploads are sent
in full. The shared SVG restores the original simple circular mark everywhere.

## Checks

44 Python mocked tests pass, covering quota-free new chats, ownership, settings
validation, custom instructions, provider creativity with no output cap, long
messages, attachments, research citations and streamed save failures. JavaScript
settings harness passes open/save/reset, efficient preset and account isolation.
Three JS syntax checks, Python compilation and git diff --check pass.
Ten production smoke checks pass: page, all three JS modules, logo, health and
config return 200; protected profile/history return 401 without auth; admin 404.
The page exposes Settings and custom instructions; preferences.js is deployed.

Earlier production verification covered real Haiku streaming, saved history and
web sources. Production file submission remains untested (mock upload tests pass).
Native Firefox preview was interrupted by concurrent user browser activity;
visual verification of the new settings dialog remains pending.

## Workspace

Preserve unrelated modified AGENTS.md and untracked GEMINI.md,
.github/copilot-instructions.md and .venv symlink. No secrets or private chat data
are recorded. Release is complete. Next useful checks: visual Settings review
when the browser is available, and a real production file submission/follow-up.
This release's authenticated model/settings flow is mock-tested; earlier real
streaming and research checks belong to the previous application release.

## 2026-10-07 — Internet/search diagnosis
Inspected branch worktree-web-ui at 34bc731. Public HTTPS to example.com
returned 200 and the custom-domain /api/health returned ok. The restricted
agent sandbox initially failed DNS; the same checks outside it succeeded.
The actual oreo.research search returned five BBC results, with no DuckDuckGo
challenge, and direct example.com reading returned 171 characters on this Mac.
Hosted UI preferences previously defaulted web to false; /api/chat only
researches when the request web flag is true. New-account default is web=true.
Existing v1 browser preferences migrate to v2, preserving each setting while
enabling web once; users can then turn it off and retain that choice. The
fewer-tokens preset still turns Web off. Hosted authenticated search from
Vercel remains unverified; next step is reproducing in the signed-in app and
checking hosted search/planner failures if needed. Authenticated accounts share
the same chat, files, settings, and research feature paths; no feature gate was
found. No automated tests run.


## 2026-10-07 — Chat responsiveness and logo cleanup
Web search is opt-in by default to avoid slowing ordinary chats. Existing
preferences migrate without altering other options, and Web defaults off for
all accounts to keep ordinary replies fast; the Web control stays available. Hosted search now uses the message directly instead of waiting for a
second model call to plan queries. The composer clears at send and restores its
text if the request fails. Removed the Oreo mark and favicon from the hosted
interface. Automated tests not run.


## 2026-10-07 — Keep the active reply in view
Sending a message now scrolls the chat to the new assistant placeholder before
waiting for the server. Streamed text then follows the reply while the reader is
near the bottom. This prevents the welcome screen from staying in view while a
reply is appended below it. No automated tests run.


## 2026-10-07 — Delete saved chats
Added a delete control to each sidebar conversation and an authenticated
DELETE /api/conversations?id=… route. The server filters deletion by both chat
and signed-in user; conversation message rows cascade with the parent. Deleting
the open chat returns the user to a fresh chat. No automated tests run.


## 2026-10-07 — Show reply preparation progress
The chat stream now starts after authentication and reports account check,
conversation setup, attachment reading, web search, and model connection
phases. This makes the wait before the first answer token visible instead of
showing only a generic thinking status. No automated tests run.

## 2026-10-08 — Conversation memory and response overhead
Inspected latest merge bf26602 (installable-app PR #1) on worktree-web-ui.
GitHub CI/deployment were successful; the live page, health and app assets
returned 200 and the deployed chat.js matched the merge. User confirmed the
reported outage had cleared, then requested faster responses and better context.

Fixed the 2,400-character default history cutoff that could drop all context
after one long answer. New api/context.py scans the last 100 owned messages,
preserves the last three turns using explicit excerpts when necessary, and
allocates bounded space to relevant older turns. Latest attachments are found
independently of recent text. Text budgets are 12k/24k/64k characters, with
separate bounded attachment excerpts. Saved history is unchanged. This is not
unlimited long-term memory; messages older than the retrieval window are omitted.

Hosted auth/database calls share an HTTP connection pool with per-request
credentials. Browser startup uses one history request; saved replies update
the sidebar locally instead of awaiting profile/history refreshes. Streaming
markdown batches at 40 ms and flushes on completion. Release the chat lease
before the done event so immediate follow-ups can start. CI caches pip, cancels
superseded runs, and includes JavaScript behavior/syntax checks. Test HTTP
shutdown polling is 10 ms; suite time fell from ~14 s to ~0.4 s locally.

Validation: Python regression suite, JavaScript send/error/account harness,
all public JS syntax, Python compilation and diff whitespace checks. An isolated
browser with fake auth/model and in-memory storage streamed a >4k-character
reply and correctly received prior context for a project-name follow-up.
Screenshot: /tmp/oreo-context-smoke.png (local test only). No real user chats
were used. No schema migration. Preserve unrelated AGENTS.md and untracked
agent pointers/.venv. Release CI/deployment verification follows the code push.
Real provider response speed has not been benchmarked.

Release follow-up: fa0f51c passed GitHub CI but live health returned 500. Vercel
runtime logs showed missing httpx because deployment uses pyproject.toml while
CI installed requirements.txt. Added the dependency to both manifests and a
regression check enforcing their parity. Final suite now has 60 Python tests
and 3 JS behavior tests. Full browser verification used a fake model; live
provider latency remains unmeasured.

## 2026-10-08 — Resume handoff checks
Inspected branch worktree-web-ui at b93a405. The worktree has unrelated local
changes in AGENTS.md, untracked .github/copilot-instructions.md, .venv symlink,
and GEMINI.md; preserve them. The hosted production app opens to its sign-in
screen in the isolated browser, so the authenticated Settings dialog could not
be reviewed visually. Firefox is in an active Meet call and was left untouched.
No file was uploaded. A production file submission requires uploading a benign
fixture to the hosted Oreo account and sending its text to the configured model
provider; waiting for the user's confirmation before that transmission. No
tests or code changes were made. Next step: after confirmation, sign in if the
browser permits, submit a generated fixture, request its contents back, and
verify the saved chat/file flow; otherwise report the specific access blocker.

## 2026-10-08 — Broader hosted speed and behavior audit
Resolved release verification for b93a405: Vercel reports deployment complete,
`/api/health` returns ok, unauthenticated conversations and an invalid bearer
chat request both return the expected 401, and production `chat.js` byte-matches
the pushed source. GitHub CI passed. The earlier 500 on fa0f51c was a packaging
manifest mismatch; `httpx` is now declared in both manifests and a parity test
prevents recurrence.

Continued audit: hosted browser defaults to Haiku for quick replies, model choices
are named by speed/capability, and warm processes reuse the ABB provider client.
Sonnet remains selectable. Full check: 62 Python tests, 3 JavaScript behavior
tests, JS syntax, Python compile and diff whitespace all pass. The local mock
browser flow streams a long answer and answers a context-dependent follow-up.
No real provider latency benchmark has been run, so no measured speed claim.

## 2026-10-08 — Minimal black hosted UI
Updated the hosted app to a pure-black canvas with restrained charcoal surfaces,
system typography, simplified line icons, and a single biscuit mark used across
the sidebar, mobile header, sign-in, favicon and installable-app icons. Removed
the welcome-screen eyebrow and starter cards. Aligned the chat-inserted welcome
copy with the static page, updated the browser theme color and PWA colors, and
added `public/theme.css` to the static route, offline shell and asset MIME test.

The local fake-auth preview at 127.0.0.1:4801 showed the mobile screen with the
black theme, composer and small biscuit mark; browser inspection confirmed the
stylesheet loaded and the canvas computes to rgb(0, 0, 0). Validation: 62 Python
unittest cases pass, 3 Node UI behavior tests pass, JavaScript syntax checks,
Python compileall and `git diff --check` pass. No real account or provider was
used. Released as commit `6e321b6` to `origin/main`. GitHub verification run
37796096710 passed, and Vercel deployment `dpl_FnBHTSgYa3hZh3S5cdLBPgcPf6zD`
is READY with `oreo.manish.engineer` attached. The live browser confirmed the
custom domain serves the new page, loads `/theme.css`, and computes the canvas
to black; the theme-color metadata is `#000000` and the Oreo favicon is linked.

Preserve unrelated modified `AGENTS.md` and untracked
`.github/copilot-instructions.md`, `.venv` symlink and `GEMINI.md`.

## 2026-10-08 — Wordmark and Settings refinement
Replaced the cookie mark with the text-only Oreo wordmark across the sidebar,
mobile header, sign-in, favicon and PWA icons. The header model control is now a
compact, subdued picker with concise model names; Settings retains descriptive
model names. Rebuilt Settings as grouped Models, Conversation, Personalization
and Behavior sections with clearer descriptions, consistent dark controls,
simple gear and close icons, a scrollable body and a pinned save bar. Kept all
existing preference field IDs and save/reset/preset behavior. Bumped the offline
shell cache to v5.

Previewed the signed-in mock at 127.0.0.1:4801. Confirmed the text-only header,
model picker, Settings hierarchy and all behavior toggles are visible and
scrollable. The new regression checks Settings hooks. Validation: 63 Python
unittest tests, 3 Node chat behavior tests, JavaScript syntax checks, Python
compileall and `git diff --check` pass. This refinement is prepared for release.
