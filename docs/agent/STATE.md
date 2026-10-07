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
