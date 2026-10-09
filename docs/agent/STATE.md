# Oreo handoff state

## 2026-10-09 — Refined animated character

Replaced the small dot face with a shared custom element: glossy blue eyes,
subtle lashes and lids, and a small smile, based on the user’s reference. It
blinks and glances at rest, responds to typing and active work, and briefly
celebrates completed replies. The local app shows it in its mobile header; the
hosted app shows it in desktop, mobile, and sign-in headers. Reduced-motion
preferences are respected. Added the module to both apps’ static routes and the
hosted offline shell.

Validation: browser preview in the local app showed the new eye design in the
desktop sidebar. All 71 Python tests and 5 Node tests pass; JS syntax, Python
compilation, and `git diff --check` pass. Source checks confirm the mobile
mascot remains visible at the small-screen breakpoint. No model calls or
external accounts were used.

## 2026-10-09 — Shared text formatting

Inspected branch `worktree-web-ui` at `02b10a2`, synced with `origin/main`.
The hosted and local chat now share `public/markdown.js`. It handles headings,
paragraphs, nested and task lists, tables, quotes, links, code spans/fences,
strikethrough, inline/display math, and source-linked citations. KaTeX is loaded
with pinned version and SRI; the service worker can cache its CDN assets after
they load. Raw HTML stays escaped and citations only link to HTTP(S) sources.
The local web server now serves the shared module. Both views wrap long content,
scroll wide equations/tables, and keep code readable on mobile. Local streamed
replies append text while generating and format once when complete.

Validation: all 71 Python tests and 5 Node UI/Markdown tests pass; public JS and
the extracted local module pass syntax checks, Python compileall and
`git diff --check` pass. Browser rendering with a signed-in account and an
offline first-load of KaTeX were not exercised. Released as `11e7b8b` to
`origin/main`, with a service-worker comment cleanup in `b5d4d00`. GitHub run
`37889369304` passed. Production health returns ok, and the page, renderer,
styles and updated service worker serve the new release. Preserve existing
unrelated workspace changes.

## 2026-10-09 — Full system smoke check

Inspected `worktree-web-ui` at `02b10a2`, synced with `origin/main`. The full
Python suite passes (71 tests), all four Node chat UI tests pass, JavaScript
syntax checks pass for the hosted modules and service worker, Python compileall
passes, and `git diff --check` is clean. GitHub verification run
`37886810161` passed.

Production `/api/health`, `/api/config`, homepage, chat/voice scripts, theme,
manifest, service worker, wordmark, and install icons return 200 and contain the
current release. Unauthenticated conversation/profile reads and a valid-shaped
chat request are rejected with 401. The local loopback server returns owner
state and its workspace, serves the Code control, and rejects an untrusted Host
with 403. Oreo Code list/context reads and an outside-workspace path rejection
also pass. The local server was stopped after the check; no model call was made.

Not covered: a signed-in production session, a real ABB model/search request,
browser microphone permission or physical speech recognition, and mobile/PWA
install interaction. Existing unrelated `AGENTS.md`, `.github/copilot-instructions.md`,
`.venv`, and `GEMINI.md` workspace changes remain untouched.

## 2026-10-09 — Search and voice UI

Inspected branch `worktree-web-ui` at `43d9e20`. The hosted composer now shows
Web: On or Web: Off with a high-contrast active state, matching accessible
pressed state and tooltip. Search stays enabled for later messages in the same
chat; a new chat starts from the saved preference. The local browser UI uses
the same explicit state label. The mic remains visible but is disabled with a
browser/security explanation when speech recognition is unavailable. Manual
sends cancel active listening without sending a second message; canceled
recognition ignores late results. Permission, microphone, network, and language
errors are described separately, and canceled older read-aloud events cannot
reset a newer speaking state.

Oreo Code is owner-only in the local browser app. Run
`bin/oreo web --workspace /path/to/project` from the active checkout, open
`http://localhost` (or the printed fallback port), and select **Oreo Code** next
to the composer controls. The hosted service deliberately cannot read or modify
the Mac's local project files.

Validation: all 71 Python tests and 4 Node chat UI tests pass; hosted and local
JavaScript syntax checks, Python compilation, and `git diff --check` pass. The
fixes were pushed in `bcdeed2`; GitHub run `37886720224` passed, production
`/api/health` returns ok, and the live page, chat script, and voice script serve
the updated controls. Real browser microphone permission/recognition was not
exercised.

## 2026-10-09 — Voice chat and Oreo Code

Inspected `worktree-web-ui` at `b7bfc0e`. Integrated Prashant's `voice-chat`
commit (`b74a5ff`, original author preserved) and committed the local Oreo Code
agent (`b7bfc0e`). Hosted voice uses browser speech recognition/synthesis,
spoken controls, and the updated offline shell. Local Oreo Code reads project
guidance, inspects Git, searches/reads/edits files, creates/moves/deletes files,
reads public documentation, and runs commands. Every file mutation and command
requires review; file tools stay inside the chosen workspace. Voice startup now
handles unavailable microphone permission without leaving the mic stuck active.

Checks: Python compilation of `oreo/code_agent.py`, `oreo/web.py`, and
`api/index.py`; Node syntax checks of the local web script, `public/chat.js`, and
`public/voice.js`; `git show --check`; and `git diff --check` pass. Automated
tests and microphone/browser behavior were not run. No production deployment
was performed.

Preserve unrelated modified `AGENTS.md`, untracked
`.github/copilot-instructions.md`, `.venv` symlink, and `GEMINI.md`.

Updated 2026-10-08. Active checkout:
`/Users/manishmandal/oreo/.claude/worktrees/web-ui`, branch `worktree-web-ui`.
Latest application commit `4b7a193` is pushed to `origin/main`. The hosted app is
live at https://oreo.manish.engineer with an all-black theme, text-only Oreo
wordmark, compact model picker and redesigned Settings. Deployment
`dpl_7SCoDR2BYBpxiaxMeZDQiuAWxqnM` is READY. No SQL changes required.

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
in full. The shared SVG is now a text-only Oreo wordmark; PWA icons match it.

## Checks

63 Python tests and 3 Node chat behavior tests pass. Public JavaScript syntax,
Python compilation, and `git diff --check` pass. The local signed-in mock preview
verified the text-only header, compact model names, and redesigned Settings
sections and controls. Production CI run 37797631576 passed, Vercel deployment
`dpl_Hi4jNwxTE1EX3EimRe65NvqEsjVm` is READY, and the live page confirms the black
canvas and text-only brand. Settings remains locally stored per account and
browser. Production file submission and measured live provider latency remain
unverified.

## Workspace

Preserve unrelated modified `AGENTS.md` and untracked `GEMINI.md`,
`.github/copilot-instructions.md` and `.venv` symlink. No secrets or private chat
data are recorded. The latest release is complete.

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
compileall and `git diff --check` pass. Released as commit `6bfe682` to
`origin/main`. GitHub run 37797631576 passed, and Vercel deployment
`dpl_Hi4jNwxTE1EX3EimRe65NvqEsjVm` is READY with `oreo.manish.engineer`
attached. The production page confirms the pure-black canvas, Oreo wordmark,
loaded stylesheet, and Settings control with no biscuit mark in the interface.

## 2026-10-08 — Settings icon
Replaced the lopsided custom Settings gear in `public/index.html` with a
standard, balanced outline gear while retaining the existing button, accessible
label, and interaction. Inspected on `worktree-web-ui` at `8f398db`.

## 2026-10-08 — Composer focus and motion polish
Removed the blue textarea focus ring that overrode the composer styling, and
kept keyboard focus visible with a neutral outline on controls and a soft border
on the composer. Switched the leftover blue accent to monochrome, added short
press/hover transitions, subtle message/settings/drawer entrance motion, and a
streaming-caret pulse. Reduced-motion preferences disable the added motion.
Validation: 63 Python tests, 3 chat UI behavior tests, HTML parsing and
`git diff --check` pass.

## 2026-10-08 — Hosted chat request latency
Removed the routine profile read from each chat request; the lease RPC checks
account eligibility, and the compatibility activation path runs only when that
check reports a legacy pending profile. Conversation ownership and the latest
100 messages now load in one owner-filtered PostgREST embedding instead of two
serial requests. Authenticated user lookups are reused for up to 20 seconds on
a warm instance, keyed by a token hash and never beyond the JWT expiry. Text-only
requests skip Pillow imports used only for image previews. New conversations are
inserted after the model stream, so that write no longer delays the first token.

Validation: 67 Python tests, 3 JavaScript behavior tests, HTML parsing and
`git diff --check` pass. No real-provider latency benchmark was run; model and
network latency outside Oreo remain unmeasured.
Released as `4b7a193` to `origin/main`; GitHub run 37799595183 passed and Vercel
deployment `dpl_7SCoDR2BYBpxiaxMeZDQiuAWxqnM` is READY with the production alias.
The live site, theme stylesheet, and `/api/health` each returned HTTP 200.

## 2026-10-08 — Initial header eye concept
The first detailed eye concept was not released. It was replaced with the
two-dot treatment below after user feedback.

## 2026-10-08 — Smoother streamed replies
Streaming replies now append incoming text to one text node and convert to
formatted Markdown once the response completes, instead of reparsing and
replacing the entire answer every 40 ms. Removed the per-message entrance
animation, which replayed whenever a message was inserted. Bumped the offline
shell cache to v6 so installed apps can pick up the updated chat script.
Validation: all 68 Python tests, 3 Node chat UI tests, JavaScript syntax, and
`git diff --check` pass. No production latency benchmark was run. Released in
commit `3f386a2` to
`origin/main`; GitHub verification run `37800616420` passed. The live health
endpoint returns ok and production `/chat.js` contains the streamed text-node
rendering change.

## 2026-10-08 — Two-dot header eyes
Replaced the detailed eye with exactly two small white dots. They blink
together and bounce gently while typing or while Oreo is working; reduced-motion
settings disable the animation. Added a regression assertion for exactly two
dots and bumped the offline shell to v7. Validation: all 68 Python tests, 3
Node chat UI tests, JavaScript syntax, and `git diff --check` pass. Released in
commit `2519320` to `origin/main`; GitHub verification run `37800977762` passed.
Production HTML and CSS serve the dots and animation, and `/api/health` returns
ok.

## 2026-10-08 — Wordmark-aligned eyes
Moved the dots out of the chat title and placed them beside the Oreo wordmark
in the desktop sidebar and mobile header. Motion is now a single 220 ms pop
when typing or starting work, with a slow blink every 8.2 seconds; reduced-motion
settings disable both. Validation: all 68 Python tests, 3 Node chat UI tests,
JavaScript syntax and `git diff --check` pass. Released in commit `2cb3935` to
`origin/main`; GitHub verification run `37801687965` passed. Production HTML and
CSS confirm the responsive placement, and `/api/health` returns ok.

## 2026-10-08 — Smiling idle character
Added a small curved smile beneath the two dots. The character now floats by
less than one pixel on a slow 3.6 second idle loop and blinks every 8.2 seconds;
while the user types or Oreo works, the idle loop speeds up slightly. Reduced
motion disables both. Bumped the offline shell to v9. Validation: all 68 Python
tests, 3 Node chat UI tests, JavaScript syntax, and `git diff --check` pass.
Released in commit `854e876` to `origin/main`; GitHub verification run
`37802179016` passed. Production serves the smile and idle styles, and
`/api/health` returns ok.
