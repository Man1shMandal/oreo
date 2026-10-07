# Oreo handoff state

Updated 2026-10-07. Active checkout:
`/Users/manishmandal/oreo/.claude/worktrees/web-ui`, branch `worktree-web-ui`.
Application commits `c59f326` (hosted rebuild) and `62e230d` (usage ring and shared
logo) are pushed to `origin/main`. HEAD inspected: `62e230d`.

## Live release

Production: https://oreo.manish.engineer. Verified deployment
`dpl_3Z8ezAEZt21fJAB8ZBPAYd7pHYRH`, READY, has the custom-domain aliases.
Supabase migrations 001–003 were previously applied and their rollback-only SQL
checks passed. This release requires no additional SQL or account configuration.
Google sign-in grants immediate access; the legacy approval flag is automatically
enabled on the server for compatibility with deployed quota functions.

## What changed

Hosted Oreo now has a responsive chat sidebar/mobile drawer, anchored composer,
streamed replies, safe markdown including lists/tables/code copying, persistent
conversation history, model selection, file upload/paste/drop, and optional web
research with persisted citations. Failed sends retain the draft and attachments.
Chat switching and account changes guard against stale responses and drafts.

Saved message envelopes retain document text, gateway-compatible image PDF
parts, small image previews, file names and source links. Old plain-text history
still works. Ownership and budgets are checked before research reads history or
calls the planner. Research validates public URLs on redirects as well as initial
fetches. SDK retries are disabled to avoid unreserved repeated requests.

Photo resizing supports typical large phone images. Current limits: five files,
2.2 MB combined after resizing, 3.2 MB JSON body, 48,000 extracted document
characters, and a 2,048-token answer cap. Web-enabled messages reserve another
4,000 estimated tokens for planning and bounded fetched context. PDF image
estimates count pages. Failed requests retain their reservation; reset is UTC.

The user requested no visible token numbers at the top: usage is now a quiet
ring with exact numbers/reset time in a tooltip and accessible label. One shared
`oreo/logo.svg` is used by sign-in, sidebar, mobile header and favicon. The local
browser also uses that same asset. Hosted/local functional storage remains separate.

## Verification

- Final Python suite: 41 mocked tests passed, including images, scanned PDFs,
  saved file follow-ups, web ownership/quota ordering, citations, streamed save
  success/failure, reserved-prefix escaping and private redirect blocking.
- Python compilation, both JS syntax checks and `git diff --check` passed.
- Isolated Firefox fake-auth/model preview verified streaming, markdown code/list/
  table formatting, citations, new chat, reopened citations, and mobile layout
  at 375 x 667. It used no real secrets or chat data.
- Live browser restored the existing signed-in session and saved-chat listing.
  A short Haiku prompt produced the expected real reply. A real hosted web-search
  prompt returned an answer with five official Python-source links. Both saved.
- Nine final public-domain smoke checks passed: page, both JS modules, shared
  SVG, health and public config return 200; account/history endpoints return
  401 without auth; removed admin route returns 404. Protected responses use
  no-store. Public config returns a valid default model ID.

Fresh Google OAuth was not repeated; the existing authenticated session was
verified. Upload processing, persistence and follow-ups were tested with mocks,
not a production file submission. A large synthetic photo and PDF were generated
in `/private/tmp/oreo-release-fixtures` for optional further manual verification.
The live smoke conversation contains only synthetic verification prompts.

## Workspace and next step

Preserved unrelated modified `AGENTS.md` and untracked provider instruction files
and `.venv` symlink. No credentials or private conversation contents are recorded
here. Final handoff refresh accompanies the pushed release notes.

The rebuild and requested UI refinements are live. Next useful check is a real
PDF/image upload and reopened follow-up; diagnose any user-reported issue against
this release. For much larger files, use private object storage rather than
expanding inline message storage indefinitely.
